from __future__ import annotations

import collections.abc
import json
import re
import urllib.error
import urllib.request
from typing import Any

from backend.config import settings
from backend.prompts import SYSTEM_PROMPT, VISION_SYSTEM_PROMPT, build_user_prompt


class DeepSeekError(RuntimeError):
    pass


def _call_deepseek(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    max_tokens: int = 1200,
) -> str:
    if not settings.deepseek_api_key:
        raise DeepSeekError("DEEPSEEK_API_KEY is not configured")
    payload = json.dumps(
        {
            "model": model or settings.deepseek_model,
            "messages": messages,
            "temperature": 0.15,
            "max_tokens": max_tokens,
            "top_p": 0.8,
            "stream": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{settings.deepseek_base_url}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=settings.deepseek_timeout
        ) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"].strip()
        if not content:
            raise DeepSeekError("DeepSeek returned an empty response")
        return content
    except urllib.error.HTTPError as exc:
        detail = exc.read(400).decode("utf-8", errors="ignore")
        raise DeepSeekError(f"DeepSeek HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as exc:
        raise DeepSeekError(f"DeepSeek request failed: {exc}") from exc


def stream_deepseek(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    max_tokens: int = 1200,
) -> collections.abc.Generator[str, None, None]:
    """Yield DeepSeek answer deltas from the streaming completions endpoint."""
    if not settings.deepseek_api_key:
        raise DeepSeekError("DEEPSEEK_API_KEY is not configured")
    payload = json.dumps(
        {
            "model": model or settings.deepseek_model,
            "messages": messages,
            "temperature": 0.15,
            "max_tokens": max_tokens,
            "top_p": 0.8,
            "stream": True,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{settings.deepseek_base_url}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.deepseek_api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=settings.deepseek_timeout
        ) as response:
            for raw_line in response:
                line = raw_line.strip()
                if not line or not line.startswith(b"data:"):
                    continue
                data_text = line[5:].strip().decode("utf-8", errors="ignore")
                if not data_text or data_text == "[DONE]":
                    if data_text == "[DONE]":
                        return
                    continue
                try:
                    chunk = json.loads(data_text)
                    delta = chunk["choices"][0].get("delta") or {}
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    continue
                piece = delta.get("content")
                if piece:
                    yield piece
    except urllib.error.HTTPError as exc:
        detail = exc.read(400).decode("utf-8", errors="ignore")
        raise DeepSeekError(f"DeepSeek HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise DeepSeekError(f"DeepSeek stream failed: {exc}") from exc


def finalize_content(
    content: str,
    graph_context: dict[str, Any],
    triage_result: dict[str, Any],
) -> str:
    """Apply citation validation and the emergency-opening guarantee."""
    cleaned = validate_citations(content, graph_context.get("citations", []))
    if triage_result["level"] == "emergency" and not re.search(
        r"120|急诊|立即就医", cleaned[:180]
    ):
        cleaned = (
            "**请立即拨打 120 或前往急诊。** 你描述的信息中存在需要优先排除的急症信号。\n\n"
            + cleaned
        )
    return cleaned


def answer_question(
    *,
    question: str,
    graph_context: dict[str, Any],
    history: list[dict[str, str]],
    summary: str,
    profile: dict[str, Any],
    triage: dict[str, Any],
    image_data: str | None = None,
) -> dict[str, Any]:
    prompt = build_user_prompt(
        question=question,
        graph_context=graph_context,
        history=history,
        summary=summary,
        profile=profile,
        triage=triage,
    )
    if settings.deepseek_api_key:
        try:
            if image_data:
                user_content: Any = [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data},
                    },
                ]
                model = settings.deepseek_vision_model
            else:
                user_content = prompt
                model = settings.deepseek_model
            content = _call_deepseek(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                model=model,
                max_tokens=1600 if image_data else 1200,
            )
            content = validate_citations(content, graph_context.get("citations", []))
            if triage["level"] == "emergency" and not re.search(
                r"120|急诊|立即就医", content[:180]
            ):
                content = (
                    "**请立即拨打 120 或前往急诊。** 你描述的信息中存在需要优先排除的急症信号。\n\n"
                    + content
                )
            return {
                "content": content,
                "source_mode": "deepseek-vision" if image_data else "deepseek",
                "model": model,
                "has_image": bool(image_data),
            }
        except DeepSeekError as exc:
            fallback = _grounded_answer(
                question, graph_context, triage, profile, str(exc)
            )
            fallback["source_mode"] = "grounded-fallback"
            fallback["model"] = "医疗知识图谱规则引擎"
            return fallback

    result = _grounded_answer(question, graph_context, triage, profile)
    result["source_mode"] = "grounded-demo"
    result["model"] = "医疗知识图谱规则引擎"
    return result


def analyze_image(image_data: str, question: str = "") -> dict[str, Any]:
    if not settings.deepseek_api_key:
        raise DeepSeekError("DEEPSEEK_API_KEY is not configured")
    prompt = (
        f"用户补充描述：{question.strip() or '请分析图中可见的健康相关信息。'}\n"
        "请只描述清晰可见的图像内容，不做确定诊断，不猜药物剂量。"
    )
    content = _call_deepseek(
        [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ],
            },
        ],
        model=settings.deepseek_vision_model,
        max_tokens=900,
    )
    return {
        "content": content,
        "model": settings.deepseek_vision_model,
        "source_mode": "deepseek-vision",
    }


