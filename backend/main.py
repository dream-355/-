from __future__ import annotations

import json
import re
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Cookie, Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import db
from backend import prompts
from backend.config import settings
from backend.email_service import (
    EmailDeliveryError,
    email_configured,
    make_reset_code,
    reset_code_digest,
    send_health_report_email,
    send_password_reset_email,
    send_registration_email,
)
from backend.graph import medical_graph
from backend.input_guard import (
    INPUT_GUIDANCE,
    contextual_health_question,
    history_has_health_context,
    is_health_related,
    needs_input_guidance,
)
from backend.llm import (
    DeepSeekError,
    analyze_image,
    answer_question,
    extract_health_metrics,
    finalize_content,
    stream_deepseek,
    summarize_history,
)
from backend.lifestyle import build_lifestyle_plan
from backend.medications import recommend_medications
from backend.reviewer import review_answer
from backend.safety import health_overview, longitudinal_insights, triage
from backend.tools import TOOL_SPECS
from backend.vector_index import vector_index


SESSION_COOKIE = "qihuang_session"
AUTH_RATE_LIMITED_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/account",
    "/api/auth/password-reset/request",
    "/api/auth/password-reset/confirm",
}
auth_attempts: dict[str, deque[float]] = defaultdict(deque)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.initialize_database()
    threading.Thread(target=vector_index.warmup, daemon=True).start()
    yield
    medical_graph.close()


app = FastAPI(
    title="知衡健康 API",
    version="1.0.0",
    description="Neo4j 医疗知识图谱、DeepSeek 受约束问答与个人健康智能体",
    lifespan=lifespan,
)


@app.middleware("http")
async def disable_stale_frontend_cache(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    elif request.url.path.startswith("/models/") and request.url.path.endswith(".bin.gz"):
        # Geometry chunks are content-stable and immutable; cache them at the
        # browser and reverse proxy so 2-core deployments do not re-stream 33 MB
        # on every consultation.
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif request.url.path in {"/models/atlas.json", "/models/atlas-female.json"}:
        response.headers["Cache-Control"] = "public, max-age=300, must-revalidate"
    elif request.url.path.startswith("/vendor/three/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


@app.middleware("http")
async def limit_auth_attempts(request: Request, call_next):
    """Simple sliding-window throttle for credential endpoints."""
    if request.url.path in AUTH_RATE_LIMITED_PATHS:
        client = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = auth_attempts[client]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= settings.auth_rate_limit_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "尝试过于频繁，请 1 分钟后再试"},
            )
        bucket.append(now)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def current_user(
    qihuang_session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict[str, Any]:
    user = db.get_user_by_session(qihuang_session)
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=24)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: str
    password: str


class AccountUpdateRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_email: str | None = Field(default=None, max_length=120)
    new_password: str | None = Field(default=None, min_length=8, max_length=72)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=5, max_length=120)


class PasswordResetConfirmRequest(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8, max_length=72)


class EmailReportRequest(BaseModel):
    report_type: str = Field(pattern=r"^(passport|visit_summary)$")


class LifestylePlanRequest(BaseModel):
    symptoms: str = Field(default="", max_length=1000)
    dietary_preferences: str = Field(default="", max_length=300)


class ConversationRequest(BaseModel):
    title: str = Field(default="新的健康咨询", max_length=80)


class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)
    image_data: str | None = Field(default=None, max_length=8_000_000)


class VisionRequest(BaseModel):
    image_data: str = Field(min_length=32, max_length=8_000_000)
    question: str = Field(default="", max_length=1000)


class HealthMetricsVisionRequest(BaseModel):
    image_data: str = Field(min_length=32, max_length=8_000_000)


class HealthRecordRequest(BaseModel):
    measured_at: str | None = None
    systolic: int | None = Field(default=None, ge=40, le=300)
    diastolic: int | None = Field(default=None, ge=20, le=200)
    heart_rate: int | None = Field(default=None, ge=20, le=250)
    glucose: float | None = Field(default=None, ge=0, le=40)
    spo2: int | None = Field(default=None, ge=50, le=100)
    weight_kg: float | None = Field(default=None, ge=10, le=400)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    steps: int | None = Field(default=None, ge=0, le=200000)
    mood: str | None = Field(default=None, max_length=30)
    note: str = Field(default="", max_length=500)
    source: str = Field(default="manual", max_length=30)


class ProfileRequest(BaseModel):
    gender: str = ""
    birth_date: str = ""
    blood_type: str = ""
    height_cm: float | None = Field(default=None, ge=50, le=260)
    allergies: list[str] = []
    conditions: list[str] = []
    medications: list[str] = []
    family_history: list[str] = []


