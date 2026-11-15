from __future__ import annotations

import hashlib
import hmac
import html
import secrets
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from typing import Any

from backend.config import settings


class EmailConfigurationError(RuntimeError):
    """Raised when outbound email has not been configured."""


class EmailDeliveryError(RuntimeError):
    """Raised when the configured mail server rejects a message."""


def email_configured() -> bool:
    return bool(settings.smtp_host.strip() and settings.smtp_from.strip())


def make_reset_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def reset_code_digest(email: str, code: str) -> str:
    payload = f"{email.strip().lower()}:{code.strip()}".encode("utf-8")
    return hmac.new(
        settings.app_secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()


def send_email(
    recipient: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    if not email_configured():
        raise EmailConfigurationError("邮件服务尚未配置")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.smtp_from_name, settings.smtp_from))
    message["To"] = recipient
    message["Date"] = formatdate(localtime=False)
    domain = settings.smtp_from.rsplit("@", 1)[-1] or None
    message["Message-ID"] = make_msgid(domain=domain)
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        if settings.smtp_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout,
            ) as client:
                if settings.smtp_username:
                    client.login(settings.smtp_username, settings.smtp_password)
                client.send_message(message)
            return

        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout,
        ) as client:
            client.ehlo()
            if settings.smtp_starttls:
                client.starttls()
                client.ehlo()
            if settings.smtp_username:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("邮件发送失败，请稍后重试") from exc


def send_registration_email(user: dict[str, Any]) -> None:
    name = user.get("name") or "用户"
    email = user["email"]
    created_at = _friendly_datetime(user.get("created_at"))
    login_url = settings.public_base_url.rstrip("/")
    text_body = "\n".join(
        [
            f"{name}，欢迎使用知衡健康。",
            "",
            "你的账户已注册成功。",
            f"登录邮箱：{email}",
            f"注册时间：{created_at}",
            f"登录地址：{login_url}",
            "",
            "为保护账户安全，系统不会通过邮件发送明文密码。",
            "如非本人操作，请立即联系平台管理员。",
            "",
            "知衡健康提供健康科普与风险提示，不替代医生诊断。",
        ]
    )
    html_body = _email_shell(
        "账户注册成功",
        f"<p>{html.escape(name)}，欢迎使用知衡健康。</p>"
        "<p>你的账户已经创建，可使用以下信息登录：</p>"
        f"<p><strong>登录邮箱：</strong>{html.escape(email)}<br>"
        f"<strong>注册时间：</strong>{html.escape(created_at)}</p>"
        f'<p><a href="{html.escape(login_url)}">进入知衡健康</a></p>'
        "<p class=\"muted\">为保护账户安全，系统不会通过邮件发送明文密码。"
        "如非本人操作，请立即联系平台管理员。</p>",
    )
    send_email(email, "知衡健康账户注册成功", text_body, html_body)


def send_password_reset_email(
    user: dict[str, Any], code: str, expires_minutes: int
) -> None:
    name = user.get("name") or "用户"
    text_body = "\n".join(
        [
            f"{name}，你正在重置知衡健康账户密码。",
            "",
            f"邮箱验证码：{code}",
            f"有效期：{expires_minutes} 分钟，仅可使用一次。",
            "",
            "如果这不是你的操作，请忽略本邮件，不要向任何人提供验证码。",
        ]
    )
    html_body = _email_shell(
        "重置登录密码",
        f"<p>{html.escape(name)}，你正在重置知衡健康账户密码。</p>"
        f"<p class=\"code\">{html.escape(code)}</p>"
        f"<p>验证码 {expires_minutes} 分钟内有效，且只能使用一次。</p>"
        "<p class=\"muted\">如果这不是你的操作，请忽略本邮件，"
        "不要向任何人提供验证码。</p>",
    )
    send_email(user["email"], "知衡健康密码重置验证码", text_body, html_body)


def send_health_report_email(
    user: dict[str, Any],
    report_type: str,
    report: dict[str, Any],
) -> None:
    if report_type == "visit_summary":
        title = "就诊前健康摘要"
        text_body = str(report.get("summary") or "")
        body_html = _summary_to_html(text_body)
    else:
        title = "健康证据护照"
        text_body = _passport_to_text(report)
        body_html = _passport_to_html(report)

    html_body = _email_shell(
        title,
        f"<p>{html.escape(user.get('name') or '用户')}，以下是你在知衡健康生成的{title}。</p>"
        f"{body_html}",
    )
    send_email(
        user["email"],
        f"知衡健康 · {title}",
        text_body,
        html_body,
    )


def _friendly_datetime(value: Any) -> str:
    if not value:
        return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    try:
        return datetime.fromisoformat(str(value)).astimezone().strftime(
            "%Y-%m-%d %H:%M"
        )
    except (TypeError, ValueError):
        return str(value)