HEALTH_METRIC_RANGES: dict[str, tuple[float, float, bool]] = {
    "systolic": (40, 300, True),
    "diastolic": (20, 200, True),
    "heart_rate": (20, 250, True),
    "glucose": (0, 40, False),
    "spo2": (50, 100, True),
    "weight_kg": (10, 400, False),
    "sleep_hours": (0, 24, False),
    "steps": (0, 200_000, True),
}


def extract_health_metrics(image_data: str) -> dict[str, Any]:
    """Extract structured smartwatch health readings from an uploaded image."""
    if not settings.deepseek_api_key:
        raise DeepSeekError("DEEPSEEK_API_KEY is not configured")
    prompt = """只提取图片中清晰可见的智能手表、健康 App 或体脂秤读数。
必须只返回一个 JSON 对象，不要 Markdown 代码块，不要解释。
可用字段及目标单位：
- systolic：收缩压，整数 mmHg
- diastolic：舒张压，整数 mmHg
- heart_rate：静息心率，整数 bpm
- glucose：血糖，数值 mmol/L
- spo2：血氧饱和度，整数百分比，不要带 % 符号
- weight_kg：体重，数值 kg
- sleep_hours：睡眠时长，数值小时
- steps：步数，整数
- confidence：high、medium 或 low
- notes：字符串数组，说明模糊、遮挡或单位转换情况

看不到或不确定的字段必须设为 null，不得猜测。不要输出诊断或建议。
如果图片中有明确日期，可额外返回 measured_at，格式为 ISO 8601。"""
    content = _call_deepseek(
        [
            {
                "role": "system",
                "content": (
                    "你是健康读数结构化识别器。只做可见数值转录，"
                    "不诊断、不推测、不补全模糊数字。"
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ],
            },
        ],
        model=settings.deepseek_vision_model,
        max_tokens=700,
    )
    payload = _parse_json_object(content)
    metrics: dict[str, int | float] = {}
    for key, (minimum, maximum, integer_only) in HEALTH_METRIC_RANGES.items():
        value = payload.get(key)
        if value is None or value == "":
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if integer_only and not number.is_integer():
            continue
        if not minimum <= number <= maximum:
            continue
        metrics[key] = int(number) if integer_only else round(number, 2)

    confidence = str(payload.get("confidence") or "low").strip().lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
    notes = payload.get("notes") or []
    if not isinstance(notes, list):
        notes = [str(notes)]
    cleaned_notes = [
        str(note).strip()[:180]
        for note in notes
        if str(note).strip()
    ][:8]
    measured_at = payload.get("measured_at")
    return {
        "metrics": metrics,
        "measured_at": str(measured_at)[:40] if measured_at else None,
        "confidence": confidence,
        "notes": cleaned_notes,
        "model": settings.deepseek_vision_model,
        "source_mode": "deepseek-vision-structured",
    }


