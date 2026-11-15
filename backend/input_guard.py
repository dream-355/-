from __future__ import annotations

import re

from backend.graph import KEY_TERMS


INPUT_GUIDANCE = """请描述您的症状、持续时间和伴随表现，我会据此继续判断。

例如可以这样写：
- 哪个部位不舒服，是疼痛、瘙痒、麻木、肿胀还是其他感觉？
- 症状从什么时候开始，已经持续多久，是否逐渐加重？
- 是否伴有发热、咳嗽、胸闷、恶心、呕吐、腹泻、头晕或乏力？
- 是否有相关病史、正在使用的药物或药物过敏史？

也可以上传检查报告、伤口、皮疹或药品包装图片。紧急情况下请直接拨打 120。"""

HEALTH_SIGNALS = (
    "症状",
    "不舒服",
    "疼痛",
    "疼",
    "痛",
    "酸",
    "痒",
    "麻",
    "肿",
    "晕",
    "咳",
    "喘",
    "痰",
    "发热",
    "发烧",
    "体温",
    "感冒",
    "流感",
    "感染",
    "发炎",
    "炎症",
    "过敏",
    "皮疹",
    "红斑",
    "伤口",
    "出血",
    "恶心",
    "呕吐",
    "腹泻",
    "便秘",
    "腹痛",
    "胸闷",
    "心悸",
    "心慌",
    "气短",
    "呼吸困难",
    "乏力",
    "疲劳",
    "失眠",
    "睡不着",
    "焦虑",
    "抑郁",
    "心情",
    "血压",
    "血糖",
    "血脂",
    "心率",
    "血氧",
    "体检",
    "检查",
    "化验",
    "报告",
    "指标",
    "疾病",
    "病",
    "药",
    "治疗",
    "缓解",
    "医院",
    "医生",
    "科室",
    "挂什么科",
    "疫苗",
    "孕",
    "月经",
    "经期",
    "人体",
    "三维定位",
    "器官",
    "肌肉",
    "骨骼",
    "牙",
    "咽",
    "喉",
    "眼",
    "耳",
    "鼻",
    "头",
    "胸",
    "腹",
    "腰",
    "背",
    "腿",
    "脚",
    "手",
    "关节",
    "摔",
    "伤",
    "中毒",
    "抽搐",
    "昏迷",
    "骨折",
    "扭伤",
    "拉伤",
    "摔伤",
    "外伤",
    "损伤",
    "关节痛",
    "腰痛",
    "背痛",
    "颈椎病",
    "腰椎间盘突出",
    *KEY_TERMS,
)

GREETING_ONLY = {
    "你好",
    "您好",
    "哈喽",
    "嗨",
    "在吗",
    "在不在",
    "谢谢",
    "多谢",
    "早上好",
    "中午好",
    "晚上好",
    "hello",
    "hi",
    "thanks",
}

SINGLE_SYMPTOMS = {"痛", "疼", "痒", "麻", "晕", "咳", "喘", "烧", "吐", "肿"}
NON_HEALTH_PATTERNS = re.compile(
    r"天气|气温|下雨|股票|基金|新闻|写代码|编程|翻译|笑话|故事|电影|音乐|游戏|"
    r"几点|几号|星期几|日期|你是谁|叫什么名字|讲个笑话"
)

CONTEXTUAL_FOLLOW_UP_PATTERN = re.compile(
    r"怎么避免|如何避免|怎么预防|如何预防|如何防止|怎么防止|"
    r"注意事项|注意什么|要注意什么|有什么禁忌|有哪些禁忌|"
    r"怎么办|怎么处理|如何处理|怎么缓解|如何缓解|"
    r"严重吗|危险吗|会不会加重|会怎样|多久能好|"
    r"吃什么药|用什么药|做什么检查|挂什么科"
)


def _meaningful_characters(text: str) -> str:
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE).lower()


def is_health_related(message: str, *, has_health_context: bool = False) -> bool:
    text = str(message or "").strip()
    normalized = _meaningful_characters(text)
    if not normalized:
        return False
    if normalized in GREETING_ONLY:
        return False
    if re.search(r"怎么判断|如何判断|判断自己|是否患|是不是|有没有|如何区分|怎么区分|自查", text) and re.search(
        r"病|炎|症|痛|伤|癌|瘤|感染|过敏|热|咳|喘|晕|麻|肿|出血|骨折|扭伤|拉伤|不适",
        text,
    ):
        return True
    if any(signal in normalized for signal in HEALTH_SIGNALS):
        return True
    if normalized in SINGLE_SYMPTOMS:
        return True
    if NON_HEALTH_PATTERNS.search(normalized):
        return False
    # Short follow-ups such as “是的”“已经三天了” are meaningful only when
    # the current conversation already contains a health context.
    if has_health_context:
        return bool(re.search(r"[\u3400-\u9fffA-Za-z0-9]", normalized))
    return False


def history_has_health_context(history: list[dict[str, str]]) -> bool:
    return any(
        item.get("role") == "user"
        and is_health_related(item.get("content", ""), has_health_context=False)
        for item in history[-8:]
    )


def contextual_health_question(
    message: str,
    history: list[dict[str, str]],
) -> str:
    """Restore the topic of an elliptical health follow-up from recent turns."""
    text = str(message or "").strip()
    normalized = _meaningful_characters(text)
    if (
        not normalized
        or len(normalized) > 32
        or not CONTEXTUAL_FOLLOW_UP_PATTERN.search(normalized)
        or NON_HEALTH_PATTERNS.search(normalized)
        or is_health_related(text, has_health_context=False)
    ):
        return text

    health_messages = [
        str(item.get("content", "")).strip()
        for item in history[-8:]
        if item.get("role") == "user"
        and is_health_related(item.get("content", ""), has_health_context=False)
    ]
    if not health_messages:
        return text

    previous_topic = next(
        (
            prior
            for prior in reversed(health_messages)
            if any(term in prior for term in KEY_TERMS)
        ),
        health_messages[-1],
    )
    return f"{previous_topic[:900]}\n当前追问：{text}"


def needs_input_guidance(
    message: str,
    *,
    history: list[dict[str, str]],
    has_image: bool = False,
) -> bool:
    if has_image:
        return False
    return not is_health_related(
        message,
        has_health_context=history_has_health_context(history),
    )