def _email_shell(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<body style="margin:0;background:#edf5f1;color:#17372d;font-family:'Microsoft YaHei',Arial,sans-serif;line-height:1.75">
  <div style="max-width:620px;margin:28px auto;padding:0 16px">
    <div style="padding:26px 28px;border-radius:18px;background:#0a2119;color:#effbf6">
      <div style="color:#79e5ba;font-size:12px;letter-spacing:2px">ZHI HENG CARE</div>
      <h1 style="margin:8px 0 0;font-size:24px;font-weight:600">{html.escape(title)}</h1>
    </div>
    <div style="margin-top:16px;padding:26px 28px;border:1px solid #d8e6df;border-radius:18px;background:#fff">
      {content}
      <p style="margin:24px 0 0;padding-top:16px;border-top:1px solid #e4eee9;color:#667b72;font-size:12px">
        本邮件由知衡健康自动发送。健康信息仅供科普和就诊沟通参考，不替代专业诊断。
      </p>
    </div>
  </div>
  <style>
    a{{color:#16845f}} p{{margin:10px 0}} .muted{{color:#6c8077;font-size:13px}}
    .code{{margin:22px 0;padding:16px;border-radius:12px;background:#eaf8f1;color:#126a4d;font-size:30px;font-weight:700;letter-spacing:8px;text-align:center}}
    h2{{margin:22px 0 8px;font-size:17px}} ul{{padding-left:20px}} li{{margin:6px 0}}
  </style>
</body>
</html>"""


def _summary_to_html(summary: str) -> str:
    parts: list[str] = []
    in_list = False
    for raw_line in summary.splitlines():
        line = raw_line.strip()
        if line.startswith("- "):
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{html.escape(line[2:])}</li>")
            continue
        if in_list:
            parts.append("</ul>")
            in_list = False
        if not line:
            continue
        if line.startswith("# "):
            parts.append(f"<h2>{html.escape(line[2:])}</h2>")
        elif line.startswith("## "):
            parts.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("> "):
            parts.append(
                f"<p class=\"muted\">{html.escape(line[2:])}</p>"
            )
        else:
            parts.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        parts.append("</ul>")
    return "".join(parts)


def _passport_to_text(report: dict[str, Any]) -> str:
    profile = report.get("profile") or {}
    overview = report.get("overview") or {}
    latest = overview.get("latest") or {}
    timeline = report.get("timeline") or []
    consultations = report.get("recent_consultations") or []
    lines = [
        f"健康证据护照 - {report.get('owner', {}).get('name', '用户')}",
        f"生成时间：{_friendly_datetime(report.get('generated_at'))}",
        "",
        f"健康状态：{overview.get('status', '等待数据')}",
        f"健康评分：{overview.get('score', 0)} / 100",
        f"健康洞察：{overview.get('insight', '')}",
        "",
        f"基础疾病：{'、'.join(profile.get('conditions') or []) or '无记录'}",
        f"过敏史：{'、'.join(profile.get('allergies') or []) or '无记录'}",
        f"长期用药：{'、'.join(profile.get('medications') or []) or '无记录'}",
        "",
        "最近体征：",
        f"血压 {latest.get('systolic', '—')}/{latest.get('diastolic', '—')} 毫米汞柱，"
        f"心率 {latest.get('heart_rate', '—')} 次/分，"
        f"睡眠 {latest.get('sleep_hours', '—')} 小时",
        "",
        "近期健康事件：",
    ]
    lines.extend(
        f"- {event.get('occurred_at', '')[:10]} {event.get('title', '')}："
        f"{event.get('description', '')}"
        for event in timeline[:20]
    )
    if not timeline:
        lines.append("- 暂无记录")
    lines.extend(["", "近期咨询："])
    lines.extend(
        f"- {item.get('title', '健康咨询')}" for item in consultations[:10]
    )
    if not consultations:
        lines.append("- 暂无记录")
    lines.extend(["", str(report.get("disclaimer") or "")])
    return "\n".join(lines)


def _passport_to_html(report: dict[str, Any]) -> str:
    profile = report.get("profile") or {}
    overview = report.get("overview") or {}
    latest = overview.get("latest") or {}
    timeline = report.get("timeline") or []
    consultations = report.get("recent_consultations") or []
    events = "".join(
        f"<li><strong>{html.escape(str(event.get('title', '')))}</strong>"
        f"<br>{html.escape(str(event.get('description', '')))}"
        f"<br><span class=\"muted\">{html.escape(str(event.get('occurred_at', ''))[:10])}"
        f" · {html.escape(str(event.get('source', '')))}</span></li>"
        for event in timeline[:20]
    ) or "<li>暂无记录</li>"
    consultation_items = "".join(
        f"<li>{html.escape(str(item.get('title', '健康咨询')))}</li>"
        for item in consultations[:10]
    ) or "<li>暂无记录</li>"
    return (
        f"<h2>健康概况</h2><p><strong>{html.escape(str(overview.get('status', '等待数据')))}"
        f"</strong> · 健康评分 {int(overview.get('score') or 0)} / 100</p>"
        f"<p>{html.escape(str(overview.get('insight', '')))}</p>"
        "<h2>健康档案</h2>"
        f"<p><strong>基础疾病：</strong>{_join_items(profile.get('conditions'))}</p>"
        f"<p><strong>过敏史：</strong>{_join_items(profile.get('allergies'))}</p>"
        f"<p><strong>长期用药：</strong>{_join_items(profile.get('medications'))}</p>"
        "<h2>最近体征</h2>"
        f"<p>血压 {html.escape(str(latest.get('systolic', '—')))}/"
        f"{html.escape(str(latest.get('diastolic', '—')))} 毫米汞柱，"
        f"心率 {html.escape(str(latest.get('heart_rate', '—')))} 次/分，"
        f"睡眠 {html.escape(str(latest.get('sleep_hours', '—')))} 小时</p>"
        f"<h2>近期健康事件</h2><ul>{events}</ul>"
        f"<h2>近期咨询</h2><ul>{consultation_items}</ul>"
        f"<p class=\"muted\">{html.escape(str(report.get('disclaimer') or ''))}</p>"
    )


def _join_items(values: Any) -> str:
    return "、".join(html.escape(str(item)) for item in (values or [])) or "无记录"