class TriageRequest(BaseModel):
    symptoms: str = Field(min_length=2, max_length=3000)
    duration_days: int | None = Field(default=None, ge=0, le=3650)
    age: int | None = Field(default=None, ge=0, le=120)
    pregnancy: bool = False
    systolic: int | None = Field(default=None, ge=40, le=300)
    diastolic: int | None = Field(default=None, ge=20, le=200)
    heart_rate: int | None = Field(default=None, ge=20, le=250)
    glucose: float | None = Field(default=None, ge=0, le=40)
    spo2: int | None = Field(default=None, ge=50, le=100)


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    ease_score: int = Field(ge=1, le=5)
    usefulness_score: int = Field(ge=1, le=5)
    comments: str = Field(default="", max_length=1000)


def user_payload(user: dict[str, Any]) -> dict[str, Any]:
    profile = db.get_health_profile(user["id"])
    return {**user, "profile": profile}


def validate_image_data(image_data: str | None) -> str | None:
    if not image_data:
        return None
    if not re.match(r"^data:image/(jpeg|png|webp);base64,", image_data):
        raise HTTPException(status_code=422, detail="仅支持 JPG、PNG 或 WebP 图片")
    return image_data


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    graph_health = medical_graph.health()
    return {
        "ok": True,
        "app": settings.app_name,
        "time": datetime.now().astimezone().isoformat(),
        "neo4j": graph_health,
        "deepseek_configured": bool(settings.deepseek_api_key),
        "email_configured": email_configured(),
        "model": settings.deepseek_model,
        "vision_model": settings.deepseek_vision_model,
        "vector_index": vector_index.stats(),
        "mcp_tools": len(TOOL_SPECS),
    }


@app.post("/api/auth/register")
def register(payload: RegisterRequest, response: Response) -> dict[str, Any]:
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", payload.email):
        raise HTTPException(status_code=422, detail="邮箱格式不正确")
    try:
        user = db.create_user(payload.email, payload.password, payload.name)
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise HTTPException(status_code=409, detail="该邮箱已注册") from exc
        raise
    token = db.create_session(user["id"])
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    email_status = "not_configured"
    email_notice = "邮件服务尚未配置，账户已创建成功"
    if email_configured():
        try:
            send_registration_email(user)
            email_status = "sent"
            email_notice = "注册信息已发送到你的邮箱"
        except EmailDeliveryError:
            email_status = "failed"
            email_notice = "账户已创建，但注册通知邮件发送失败"
    return {
        "user": user_payload(user),
        "registration_email": {
            "status": email_status,
            "message": email_notice,
        },
    }


@app.post("/api/auth/login")
def login(payload: LoginRequest, response: Response) -> dict[str, Any]:
    user = db.authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码不正确")
    token = db.create_session(user["id"])
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return {"user": user_payload(user)}


@app.post("/api/auth/demo")
def demo_login(response: Response) -> dict[str, Any]:
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="演示模式未开启")
    user = db.authenticate("demo@qihuang.local", "demo1234")
    if not user:
        raise HTTPException(status_code=503, detail="演示档案尚未初始化")
    token = db.create_session(user["id"])
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return {"user": user_payload(user)}


@app.post("/api/auth/logout")
def logout(
    response: Response,
    qihuang_session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict[str, bool]:
    db.delete_session(qihuang_session)
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.post("/api/auth/password-reset/request")
def request_password_reset(payload: PasswordResetRequest) -> dict[str, Any]:
    email = payload.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=422, detail="邮箱格式不正确")
    if not email_configured():
        raise HTTPException(
            status_code=503,
            detail="邮件服务尚未配置，暂时无法发送验证码",
        )

    user = db.get_user_by_email(email)
    generic_response = {
        "ok": True,
        "message": "如果该邮箱已注册，验证码将在几分钟内送达",
        "expires_in_minutes": 10,
    }
    if not user:
        return generic_response

    if user["email"].lower() == "demo@qihuang.local":
        return generic_response

    code = make_reset_code()
    issued = db.issue_password_reset_code(
        user["id"],
        reset_code_digest(email, code),
    )
    if not issued["ok"]:
        if issued["error"] == "cooldown":
            raise HTTPException(
                status_code=429,
                detail=f"请求过于频繁，请在 {issued['retry_after']} 秒后重试",
            )
        raise HTTPException(status_code=500, detail="验证码生成失败")

    try:
        send_password_reset_email(user, code, issued["expires_in_minutes"])
    except EmailDeliveryError as exc:
        db.invalidate_password_reset_codes(user["id"])
        raise HTTPException(
            status_code=503,
            detail="验证码邮件发送失败，请稍后重试",
        ) from exc
    return generic_response


