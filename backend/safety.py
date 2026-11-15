from __future__ import annotations

import re
from datetime import datetime
from statistics import mean, pstdev
from typing import Any


EMERGENCY_PATTERNS = [
    (r"胸痛.{0,12}(呼吸困难|喘不上气)|呼吸困难.{0,12}胸痛", "胸痛伴呼吸困难"),
    (r"意识不清|昏迷|叫不醒|突然昏倒|晕厥", "意识障碍或晕厥"),
    (r"口角歪斜|单侧.{0,5}(无力|麻木)|半边.{0,5}(无力|麻木)", "卒中样表现"),
    (r"说话不清|言语不清|不能说话", "言语障碍"),
    (r"大出血|血流不止|呕血|大量便血", "活动性出血"),
    (r"抽搐|惊厥", "抽搐发作"),
    (r"喉咙.{0,8}(肿|紧)|严重过敏|过敏性休克", "严重过敏风险"),
    (r"呼吸困难|喘不上气", "呼吸困难"),
    (r"自杀|轻生|不想活|伤害自己", "自伤风险"),
    (r"孕.{0,10}(大出血|剧烈腹痛|胎动减少)", "孕产急症"),
]

URGENT_PATTERNS = [
    (r"38\.5|39度|40度|持续高烧|高热", "高热"),
    (r"剧烈头痛|突然头痛", "剧烈或突发头痛"),
    (r"持续呕吐|无法进食|脱水", "持续呕吐或脱水"),
    (r"视力突然|看不清|视野缺损", "突发视觉异常"),
    (r"儿童|婴儿|孕妇|老人", "特殊人群"),
]

SYMPTOM_TERMS = [
    "头晕",
    "眩晕",
    "头痛",
    "发热",
    "咳嗽",
    "胸闷",
    "胸痛",
    "心悸",
    "呼吸困难",
    "腹痛",
    "腹泻",
    "恶心",
    "呕吐",
    "乏力",
    "失眠",
    "皮疹",
    "瘙痒",
    "水肿",
    "麻木",
    "视物模糊",
    "耳鸣",
    "咽痛",
    "咽痒",
    "鼻塞",
    "流涕",
    "打喷嚏",
    "咳痰",
    "声音嘶哑",
    "肌肉酸痛",
    "反酸",
    "烧心",
    "感冒样症状",
]


def recognize_symptoms(text: str) -> list[str]:
    canonical = [
        term
        for term in SYMPTOM_TERMS
        if term != "感冒样症状" and term in text
    ]
    aliases = {
        "嗓子疼": "咽痛",
        "喉咙痛": "咽痛",
        "嗓子痒": "咽痒",
        "喉咙痒": "咽痒",
        "流鼻涕": "流涕",
        "打喷涕": "打喷嚏",
        "全身酸痛": "肌肉酸痛",
        "胃反酸": "反酸",
        "胃部灼热": "烧心",
        "拉肚子": "腹泻",
    }
    for alias, term in aliases.items():
        if alias in text and term not in canonical:
            canonical.append(term)
    if re.search(r"嗓子.{0,8}痒|喉咙.{0,8}痒", text) and "咽痒" not in canonical:
        canonical.append("咽痒")
    if re.search(r"感冒|着凉|受凉", text):
        canonical.append("感冒样症状")
    found = list(dict.fromkeys(canonical))
    if "喘不上气" in text and "呼吸困难" not in found:
        found.append("呼吸困难")
    if "发烧" in text and "发热" not in found:
        found.append("发热")
    return found