def _parse_json_object(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise DeepSeekError("图片中未返回可识别的结构化数据")
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise DeepSeekError("图片读数格式无法解析") from exc
    if not isinstance(payload, dict):
        raise DeepSeekError("图片读数格式无法解析")
    return payload


def validate_citations(content: str, citations: list[dict[str, Any]]) -> str:
    valid = {item["id"] for item in citations}

    def replace(match: re.Match[str]) -> str:
        return match.group(0) if f"E{match.group(1)}" in valid else ""

    cleaned = re.sub(r"\[E(\d+)\]", replace, content).strip()
    if not citations:
        return cleaned
    if "引用依据" in cleaned:
        return cleaned
    used = {
        f"E{number}"
        for number in re.findall(r"\[E(\d+)\]", cleaned)
        if f"E{number}" in valid
    }
    reference_items = [
        item for item in citations if not used or item["id"] in used
    ][:8]
    if not reference_items:
        return cleaned
    lines = ["\n**引用依据**"]
    for item in reference_items:
        lines.append(
            f"- [{item['id']}] {item['subject']} — {item['predicate']} → {item['object']}"
        )
    return cleaned + "\n".join(lines)


def _prevention_items(
    context: dict[str, Any],
    target: str,
    *,
    limit: int = 5,
) -> list[str]:
    sections = context.get("sections", {})
    items = []
    for relation in ("注意事项", "禁忌", "预防措施", "不良反应"):
        for item in sections.get(relation, []):
            value = str(item).strip()
            if value and value not in items:
                items.append(value)
    if items:
        return items[:limit]

    if any(term in target for term in ("骨折", "扭伤", "拉伤", "外伤")):
        return [
            "避免跌倒和重复受伤，湿滑、昏暗或高低不平处要减速并保持照明。",
            "运动前充分热身，循序增加强度；高风险运动使用合适的护具。",
            "负重和发力动作保持稳定，出现疼痛、肿胀或活动受限时停止继续负重。",
            "中老年人或骨质疏松风险较高者，可与医生讨论骨密度和跌倒风险评估。",
        ][:limit]
    if any(term in target for term in ("感冒", "流感", "发热", "肺炎", "感染")):
        return [
            "勤洗手并保持室内通风，避免与明显呼吸道症状者近距离接触。",
            "在符合接种条件时按建议完成流感等疫苗，降低相应感染风险。",
            "保证睡眠、饮水和均衡饮食，不因短暂好转而过早恢复高强度活动。",
            "出现呼吸急促、持续高热或意识变化时及时就医，不要只靠自行用药掩盖症状。",
        ][:limit]
    if "高血压" in target:
        return [
            "按既定方案规律监测血压和服药，不自行停药或调整剂量。",
            "减少高盐饮食和过量饮酒，保持规律活动与稳定睡眠。",
            "出现持续胸痛、呼吸困难、肢体无力或说话不清时立即急诊。",
        ][:limit]
    if any(term in target for term in ("糖尿病", "高血糖", "低血糖")):
        return [
            "按计划监测血糖，规律进餐，避免漏餐或自行调整降糖方案。",
            "每天检查足部皮肤和伤口，选择合脚鞋袜，避免赤脚行走。",
            "随身准备低血糖应急措施，并让家人知道识别和处理方法。",
        ][:limit]
    return [
        "先避开已经明确的诱因、危险动作或接触因素，并记录每次出现前发生了什么。",
        "基础疾病按既定方案管理，不自行停药或叠加成分不明的药物。",
        "保持规律睡眠、饮食和适度活动；症状反复或进行性加重时及时就医评估。",
    ][:limit]


def _prevention_answer(
    question: str,
    context: dict[str, Any],
    triage_result: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    entities = context.get("entities", [])
    target = "、".join(
        entity.get("name", "") for entity in entities[:3] if entity.get("name")
    ) or question.strip("？?。 ")
    items = _prevention_items(context, target)
    lines = [
        f"**针对“{target}”，重点是从诱因、日常防护和风险信号三方面降低发生或加重风险。**",
        "",
        "**可以直接这样做**",
    ]
    lines.extend(f"- {item}" for item in items)
    if triage_result.get("red_flags"):
        lines.extend(
            [
                "",
                "**需要立即处理的表现**",
                f"- 本轮规则筛查识别到：{'、'.join(triage_result['red_flags'])}。",
            ]
        )
    lines.extend(
        [
            "",
            "**何时就医**",
            f"- {triage_result.get('action', '症状持续、反复或加重时，建议及时就医评估。')}",
            "- 出现呼吸困难、胸痛、意识改变、晕厥、大出血或快速进展的神经症状时，应立即急诊处理。",
            "",
            "以上为健康科普信息，不能替代医生诊断。",
        ]
    )
    if profile.get("allergies"):
        lines.insert(
            -2,
            f"**个性化提醒**\n档案记录过敏史：{'、'.join(profile['allergies'])}。",
        )
    return {
        "content": "\n".join(lines),
        "source_mode": "grounded-demo",
        "model": "医疗知识图谱规则引擎",
    }


def _cold_assessment_answer(
    context: dict[str, Any],
    triage_result: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    sections = context.get("sections", {})
    citations = context.get("citations", [])
    symptoms = [
        item
        for item in sections.get("症状与体征", [])
        if item and len(item) <= 16
    ][:6]
    symptom_text = "、".join(symptoms) if symptoms else "鼻塞、流涕、咽痛、咳嗽或发热"
    symptom_citations = []
    for citation in citations:
        if (
            citation.get("predicate") == "症状与体征"
            and citation.get("object") in symptoms
        ):
            symptom_citations.append(f"[{citation['id']}]")

    lines = [
        "**不能仅凭单一症状判断是不是普通感冒。** "
        f"更有价值的线索是症状组合和病程，例如同时出现 {symptom_text}，"
        "并结合起病速度、体温和近期接触史。"
        + (f" {' '.join(symptom_citations[:4])}" if symptom_citations else ""),
        "",
        "**可以这样自查**",
        "1. 记录最明显的 3–4 个症状，以及是否同时有鼻塞、流涕、咽痛、咳嗽或发热。",
        "2. 记录从出现到现在多久，体温最高多少，症状是在逐渐缓解还是持续加重。",
        "3. 注意是否突然起病。普通感冒与流感、新冠或过敏可能出现相似症状，单凭感觉不能确诊。",
        "4. 若服用过药物，记录名称、时间和效果，避免重复使用含相同成分的复方感冒药。",
        "",
        "**如何降低感染或传播风险**",
        *(
            f"- {item}"
            for item in _prevention_items(context, "普通感冒", limit=4)
        ),
        "",
        "**需要尽快就医的情况**",
        "- 呼吸困难、胸痛、意识改变、明显脱水，或高热持续不缓解。",
        "- 咽痛严重到无法吞咽、流口水，或伴单侧颈部明显肿痛。",
        "- 婴幼儿、孕妇、老年人或有心肺基础病者，症状加重时应降低就医门槛。",
    ]
    if triage_result.get("red_flags"):
        lines.append(
            f"- 本轮规则筛查识别到：{'、'.join(triage_result['red_flags'])}。"
        )
    if profile.get("allergies"):
        lines.append(
            f"\n**用药前提醒**\n档案记录过敏史：{'、'.join(profile['allergies'])}。"
            "购买或使用任何感冒药前，请主动告知医生或药师。"
        )
    lines.extend(
        [
            "",
            "**为了更准确判断，请再告诉我**",
            "- 你现在具体有哪些症状，最难受的是哪一个？",
            "- 已经持续多久，体温最高多少？",
            "- 是否有气短、胸痛、明显乏力，或近期接触过流感、新冠患者？",
            "",
            "以上为健康科普信息，不能替代医生诊断。",
        ]
    )
    if citations:
        lines.append("\n**引用依据**")
        for citation in citations[:6]:
            lines.append(
                f"- [{citation['id']}] {citation['subject']} — "
                f"{citation['predicate']} → {citation['object']}"
            )
    return {
        "content": "\n".join(lines),
        "source_mode": "grounded-demo",
        "model": "医疗知识图谱规则引擎",
    }


def _fever_assessment_answer(
    context: dict[str, Any],
    triage_result: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    citations = context.get("citations", [])
    citation_text = " ".join(f"[{item['id']}]" for item in citations[:3])
    lines = [
        "**判断是否发热，应以规范测量体温为准，不能只靠摸额头或主观发热感。**"
        "成人腋温达到 37.3 ℃通常提示发热；不同测量部位和体温计的阈值可能略有差异，"
        "请以设备说明为准。"
        + (f" {citation_text}" if citation_text else ""),
        "",
        "**自查顺序**",
        "1. 测量前安静休息 15–30 分钟，避免刚运动、洗热水澡或喝热饮后立即测量。",
        "2. 使用同一部位、同一台体温计复测一次，记录测量时间、部位和具体数值。",
        "3. 同时记录寒战、乏力、咽痛、咳嗽、鼻塞、腹泻、皮疹等症状，以及症状从何时开始。",
        "4. 体温升高并不等于已经确定病因，普通感染、流感、新冠及其他炎症都可能引起发热。",
        "",
        "**如何降低发生或传播风险**",
        *(
            f"- {item}"
            for item in _prevention_items(context, "发热", limit=4)
        ),
        "",
        "**出现以下情况应尽快就医**",
        "- 呼吸困难、胸痛、意识模糊、抽搐、明显脱水，或皮肤出现按压不褪色的出血点。",
        "- 高热持续不退、发热超过 3 天，或症状在短时间内明显加重。",
        "- 婴儿、孕妇、高龄者、免疫功能低下或有严重心肺基础病者，应降低就医门槛。",
    ]
    if triage_result.get("red_flags"):
        lines.append(
            f"- 本轮规则筛查还识别到：{'、'.join(triage_result['red_flags'])}。"
        )
    if profile.get("allergies"):
        lines.append(
            f"\n**用药提醒**\n档案记录过敏史：{'、'.join(profile['allergies'])}。"
            "使用退热药或复方感冒药前，请先让医生或药师核对成分与禁忌。"
        )
    lines.extend(
        [
            "",
            "**请告诉我这三项，我可以继续帮你判断风险**",
            "- 测得体温是多少，测量的是腋温、口温还是耳温？",
            "- 发热持续了多久，最高体温是多少？",
            "- 现在最明显的不适是什么，是否伴有气短、胸痛或意识异常？",
            "",
            "以上为健康科普信息，不能替代医生诊断。",
        ]
    )
    if citations:
        lines.append("\n**引用依据**")
        for citation in citations[:6]:
            lines.append(
                f"- [{citation['id']}] {citation['subject']} — "
                f"{citation['predicate']} → {citation['object']}"
            )
    return {
        "content": "\n".join(lines),
        "source_mode": "grounded-demo",
        "model": "医疗知识图谱规则引擎",
    }


def _general_assessment_answer(
    context: dict[str, Any],
    triage_result: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    entities = context.get("entities", [])
    entity_names = [
        entity.get("name", "") for entity in entities[:3] if entity.get("name")
    ]
    target = "、".join(entity_names) or "这种情况"
    sections = context.get("sections", {})
    citations = context.get("citations", [])
    symptoms = []
    for relation in ("症状与体征", "相关症状"):
        for item in sections.get(relation, []):
            if item and len(item) <= 20 and item not in symptoms:
                symptoms.append(item)
    symptom_text = "、".join(symptoms[:6]) or "与问题直接相关的典型表现"
    symptom_citations = [
        f"[{item['id']}]"
        for item in citations
        if item.get("predicate") in {"症状与体征", "相关症状"}
        and item.get("object") in symptoms[:6]
    ][:3]
    prevention_items = _prevention_items(context, target)

    lines = [
        f"**不能只凭一个感觉就判断是不是 {target}。** "
        f"更有价值的判断线索是：{symptom_text}是否同时出现，"
        "以及起病速度、持续时间、诱因和症状是否进行性加重。"
        + (f" {' '.join(symptom_citations)}" if symptom_citations else ""),
        "",
        "**可以按这个顺序自查**",
        f"1. 先确认最核心的表现：对照是否有{symptom_text}，记录每一项出现的时间和严重程度。",
        "2. 记录时间线：是突然出现还是逐渐发生，持续多久，什么动作、进食、接触或用药会加重或缓解。",
        "3. 检查伴随症状：是否同时有发热、呼吸困难、明显疼痛、意识变化、出血或无法正常进食饮水。",
        "4. 记录近期接触史、既往病史、正在使用的药物和过敏史，这些信息可能改变判断和就医优先级。",
        "",
        "**如何降低发生或加重风险**",
        *(f"- {item}" for item in prevention_items),
        "",
        "**不建议这样做**",
        "- 不根据单一症状或网络搜索直接给自己下诊断。",
        "- 不自行叠加成分相同的复方药，也不因暂时缓解而延迟处理持续加重的症状。",
    ]
    if triage_result.get("red_flags"):
        lines.extend(
            [
                "",
                "**需要立即处理的表现**",
                f"- 本轮规则筛查识别到：{'、'.join(triage_result['red_flags'])}。",
            ]
        )
    lines.extend(
        [
            "",
            "**何时就医**",
            f"- {triage_result.get('action', '症状持续或加重时，建议及时就医评估。')}",
            "- 出现呼吸困难、胸痛、意识改变、晕厥、大出血或快速进展的神经症状时，应立即急诊处理。",
            "",
            "**请补充这三项**",
            "- 你现在具体有哪些症状，最明显的是哪一个？",
            "- 症状已经持续多久，是逐渐加重还是正在缓解？",
            "- 年龄、既往病史、正在使用的药物和药物过敏史。",
        ]
    )
    if profile.get("allergies"):
        lines.append(
            f"\n**个性化提醒**\n档案记录过敏史：{'、'.join(profile['allergies'])}。"
            "就诊或用药前请主动告知医生。"
        )
    lines.append("\n以上为健康科普信息，不能替代医生诊断。")
    if citations:
        lines.append("\n**引用依据**")
        for citation in citations[:6]:
            lines.append(
                f"- [{citation['id']}] {citation['subject']} — "
                f"{citation['predicate']} → {citation['object']}"
            )
    return {
        "content": "\n".join(lines),
        "source_mode": "grounded-demo",
        "model": "医疗知识图谱规则引擎",
    }


def _grounded_answer(
    question: str,
    context: dict[str, Any],
    triage_result: dict[str, Any],
    profile: dict[str, Any],
    error_hint: str | None = None,
) -> dict[str, Any]:
    entities = context.get("entities", [])
    entity_names = []
    for entity in entities[:4]:
        if entity["name"] not in entity_names:
            entity_names.append(entity["name"])
    sections = context.get("sections", {})
    citations = context.get("citations", [])
    retrieval = context.get("retrieval", {})
    clarification = context.get("clarification")

    entity_names_lower = {entity.get("name", "") for entity in entities}
    if context.get("intent") == "prevention" and triage_result["level"] != "emergency":
        return _prevention_answer(question, context, triage_result, profile)
    if context.get("intent") == "assessment" and triage_result["level"] != "emergency":
        if "普通感冒" in entity_names_lower:
            return _cold_assessment_answer(context, triage_result, profile)
        if "发热" in entity_names_lower or re.search(r"发烧|发热", question):
            return _fever_assessment_answer(context, triage_result, profile)
        return _general_assessment_answer(context, triage_result, profile)

    if triage_result["level"] == "emergency":
        opening = (
            "**请立即拨打 120 或前往急诊。** "
            f"你描述的信息中识别到：{'、'.join(triage_result['red_flags'])}。"
        )
    elif triage_result["level"] == "high":
        opening = (
            "根据你描述的信息，建议尽快联系医生或前往门诊评估。"
            "如果症状加重，请立即就医。"
        )
    elif entities:
        opening = (
            f"从当前描述看，与 **{'、'.join(entity_names[:3])}** 相关的信息值得关注。"
            "图谱命中只能作为健康知识线索，不能据此作出诊断。"
        )
    else:
        opening = (
            "当前描述尚未明确命中图谱实体，现有证据不足以判断具体原因。"
            "建议先记录症状变化和生命体征。"
        )

    lines = [opening]
    if triage_result["symptoms"]:
        lines.append(
            "\n**已识别的健康信号**\n"
            + "、".join(triage_result["symptoms"])
            + "。"
        )

    if sections:
        heading = (
            "\n**图谱提供的间接线索（二跳关系，需谨慎参考）**"
            if retrieval.get("evidence_level") == "indirect"
            else "\n**图谱提供的信息线索**"
        )
        lines.append(heading)
        relation_order = [
            "症状与体征",
            "相关症状",
            "可能病因",
            "就诊科室",
            "相关检查",
            "并发症",
            "注意事项",
        ]
        used = 0
        for relation in relation_order:
            values = sections.get(relation)
            if values:
                citation_ids = [
                    item["id"]
                    for item in citations
                    if item["predicate"] == relation and item["object"] in values[:5]
                ][:3]
                suffix = f" {' '.join(f'[{cid}]' for cid in citation_ids)}" if citation_ids else ""
                lines.append(f"- {relation}：" + "、".join(values[:5]) + suffix)
                used += 1
            if used >= 4:
                break

    if clarification:
        lines.append("\n**需要你补充的信息**")
        for item in clarification.get("needed", [])[:4]:
            lines.append(f"- {item}")

    if profile.get("allergies"):
        lines.append(
            "\n**个性化提醒**\n"
            f"档案记录过敏史：{'、'.join(profile['allergies'])}。就诊或用药前请主动告知医生。"
        )

    if triage_result["red_flags"]:
        lines.append(
            "\n**需要立即处理的表现**\n"
            + "、".join(triage_result["red_flags"])
            + "。"
        )

    lines.append(
        "\n**建议下一步**\n"
        f"- {triage_result['action']}\n"
        f"- 可优先咨询：{'、'.join(triage_result['departments'][:2])}。\n"
        "- 记录症状出现时间、持续时长、诱因及伴随表现，便于医生判断。"
    )
    if error_hint:
        lines.append(
            "\n> 智能模型暂未连接成功，本回答由本地图谱证据和风险规则生成。"
        )
    lines.append("\n以上为健康科普信息，不能替代医生诊断。")
    if citations:
        lines.append("\n**引用依据**")
        for item in citations[:6]:
            lines.append(
                f"- [{item['id']}] {item['subject']} — {item['predicate']} → {item['object']}"
            )
    return {
        "content": "\n".join(lines),
        "source_mode": "grounded-demo",
        "model": "医疗知识图谱规则引擎",
    }


def summarize_history(
    previous_summary: str,
    question: str,
    answer: str,
) -> str:
    clean_answer = re.sub(r"[#*>`]", "", answer)
    compact_answer = re.sub(r"\s+", " ", clean_answer).strip()[:180]
    new_summary = (
        f"用户咨询：{question.strip()[:140]}；"
        f"回复要点：{compact_answer}"
    )
    if previous_summary:
        return f"{previous_summary[-260:]}。后续：{new_summary}"[-900:]
    return new_summary[:900]