@app.post("/api/auth/password-reset/confirm")
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
) -> dict[str, Any]:
    email = payload.email.strip().lower()
    if not re.fullmatch(r"\d{6}", payload.code):
        raise HTTPException(status_code=422, detail="请输入 6 位数字验证码")
    result = db.reset_password_with_code(
        email,
        reset_code_digest(email, payload.code),
        payload.new_password,
    )
    if not result["ok"]:
        messages = {
            "invalid_code": "验证码不正确或已失效",
            "expired": "验证码已过期，请重新获取",
            "too_many_attempts": "验证码错误次数过多，请重新获取",
        }
        raise HTTPException(
            status_code=400,
            detail=messages.get(result["error"], "密码重置失败"),
        )
    return {
        "ok": True,
        "message": "密码已重置，请使用新密码登录",
    }


@app.get("/api/auth/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return {"user": user_payload(user)}


@app.put("/api/auth/account")
def update_account(
    payload: AccountUpdateRequest,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    new_email = (payload.new_email or "").strip()
    if new_email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", new_email):
        raise HTTPException(status_code=422, detail="邮箱格式不正确")
    result = db.update_account(
        user["id"],
        payload.current_password,
        new_email=new_email or None,
        new_password=payload.new_password,
    )
    if not result["ok"]:
        messages = {
            "invalid_password": "当前密码不正确",
            "email_taken": "该邮箱已被其他账号使用",
            "nothing_to_update": "邮箱和密码都没有变化",
            "user_not_found": "账号不存在",
        }
        raise HTTPException(
            status_code=400 if result["error"] != "email_taken" else 409,
            detail=messages.get(result["error"], "账号更新失败"),
        )
    return {"user": result["user"]}


@app.get("/api/dashboard")
def dashboard(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    records = db.list_health_records(user["id"], 14)
    conversations = db.list_conversations(user["id"])
    return {
        "overview": health_overview(records),
        "recent_records": records[:7],
        "conversations": conversations[:4],
        "longitudinal": longitudinal_insights(records, conversations),
        "graph": medical_graph.stats(),
    }


@app.post("/api/lifestyle/plan")
def lifestyle_plan(
    payload: LifestylePlanRequest,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    return build_lifestyle_plan(
        db.get_health_profile(user["id"]),
        db.list_health_records(user["id"], 14),
        db.list_triage_events(user["id"], 5),
        symptoms=payload.symptoms,
        dietary_preferences=payload.dietary_preferences,
    )


def build_health_timeline(user_id: str, limit: int = 80) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for record in db.list_health_records(user_id, limit):
        indicators = []
        if record.get("systolic") is not None:
            indicators.append(
                f"血压 {record['systolic']}/{record.get('diastolic', '—')}"
            )
        if record.get("heart_rate") is not None:
            indicators.append(f"心率 {record['heart_rate']} 次/分")
        if record.get("sleep_hours") is not None:
            indicators.append(f"睡眠 {record['sleep_hours']} 小时")
        events.append(
            {
                "id": record["id"],
                "type": "vital",
                "title": "健康体征记录",
                "description": " · ".join(indicators) or "新增健康记录",
                "occurred_at": record["measured_at"],
                "risk": "low",
                "source": record.get("source") or "手动记录",
            }
        )
    for event in db.list_triage_events(user_id, limit):
        events.append(
            {
                "id": event["id"],
                "type": "triage",
                "title": event.get("result", {}).get("title") or "智能健康检测",
                "description": f"{event['symptoms']} · 风险指数 {event['score']}",
                "occurred_at": event["created_at"],
                "risk": event["level"],
                "source": "规则与图谱双引擎",
            }
        )
    for conversation in db.list_conversations(user_id):
        events.append(
            {
                "id": conversation["id"],
                "type": "consultation",
                "title": conversation["title"],
                "description": conversation.get("summary")
                or "健康咨询记录",
                "occurred_at": conversation["updated_at"],
                "risk": conversation.get("risk_level", "low"),
                "source": "知衡健康 AI",
            }
        )
    events.sort(key=lambda item: item.get("occurred_at", ""), reverse=True)
    return events[:limit]


@app.get("/api/health/timeline")
def health_timeline(
    limit: int = Query(default=40, ge=1, le=200),
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    return {"events": build_health_timeline(user["id"], limit)}


@app.get("/api/health/summary")
def health_summary(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    profile = db.get_health_profile(user["id"])
    records = db.list_health_records(user["id"], 14)
    conversations = db.list_conversations(user["id"])[:6]
    events = build_health_timeline(user["id"], 20)
    overview = health_overview(records)
    insights = longitudinal_insights(records, conversations)
    latest = overview.get("latest", {})

    vitals = []
    if latest.get("systolic"):
        vitals.append(f"血压 {latest['systolic']}/{latest.get('diastolic', '—')} 毫米汞柱")
    if latest.get("heart_rate"):
        vitals.append(f"静息心率 {latest['heart_rate']} 次/分")
    if latest.get("glucose") is not None:
        vitals.append(f"血糖 {latest['glucose']} mmol/L")
    if latest.get("sleep_hours") is not None:
        vitals.append(f"睡眠 {latest['sleep_hours']} 小时")

    risk_events = [
        event for event in events
        if event.get("risk") in {"high", "emergency"}
    ][:3]

    questions = [
        "目前的指标波动是否需要进一步检查？",
        "现有用药方案是否需要调整？",
    ]
    if latest.get("sleep_hours") and float(latest["sleep_hours"]) < 7:
        questions.append("长期睡眠不足应如何干预？")
    if profile.get("allergies"):
        questions.append("用药时如何规避已知过敏原？")

    lines = [
        "# 就诊前健康摘要",
        "",
        f"生成时间：{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M')}",
        f"用户：{user.get('name', '')}",
        "",
        "## 基本信息",
        f"- 性别：{profile.get('gender') or '未填写'}",
        f"- 出生日期：{profile.get('birth_date') or '未填写'}",
        f"- 血型：{profile.get('blood_type') or '未填写'}",
        f"- 过敏史：{'、'.join(profile.get('allergies') or []) or '无记录'}",
        f"- 基础疾病：{'、'.join(profile.get('conditions') or []) or '无记录'}",
        f"- 长期用药：{'、'.join(profile.get('medications') or []) or '无记录'}",
        "",
        "## 最近记录",
        "、".join(vitals) if vitals else "暂无体征记录",
        f"综合评分：{overview.get('score')}（{overview.get('status')}）",
        "",
        "## 近期健康咨询",
    ]
    if conversations:
        for conversation in conversations:
            lines.append(f"- {conversation.get('title', '健康咨询')}")
    else:
        lines.append("- 暂无咨询记录")
    lines.append("")
    lines.append("## 需要关注的变化")
    if insights:
        for insight in insights:
            lines.append(f"- {insight['title']}：{insight['detail']}")
    else:
        lines.append("- 暂未发现明确的指标与症状关联")
    if risk_events:
        lines.append("")
        lines.append("## 近期高风险事件")
        for event in risk_events:
            lines.append(f"- {event.get('title')}（{event.get('occurred_at', '')[:10]}）")
    lines.append("")
    lines.append("## 想咨询医生的问题")
    for question in questions[:4]:
        lines.append(f"- {question}")
    lines.append("")
    lines.append("> 本摘要由用户记录自动整理，仅供就诊沟通参考，不构成诊断。")

    return {
        "summary": "\n".join(lines),
        "generated_at": datetime.now().astimezone().isoformat(),
        "insights": insights,
        "risk_events": risk_events,
    }


@app.get("/api/health/passport")
def health_passport(
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    profile = db.get_health_profile(user["id"])
    records = db.list_health_records(user["id"], 30)
    overview = health_overview(records)
    timeline = build_health_timeline(user["id"], 50)
    conversations = db.list_conversations(user["id"])[:6]
    return {
        "owner": {"name": user["name"], "email": user["email"]},
        "generated_at": datetime.now().astimezone().isoformat(),
        "profile": profile,
        "overview": overview,
        "latest_records": records[:10],
        "timeline": timeline,
        "recent_consultations": conversations,
        "feedback": db.feedback_summary(user["id"]),
        "disclaimer": (
            "本摘要由用户授权生成，用于整理健康信息和就诊沟通，"
            "不是医生诊断，也不代表任何医疗机构审核。"
        ),
    }


@app.post("/api/email/health-report")
def email_health_report(
    payload: EmailReportRequest,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    if not email_configured():
        raise HTTPException(
            status_code=503,
            detail="邮件服务尚未配置，暂时无法发送报告",
        )
    if user["email"].lower() == "demo@qihuang.local":
        raise HTTPException(
            status_code=400,
            detail="游客账号未绑定真实邮箱，请注册账户后使用报告邮件功能",
        )
    report = (
        health_passport(user)
        if payload.report_type == "passport"
        else health_summary(user)
    )
    try:
        send_health_report_email(user, payload.report_type, report)
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=503,
            detail="报告邮件发送失败，请稍后重试",
        ) from exc
    return {
        "ok": True,
        "recipient": user["email"],
        "report_type": payload.report_type,
        "message": "报告已发送到你的注册邮箱",
    }


@app.post("/api/feedback")
def submit_feedback(
    payload: FeedbackRequest,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    feedback = db.add_feedback(
        user["id"],
        rating=payload.rating,
        ease_score=payload.ease_score,
        usefulness_score=payload.usefulness_score,
        comments=payload.comments,
    )
    return {"feedback": feedback, "summary": db.feedback_summary(user["id"])}


@app.get("/api/feedback/summary")
def get_feedback_summary(
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    return db.feedback_summary(user["id"])


@app.get("/api/health/profile")
def get_profile(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return {"profile": db.get_health_profile(user["id"])}


@app.put("/api/health/profile")
def save_profile(
    payload: ProfileRequest, user: dict[str, Any] = Depends(current_user)
) -> dict[str, Any]:
    profile = db.update_health_profile(user["id"], payload.model_dump())
    return {"profile": profile}


@app.get("/api/health/records")
def get_health_records(
    limit: int = Query(default=30, ge=1, le=365),
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    records = db.list_health_records(user["id"], limit)
    return {"records": records, "overview": health_overview(records)}


@app.post("/api/health/records")
def save_health_record(
    payload: HealthRecordRequest, user: dict[str, Any] = Depends(current_user)
) -> dict[str, Any]:
    values = payload.model_dump()
    if not any(
        values.get(key) is not None
        for key in (
            "systolic",
            "diastolic",
            "heart_rate",
            "glucose",
            "spo2",
            "weight_kg",
            "sleep_hours",
            "steps",
        )
    ):
        raise HTTPException(status_code=422, detail="请至少填写一项健康指标")
    record = db.add_health_record(user["id"], values)
    records = db.list_health_records(user["id"], 14)
    return {"record": record, "overview": health_overview(records)}


@app.get("/api/conversations")
def get_conversations(
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    return {"conversations": db.list_conversations(user["id"])}


@app.post("/api/conversations")
def new_conversation(
    payload: ConversationRequest, user: dict[str, Any] = Depends(current_user)
) -> dict[str, Any]:
    return {"conversation": db.create_conversation(user["id"], payload.title)}


@app.get("/api/conversations/{conversation_id}")
def conversation_detail(
    conversation_id: str, user: dict[str, Any] = Depends(current_user)
) -> dict[str, Any]:
    conversation = db.get_conversation(user["id"], conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"conversation": conversation}


@app.patch("/api/conversations/{conversation_id}")
def rename_conversation(
    conversation_id: str,
    payload: RenameConversationRequest,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, bool]:
    if not db.get_conversation(user["id"], conversation_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    db.update_conversation(conversation_id, title=payload.title)
    return {"ok": True}


@app.delete("/api/conversations/{conversation_id}")
def remove_conversation(
    conversation_id: str, user: dict[str, Any] = Depends(current_user)
) -> dict[str, bool]:
    if not db.delete_conversation(user["id"], conversation_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}


def _input_guidance_trace() -> dict[str, Any]:
    return {
        "entities": [],
        "graph": {"nodes": [], "edges": []},
        "triage": {
            "level": "low",
            "title": "等待症状描述",
            "red_flags": [],
            "symptoms": [],
            "action": "请先补充症状、持续时间和伴随表现。",
            "departments": ["全科医学科"],
        },
        "source_mode": "input-guidance",
        "model": "本地输入引导",
        "evidence_count": 0,
        "citations": [],
        "retrieval": {},
        "intent": "clarification",
        "has_image": False,
        "metrics": {
            "retrieval_ms": 0,
            "first_token_ms": 0,
            "total_ms": 0,
            "stream_tokens": 0,
            "answer_chars": len(INPUT_GUIDANCE),
        },
        "tool_calls": [],
    }


def _save_input_guidance(
    conversation: dict[str, Any],
    message: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    user_message = db.add_message(conversation["id"], "user", message)
    trace = _input_guidance_trace()
    assistant_message = db.add_message(
        conversation["id"], "assistant", INPUT_GUIDANCE, trace
    )
    db.update_conversation(conversation["id"], risk_level="low")
    return user_message, assistant_message, trace


@app.post("/api/chat")
def chat(
    payload: ChatRequest, user: dict[str, Any] = Depends(current_user)
) -> dict[str, Any]:
    request_started = time.perf_counter()
    if payload.conversation_id:
        conversation = db.get_conversation(user["id"], payload.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        title = (
            re.sub(r"\s+", " ", payload.message).strip()[:32]
            if is_health_related(payload.message)
            else "新的健康咨询"
        )
        conversation = db.create_conversation(user["id"], title)

    history = db.conversation_context(conversation["id"], 12)
    if needs_input_guidance(
        payload.message,
        history=history,
        has_image=bool(payload.image_data),
    ):
        user_message, assistant_message, trace = _save_input_guidance(
            conversation, payload.message
        )
        return {
            "conversation_id": conversation["id"],
            "user_message": user_message,
            "assistant_message": assistant_message,
            "trace": trace,
        }
    profile = db.get_health_profile(user["id"])
    age = _age_from_birth_date(profile.get("birth_date"))
    latest_records = db.list_health_records(user["id"], 1)
    triage_result = triage(
        payload.message,
        age=age,
        vitals=latest_records[0] if latest_records else {},
    )
    resolved_question = contextual_health_question(payload.message, history)
    contextual_follow_up = resolved_question != payload.message
    retrieval_started = time.perf_counter()
    graph_context = medical_graph.build_context(
        resolved_question,
        age=age,
        gender=profile.get("gender", ""),
        intent_override=(
            medical_graph.detect_intent(payload.message)
            if contextual_follow_up
            else None
        ),
    )
    graph_context["current_question"] = payload.message
    graph_context["resolved_question"] = resolved_question
    graph_context["contextual_follow_up"] = contextual_follow_up
    retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000, 2)
    user_message = db.add_message(
        conversation["id"],
        "user",
        f"[图片] {payload.message}" if payload.image_data else payload.message,
    )
    model_started = time.perf_counter()
    result = answer_question(
        question=payload.message,
        graph_context=graph_context,
        history=history,
        summary=conversation.get("summary", ""),
        profile=profile,
        triage=triage_result,
        image_data=validate_image_data(payload.image_data),
    )
    model_ms = round((time.perf_counter() - model_started) * 1000, 2)
    review_started = time.perf_counter()
    review = review_answer(
        question=payload.message,
        answer=result["content"],
        graph_context=graph_context,
        triage_result=triage_result,
    )
    review_ms = round((time.perf_counter() - review_started) * 1000, 2)
    result["content"] = review["content"]
    trace = {
        "entities": graph_context.get("entities", []),
        "graph": {
            "nodes": graph_context.get("nodes", [])[:42],
            "edges": graph_context.get("edges", [])[:60],
        },
        "triage": triage_result,
        "source_mode": result["source_mode"],
        "model": result["model"],
        "evidence_count": len(graph_context.get("facts", [])),
        "citations": graph_context.get("citations", []),
        "retrieval": graph_context.get("retrieval", {}),
        "intent": graph_context.get("intent", "general"),
        "has_image": bool(payload.image_data),
        "review": {
            key: value for key, value in review.items() if key != "content"
        },
        "metrics": {
            "retrieval_ms": retrieval_ms,
            "model_ms": model_ms,
            "review_ms": review_ms,
            "total_ms": round((time.perf_counter() - request_started) * 1000, 2),
            "answer_chars": len(result["content"]),
        },
        "tool_calls": [
            {
                "name": "medical_graph.hybrid_search",
                "status": "success",
                "result_count": len(graph_context.get("entities", [])),
                "duration_ms": retrieval_ms,
            },
            {
                "name": "medical_graph.expand_relationship",
                "status": "success",
                "result_count": len(graph_context.get("nodes", [])),
            },
            {
                "name": "medical_graph.filter_by_intent",
                "status": "success",
                "intent": graph_context.get("intent", "general"),
                "raw_fact_count": graph_context.get("retrieval", {}).get(
                    "raw_fact_count", 0
                ),
                "filtered_fact_count": graph_context.get("retrieval", {}).get(
                    "filtered_fact_count", 0
                ),
            },
            {
                "name": "llm.generate_with_citations",
                "status": "success",
                "model": result["model"],
                "duration_ms": model_ms,
            },
            {
                "name": "reviewer.medical_quality_check",
                "status": review["verdict"],
                "result_count": review["issue_count"],
                "duration_ms": review_ms,
            },
        ],
    }
    assistant_message = db.add_message(
        conversation["id"], "assistant", result["content"], trace
    )
    update_title = None
    if conversation["title"] == "新的健康咨询":
        update_title = re.sub(r"\s+", " ", payload.message).strip()[:32]
    db.update_conversation(
        conversation["id"],
        title=update_title,
        summary=summarize_history(
            conversation.get("summary", ""),
            payload.message,
            result["content"],
        ),
        risk_level=triage_result["level"],
    )
    return {
        "conversation_id": conversation["id"],
        "user_message": user_message,
        "assistant_message": assistant_message,
        "trace": trace,
    }


def _sse(payload: dict[str, Any]) -> str:
    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


@app.post("/api/chat/stream")
def chat_stream(
    payload: ChatRequest, user: dict[str, Any] = Depends(current_user)
) -> StreamingResponse:
    """Stream the answer token by token; every failure degrades to the grounded answer."""
    if payload.conversation_id:
        conversation = db.get_conversation(user["id"], payload.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        title = (
            re.sub(r"\s+", " ", payload.message).strip()[:32]
            if is_health_related(payload.message)
            else "新的健康咨询"
        )
        conversation = db.create_conversation(user["id"], title)

    history = db.conversation_context(conversation["id"], 12)
    if needs_input_guidance(
        payload.message,
        history=history,
        has_image=bool(payload.image_data),
    ):

        def generate_guidance():
            _, _, trace = _save_input_guidance(conversation, payload.message)
            for index in range(0, len(INPUT_GUIDANCE), 48):
                yield _sse({"token": INPUT_GUIDANCE[index : index + 48]})
            yield _sse(
                {
                    "done": True,
                    "conversation_id": conversation["id"],
                    "review": {"verdict": "pass", "issue_count": 0},
                }
            )

        return StreamingResponse(
            generate_guidance(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    profile = db.get_health_profile(user["id"])
    age = _age_from_birth_date(profile.get("birth_date"))
    latest_records = db.list_health_records(user["id"], 1)
    triage_result = triage(
        payload.message,
        age=age,
        vitals=latest_records[0] if latest_records else {},
    )
    resolved_question = contextual_health_question(payload.message, history)
    contextual_follow_up = resolved_question != payload.message
    retrieval_started = time.perf_counter()
    graph_context = medical_graph.build_context(
        resolved_question,
        age=age,
        gender=profile.get("gender", ""),
        intent_override=(
            medical_graph.detect_intent(payload.message)
            if contextual_follow_up
            else None
        ),
    )
    graph_context["current_question"] = payload.message
    graph_context["resolved_question"] = resolved_question
    graph_context["contextual_follow_up"] = contextual_follow_up
    retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000, 2)
    db.add_message(
        conversation["id"],
        "user",
        f"[图片] {payload.message}" if payload.image_data else payload.message,
    )

    prompt = prompts.build_user_prompt(
        question=payload.message,
        graph_context=graph_context,
        history=history,
        summary=conversation.get("summary", ""),
        profile=profile,
        triage=triage_result,
    )
    image_data = validate_image_data(payload.image_data)
    model = settings.deepseek_vision_model if image_data else settings.deepseek_model
    user_content: Any = prompt
    if image_data:
        user_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_data}},
        ]

    def generate():
        collected: list[str] = []
        started = time.perf_counter()
        first_token_ms: float | None = None
        token_count = 0

        def emit(text: str):
            collected.append(text)
            return _sse({"token": text})

        source_mode = "deepseek-vision" if image_data else "deepseek"
        try:
            for piece in stream_deepseek(
                [
                    {"role": "system", "content": prompts.SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                model=model,
                max_tokens=1600 if image_data else 1200,
            ):
                if piece:
                    if first_token_ms is None:
                        first_token_ms = round((time.perf_counter() - started) * 1000, 2)
                    token_count += 1
                    yield emit(piece)
        except DeepSeekError:
            fallback = answer_question(
                question=payload.message,
                graph_context=graph_context,
                history=history,
                summary=conversation.get("summary", ""),
                profile=profile,
                triage=triage_result,
                image_data=image_data,
            )
            collected.clear()
            source_mode = fallback["source_mode"]
            text = fallback["content"]
            for index in range(0, len(text), 60):
                yield emit(text[index : index + 60])

        draft = finalize_content("".join(collected), graph_context, triage_result)
        review = review_answer(
            question=payload.message,
            answer=draft,
            graph_context=graph_context,
            triage_result=triage_result,
        )
        full_text = review["content"]
        if full_text != draft:
            yield _sse({"revision": full_text})
        trace = {
            "entities": graph_context.get("entities", []),
            "graph": {
                "nodes": graph_context.get("nodes", [])[:42],
                "edges": graph_context.get("edges", [])[:60],
            },
            "triage": triage_result,
            "source_mode": source_mode,
            "model": model,
            "evidence_count": len(graph_context.get("facts", [])),
            "citations": graph_context.get("citations", []),
            "retrieval": graph_context.get("retrieval", {}),
            "intent": graph_context.get("intent", "general"),
            "has_image": bool(payload.image_data),
            "review": {
                key: value for key, value in review.items() if key != "content"
            },
            "metrics": {
                "retrieval_ms": retrieval_ms,
                "first_token_ms": first_token_ms
                if first_token_ms is not None
                else round((time.perf_counter() - started) * 1000, 2),
                "total_ms": round((time.perf_counter() - started) * 1000, 2),
                "stream_tokens": token_count,
                "answer_chars": len(full_text),
            },
            "tool_calls": [
                {
                    "name": "medical_graph.hybrid_search",
                    "status": "success",
                    "result_count": len(graph_context.get("entities", [])),
                    "duration_ms": retrieval_ms,
                },
                {
                    "name": "llm.stream_completion",
                    "status": "success",
                    "model": model,
                },
                {
                    "name": "reviewer.medical_quality_check",
                    "status": review["verdict"],
                    "result_count": review["issue_count"],
                },
            ],
        }
        db.add_message(conversation["id"], "assistant", full_text, trace)
        update_title = None
        if conversation["title"] == "新的健康咨询":
            update_title = re.sub(r"\s+", " ", payload.message).strip()[:32]
        db.update_conversation(
            conversation["id"],
            title=update_title,
            summary=summarize_history(
                conversation.get("summary", ""),
                payload.message,
                full_text,
            ),
            risk_level=triage_result["level"],
        )
        yield _sse(
            {
                "done": True,
                "conversation_id": conversation["id"],
                "review": trace["review"],
            }
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/vision")
def vision_analysis(
    payload: VisionRequest,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    try:
        result = analyze_image(
            validate_image_data(payload.image_data) or "",
            payload.question,
        )
    except DeepSeekError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        **result,
        "notice": "图片未保存；分析仅描述可见内容，不构成诊断。",
    }


@app.post("/api/vision/health-metrics")
def vision_health_metrics(
    payload: HealthMetricsVisionRequest,
    _: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    try:
        result = extract_health_metrics(
            validate_image_data(payload.image_data) or ""
        )
    except DeepSeekError as exc:
        raise HTTPException(
            status_code=503,
            detail="暂时无法识别图片，请稍后重试或手动填写",
        ) from exc
    return {
        **result,
        "notice": (
            "图片未保存。识别结果仅供表单预填，"
            "请核对每个读数后再保存。"
        ),
    }


def _age_from_birth_date(value: str | None) -> int | None:
    if not value:
        return None
    try:
        birth = datetime.strptime(value[:10], "%Y-%m-%d")
        now = datetime.now()
        return now.year - birth.year - (
            (now.month, now.day) < (birth.month, birth.day)
        )
    except (ValueError, TypeError):
        return None


@app.post("/api/triage")
def run_triage(
    payload: TriageRequest, user: dict[str, Any] = Depends(current_user)
) -> dict[str, Any]:
    if needs_input_guidance(payload.symptoms, history=[]):
        raise HTTPException(status_code=422, detail=INPUT_GUIDANCE)
    profile = db.get_health_profile(user["id"])
    profile_age = _age_from_birth_date(profile.get("birth_date"))
    analysis_age = payload.age if payload.age is not None else profile_age
    vitals = {
        "systolic": payload.systolic,
        "diastolic": payload.diastolic,
        "heart_rate": payload.heart_rate,
        "glucose": payload.glucose,
        "spo2": payload.spo2,
    }
    result = triage(
        payload.symptoms,
        duration_days=payload.duration_days,
        age=analysis_age,
        pregnancy=payload.pregnancy,
        vitals=vitals,
    )
    entities = medical_graph.extract_entities(payload.symptoms)
    result["graph_entities"] = entities
    result["medication_advice"] = recommend_medications(
        payload.symptoms,
        result,
        age=analysis_age,
        pregnancy=payload.pregnancy,
        allergies=profile.get("allergies", []),
        conditions=profile.get("conditions", []),
    )
    result["saved_event"] = db.add_triage_event(
        user["id"], payload.symptoms, result
    )
    return result


@app.get("/api/graph/overview")
def graph_overview(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return {
        "stats": medical_graph.stats(),
        "graph": medical_graph.showcase_graph(),
        "labels": medical_graph.stats().get("labels", []),
        "vector_index": vector_index.stats(),
    }


@app.get("/api/graph/search")
def graph_search(
    q: str = Query(min_length=1, max_length=80, default="高血压"),
    limit: int = Query(default=12, ge=1, le=30),
    _: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    return {
        "results": medical_graph.hybrid_search(q, limit),
        "query": q,
        "intent": medical_graph.detect_intent(q),
    }


@app.get("/api/graph/node/{node_id:path}")
def graph_neighborhood(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=2),
    _: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    return medical_graph.neighborhood(node_id, limit=42, depth=depth)


assets_dir = settings.frontend_dir / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
def index() -> FileResponse:
    path = settings.frontend_dir / "index.html"
    if not path.exists():
        raise HTTPException(status_code=500, detail="前端文件未安装")
    return FileResponse(path)


@app.get("/{path:path}")
def spa_fallback(path: str) -> FileResponse:
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="接口不存在")
    candidate = settings.frontend_dir / path
    if candidate.is_file() and settings.frontend_dir in candidate.resolve().parents:
        return FileResponse(candidate)
    return FileResponse(settings.frontend_dir / "index.html")