def triage(
    symptoms_text: str,
    *,
    duration_days: int | None = None,
    age: int | None = None,
    pregnancy: bool = False,
    vitals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = symptoms_text or ""
    vitals = vitals or {}
    red_flags: list[str] = []
    urgency_reasons: list[str] = []

    for pattern, label in EMERGENCY_PATTERNS:
        if re.search(pattern, text):
            red_flags.append(label)
    for pattern, label in URGENT_PATTERNS:
        if re.search(pattern, text):
            urgency_reasons.append(label)

    if pregnancy:
        urgency_reasons.append("孕期")
    if age is not None and (age < 5 or age >= 70):
        urgency_reasons.append("低龄或高龄")

    score = 0
    score += len(red_flags) * 40
    score += len(urgency_reasons) * 12
    symptoms = recognize_symptoms(text)
    symptom_score = min(len(symptoms) * 4, 24)
    if len(symptoms) >= 2:
        symptom_score += 4
    score += symptom_score
    if duration_days is not None and duration_days >= 14:
        score += 10

    vital_alerts = analyze_vitals(vitals)
    score += sum(18 for alert in vital_alerts if alert["severity"] == "high")
    score += sum(8 for alert in vital_alerts if alert["severity"] == "medium")
    score = min(score, 100)

    if red_flags or score >= 75:
        level = "emergency"
        title = "建议立即就医"
        subtitle = "检测到需要优先排除的急症信号"
        action = "请立即拨打 120 或前往最近的急诊。不要独自驾车。"
    elif score >= 38 or urgency_reasons:
        level = "high"
        title = "建议尽快就医"
        subtitle = "存在需要医生进一步评估的风险因素"
        action = "建议在 24 小时内联系医生或前往门诊；症状加重时立即急诊。"
    elif score >= 16:
        level = "medium"
        title = "建议持续观察"
        subtitle = "当前信息未提示明确急症，但需要监测变化"
        action = "记录症状与生命体征；若持续不缓解或出现红旗症状，及时就医。"
    else:
        level = "low"
        title = "暂时可居家观察"
        subtitle = "未识别到明显急症信号"
        action = "注意休息与补水，继续记录变化；不缓解时咨询医生。"

    departments = suggest_departments(text, age, pregnancy)
    return {
        "level": level,
        "score": score,
        "title": title,
        "subtitle": subtitle,
        "action": action,
        "red_flags": list(dict.fromkeys(red_flags)),
        "urgency_reasons": list(dict.fromkeys(urgency_reasons)),
        "symptoms": recognize_symptoms(text),
        "duration_days": duration_days,
        "vital_alerts": vital_alerts,
        "departments": departments,
        "disclaimer": "分诊结果为规则辅助判断，不构成医学诊断；急症请立即呼叫急救。",
    }


def analyze_vitals(vitals: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    def number(key: str) -> float | None:
        value = vitals.get(key)
        try:
            return float(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    systolic = number("systolic")
    diastolic = number("diastolic")
    heart_rate = number("heart_rate")
    glucose = number("glucose")
    spo2 = number("spo2")

    if systolic is not None and (systolic >= 180 or systolic < 80):
        alerts.append(
            {
                "metric": "收缩压",
                "value": systolic,
                "severity": "high",
                "message": "收缩压处于明显异常范围",
            }
        )
    elif systolic is not None and systolic >= 140:
        alerts.append(
            {
                "metric": "收缩压",
                "value": systolic,
                "severity": "medium",
                "message": "收缩压偏高，建议复测并记录",
            }
        )
    if diastolic is not None and diastolic >= 120:
        alerts.append(
            {
                "metric": "舒张压",
                "value": diastolic,
                "severity": "high",
                "message": "舒张压明显偏高",
            }
        )
    if heart_rate is not None and (heart_rate > 120 or heart_rate < 45):
        alerts.append(
            {
                "metric": "心率",
                "value": heart_rate,
                "severity": "high",
                "message": "静息心率明显异常",
            }
        )
    if glucose is not None and (glucose >= 16.7 or glucose < 3.5):
        alerts.append(
            {
                "metric": "血糖",
                "value": glucose,
                "severity": "high",
                "message": "血糖处于明显异常范围",
            }
        )
    if spo2 is not None and spo2 < 92:
        alerts.append(
            {
                "metric": "血氧",
                "value": spo2,
                "severity": "high",
                "message": "血氧饱和度偏低",
            }
        )
    return alerts


def suggest_departments(
    text: str, age: int | None, pregnancy: bool
) -> list[str]:
    if pregnancy:
        return ["产科", "急诊医学科（急症时）"]
    if age is not None and age < 14:
        return ["儿科", "急诊医学科（急症时）"]
    if re.search(r"胸痛|心悸|胸闷|血压", text):
        return ["心血管内科", "急诊医学科（胸痛持续时）"]
    if re.search(r"头晕|麻木|说话不清|头痛", text):
        return ["神经内科", "急诊医学科（突发症状时）"]
    if re.search(r"腹痛|腹泻|恶心|呕吐|胃", text):
        return ["消化内科"]
    if re.search(r"咳嗽|发热|呼吸困难|喘", text):
        return ["呼吸内科"]
    if re.search(r"皮疹|瘙痒|皮肤", text):
        return ["皮肤科"]
    if re.search(r"月经|痛经|孕", text):
        return ["妇科"]
    return ["全科医学科"]


SYMPTOM_GROUPS: dict[str, list[str]] = {
    "头晕头痛": ["头晕", "头痛", "眩晕", "偏头痛"],
    "睡眠相关": ["失眠", "睡不着", "入睡困难", "熬夜"],
    "心肺不适": ["心慌", "心悸", "胸闷", "气短", "胸痛"],
    "消化道不适": ["胃痛", "腹痛", "反酸", "腹泻", "恶心"],
}


def _date_key(value: str | None) -> str:
    return (value or "")[:10]


def longitudinal_insights(
    records: list[dict[str, Any]],
    conversations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Correlate consultation topics with same-day vitals and sleep.

    This surfaces patterns such as "dizziness reported on days following
    short sleep" using only data the user already recorded. It never infers
    a diagnosis and stays silent when there is not enough evidence.
    """
    if not records or not conversations:
        return []

    by_date: dict[str, dict[str, Any]] = {}
    for record in records:
        key = _date_key(record.get("measured_at"))
        if key:
            by_date.setdefault(key, record)

    buckets: dict[str, dict[str, Any]] = {}
    for conversation in conversations:
        title = conversation.get("title") or ""
        date = _date_key(conversation.get("updated_at"))
        if not date:
            continue
        matched = [
            group
            for group, terms in SYMPTOM_GROUPS.items()
            if any(term in title for term in terms)
        ]
        if not matched:
            continue
        for group in matched:
            entry = buckets.setdefault(
                group, {"count": 0, "dates": set(), "low_sleep": 0, "high_bp": 0}
            )
            entry["count"] += 1
            entry["dates"].add(date)
            record = by_date.get(date)
            if record:
                sleep = record.get("sleep_hours")
                systolic = record.get("systolic")
                if sleep is not None and float(sleep) < 6.5:
                    entry["low_sleep"] += 1
                if systolic is not None and float(systolic) >= 140:
                    entry["high_bp"] += 1

    insights: list[dict[str, Any]] = []
    for group, entry in buckets.items():
        if entry["count"] < 2:
            continue
        details: list[str] = []
        if entry["low_sleep"]:
            details.append(f"{entry['low_sleep']} 次与睡眠不足 6.5 小时同日出现")
        if entry["high_bp"]:
            details.append(f"{entry['high_bp']} 次与收缩压 ≥140 毫米汞柱同日出现")
        if not details:
            details.append("多次出现在咨询记录中，建议持续观察")
        insights.append(
            {
                "title": group,
                "detail": f"近 {len(entry['dates'])} 天记录到 {entry['count']} 次相关咨询，"
                + "；".join(details) + "。",
                "severity": "medium" if (entry["low_sleep"] or entry["high_bp"]) else "low",
                "evidence": {
                    "consultations": entry["count"],
                    "days": len(entry["dates"]),
                    "low_sleep_days": entry["low_sleep"],
                    "high_bp_days": entry["high_bp"],
                },
            }
        )
    insights.sort(key=lambda item: item["evidence"]["consultations"], reverse=True)
    return insights[:3]


def health_overview(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "score": 82,
            "status": "等待数据",
            "latest": {},
            "trends": {},
            "alerts": [],
            "insight": "添加第一条健康记录后，系统会开始识别趋势与异常。",
        }

    latest = records[0]
    trends: dict[str, dict[str, Any]] = {}
    series_ranges = {
        "systolic": (90, 140),
        "diastolic": (60, 90),
        "heart_rate": (50, 100),
        "glucose": (3.9, 11.1),
        "spo2": (94, 100),
        "sleep_hours": (7, 9),
    }
    score = 100
    alerts = analyze_vitals(latest)
    score -= sum(16 for alert in alerts if alert["severity"] == "high")
    score -= sum(9 for alert in alerts if alert["severity"] == "medium")

    for key, (low, high) in series_ranges.items():
        values = [
            float(row[key])
            for row in records
            if row.get(key) not in (None, "")
        ]
        if not values:
            continue
        current = values[0]
        baseline = mean(values[-7:])
        deviation = abs(current - baseline)
        sigma = pstdev(values[-7:]) if len(values) > 1 else 0
        in_range = low <= current <= high
        if not in_range:
            score -= 4
        trends[key] = {
            "current": current,
            "baseline": round(baseline, 1),
            "delta": round(current - baseline, 1),
            "direction": "up" if current > baseline else "down",
            "sigma": round(sigma, 2),
            "deviation": round(deviation, 2),
        }

    sleep_values = [
        float(row["sleep_hours"])
        for row in records[-7:]
        if row.get("sleep_hours") is not None
    ]
    if sleep_values and mean(sleep_values) < 7:
        score -= 5
        alerts.append(
            {
                "metric": "睡眠",
                "value": round(mean(sleep_values), 1),
                "severity": "medium",
                "message": "近 7 天平均睡眠不足 7 小时",
            }
        )

    score = max(40, min(100, int(round(score))))
    if score >= 88:
        status = "状态稳定"
        insight = "近 7 天核心指标总体平稳，继续保持规律作息并记录变化。"
    elif score >= 72:
        status = "需要关注"
        insight = "部分指标存在波动，建议连续复测并结合症状变化观察。"
    else:
        status = "建议咨询"
        insight = "健康信号出现持续偏离，建议携带记录咨询医生。"

    if latest.get("sleep_hours") and latest["sleep_hours"] < 7:
        leading = "昨晚睡眠偏少"
    elif alerts:
        leading = alerts[0]["message"]
    else:
        leading = "生命体征整体平稳"

    return {
        "score": score,
        "status": status,
        "latest": latest,
        "trends": trends,
        "alerts": alerts,
        "insight": insight,
        "headline": leading,
        "updated_at": datetime.now().astimezone().isoformat(),
    }

