from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from backend.safety import triage


def build_lifestyle_plan(
    profile: dict[str, Any],
    records: list[dict[str, Any]],
    triage_events: list[dict[str, Any]],
    *,
    symptoms: str = "",
    dietary_preferences: str = "",
) -> dict[str, Any]:
    combined_conditions = " ".join(profile.get("conditions") or [])
    allergies = " ".join(
        [*(profile.get("allergies") or []), dietary_preferences]
    )
    latest_triage = triage_events[0] if triage_events else {}
    current_symptoms = symptoms.strip() or str(
        latest_triage.get("symptoms") or ""
    )
    age = _age_from_birth_date(profile.get("birth_date"))
    current_triage = triage(
        current_symptoms,
        age=age,
        vitals=records[0] if records else {},
    )
    if latest_triage and not symptoms.strip():
        stored_result = latest_triage.get("result") or {}
        if stored_result.get("level") in {"high", "emergency"}:
            current_triage = {
                **current_triage,
                "level": stored_result["level"],
                "title": stored_result.get("title", current_triage["title"]),
                "action": stored_result.get("action", current_triage["action"]),
                "red_flags": stored_result.get("red_flags", []),
            }

    diet = _build_diet_plan(
        combined_conditions,
        allergies,
        current_symptoms,
        current_triage,
        records,
    )
    movement = _build_movement_plan(
        current_symptoms,
        current_triage,
        profile,
    )
    safety = _build_safety_notes(
        current_triage,
        combined_conditions,
        allergies,
        profile,
    )
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "basis": {
            "symptoms": current_symptoms or "未提供当前不适",
            "risk_level": current_triage["level"],
            "risk_title": current_triage["title"],
            "conditions": profile.get("conditions") or [],
            "allergies": profile.get("allergies") or [],
            "dietary_preferences": dietary_preferences.strip(),
        },
        "diet": diet,
        "movement": movement,
        "safety": safety,
        "sources": [
            "《中国居民膳食指南（2022）》一般膳食原则",
            "WHO《2020 身体活动与久坐行为指南》一般活动原则",
        ],
        "disclaimer": (
            "本方案用于健康科普和生活方式参考，不构成诊断、治疗处方、"
            "营养处方或康复处方。出现不适或患有慢性病时，请咨询医生、"
            "注册营养师或康复治疗师。"
        ),
    }


def _build_diet_plan(
    conditions: str,
    allergies: str,
    symptoms: str,
    current_triage: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    proteins = _protein_choices(allergies)
    focus = _diet_focus(conditions, symptoms, records, current_triage)
    principles: list[dict[str, str]] = [
        {
            "title": "餐盘比例",
            "detail": "每餐约一半蔬菜、四分之一主食、四分之一蛋白质食物。",
        },
        {
            "title": "生活化份量",
            "detail": "主食约一拳、蛋白质约一掌心、蔬菜约两拳、水果约一拳。",
        },
        {
            "title": "少加工",
            "detail": "优先蒸、煮、炖、快炒，少油炸、腌制和高盐酱料。",
        },
    ]
    less_foods = ["含糖饮料和高糖甜点", "油炸食品", "腌制和高度加工食品"]
    focus_copy = {
        "blood_pressure": (
            "优先控盐",
            "本次描述涉及血压偏高，先把减盐、少加工和规律进餐放在首位。",
        ),
        "throat": (
            "温和、易吞咽",
            "咽喉不适时优先温热、柔软和水分充足的食物，避免刺激。",
        ),
        "sleep": (
            "为睡眠留出时间",
            "晚餐不过晚、不过饱，下午后减少咖啡因，睡前避免酒精。",
        ),
        "shoulder": (
            "食物不能替代止痛和活动调整",
            "肩颈酸痛时饮食保持均衡即可，重点仍是避免久坐和疼痛加重的动作。",
        ),
        "digestion": (
            "少量、清淡、规律",
            "胃部不适时减少油腻、辛辣和暴饮暴食，观察不适与食物的关联。",
        ),
        "glucose": (
            "关注碳水份量与进食顺序",
            "近期血糖记录需要关注，但不能仅凭单次记录诊断或自行调整药物。",
        ),
        "urgent": (
            "先处理当前风险",
            "当前风险分级较高，饮食调整不能替代及时就医。",
        ),
        "general": (
            "保持均衡，不追求治疗性食谱",
            "当前没有需要特殊调整饮食的症状，按餐盘比例规律进餐即可。",
        ),
    }
    focus_title, focus_note = focus_copy[focus]
    principles.insert(
        0,
        {"title": focus_title, "detail": focus_note},
    )
    if focus == "blood_pressure":
        less_foods.extend(["咸菜、腌肉和高钠调味料", "浓汤、火锅蘸料和高盐外卖"])
    elif focus == "throat":
        less_foods.extend(["辣椒和烈酒", "过烫、过冷或粗糙尖锐的食物"])
    elif focus == "sleep":
        less_foods.extend(["下午后的咖啡、浓茶和能量饮料", "睡前酒精和高糖夜宵"])
    elif focus == "digestion":
        less_foods.extend(["辛辣、油腻和过饱饮食", "空腹浓茶或咖啡"])
    elif focus == "glucose":
        less_foods.extend(["甜饮料、果汁和精制糕点", "一次性大量精制主食"])
    elif focus == "urgent":
        less_foods.append("不要用饮食或自行用药拖延就医")
    if re.search(r"高血压|血压高|心脑血管", conditions):
        principles.append(
            {
                "title": "控盐",
                "detail": "减少咸菜、加工肉和重口味酱料；烹调时逐步减盐。",
            }
        )
        less_foods.append("高盐汤底、酱菜和加工肉")
    if re.search(r"糖尿病|血糖高|糖耐量", conditions):
        principles.append(
            {
                "title": "稳定碳水",
                "detail": "主食定量并优先全谷物；先吃蔬菜和蛋白质，再吃主食。",
            }
        )
        less_foods.append("甜饮料、果汁和精制糕点")
    if re.search(r"高血脂|血脂高|脂肪肝", conditions):
        principles.append(
            {
                "title": "脂肪来源",
                "detail": "优先鱼、豆制品和适量坚果，减少肥肉、奶油和反复煎炸。",
            }
        )
    if re.search(r"贫血|缺铁", conditions):
        principles.append(
            {
                "title": "铁与维生素 C",
                "detail": "可搭配瘦肉、动物血或豆类与富含维生素 C 的蔬果。",
            }
        )
    if re.search(r"肾病|肾功能|透析|心衰|心功能不全", conditions):
        principles.append(
            {
                "title": "先遵医嘱",
                "detail": "肾病或心衰患者可能需要限制蛋白质、钾、磷或液体，不能套用通用餐单。",
            }
        )

    meals = [
        {
            "name": "早餐",
            "staple": "燕麦、杂粮粥或全麦主食约一拳",
            "protein": proteins["breakfast"],
            "vegetable": "番茄、黄瓜或其他蔬菜一小份",
            "extra": "水果约一拳；饮品选择白水或无糖茶",
        },
        {
            "name": "午餐",
            "staple": "米饭或杂粮饭约一拳",
            "protein": proteins["main"],
            "vegetable": "两种以上蔬菜约两拳",
            "extra": "烹调油适量，汤品优先清汤并少放盐",
        },
        {
            "name": "晚餐",
            "staple": "薯类、杂粮或米饭约半拳到一拳",
            "protein": proteins["dinner"],
            "vegetable": "深色蔬菜为主约两拳",
            "extra": "晚餐与睡眠间隔至少 2 小时，避免过饱",
        },
        {
            "name": "加餐",
            "staple": proteins["snack"],
            "protein": "根据饥饿程度选择，不要用甜饮料代替",
            "vegetable": "可以搭配一小份水果",
            "extra": "血糖异常者需结合血糖监测和医生建议",
        },
    ]
    if focus == "blood_pressure":
        meals[0]["vegetable"] = "新鲜番茄或黄瓜，不搭配咸菜"
        meals[1]["extra"] = "少盐烹调，汤汁尽量少喝；优先清蒸、炖煮"
        meals[2]["extra"] = "晚餐同样控制盐和酱料，避免宵夜外卖"
    elif focus == "throat":
        meals[0].update(
            {
                "staple": "温热燕麦粥、软烂杂粮粥或面食一小碗",
                "vegetable": "南瓜、冬瓜等柔软蔬菜一小份",
                "extra": "温水少量多次；水果选择不酸、不过冷的种类",
            }
        )
        meals[1].update(
            {
                "staple": "软米饭或面食约一拳",
                "protein": proteins["main"].replace("清蒸鱼", "蒸蛋或清蒸鱼"),
                "vegetable": "蒸软或煮软的蔬菜约两拳",
                "extra": "避免过烫、过辣和粗糙食物，细嚼慢咽",
            }
        )
        meals[2].update(
            {
                "staple": "温热面食或软饭约半拳到一拳",
                "vegetable": "冬瓜、丝瓜或嫩叶菜约两拳",
                "extra": "保持水分；避免烟酒、浓茶和过度用嗓",
            }
        )
    elif focus == "sleep":
        meals[0]["extra"] = "早晨可适量饮用含咖啡因饮品，下午后不再摄入"
        meals[2].update(
            {
                "staple": "晚餐主食约半拳到一拳，避免过量",
                "extra": "尽量在睡前 2–3 小时完成晚餐，不用酒精助眠",
            }
        )
        meals[3]["extra"] = "晚间如饥饿可选择少量水果或牛奶，避免咖啡因"
    elif focus == "shoulder":
        meals[0]["extra"] = "无需为肩痛刻意忌口，保持规律早餐和充足饮水"
        meals[2]["extra"] = "久坐期间定时起身活动，饮食保持日常均衡"
    elif focus == "digestion":
        meals[1].update(
            {
                "vegetable": "选择易消化的熟蔬菜约一拳到两拳",
                "extra": "七八分饱即可，避免油炸和强烈辛辣",
            }
        )
        meals[2].update(
            {
                "staple": "易消化的主食约半拳到一拳",
                "extra": "晚餐不过饱，记录反酸、腹胀与进餐的关系",
            }
        )
    elif focus == "glucose":
        meals[0]["staple"] = "定量杂粮主食约一拳，不额外添加糖"
        meals[1]["extra"] = "先吃蔬菜和蛋白质，再吃主食；按监测结果与医生复盘"
        meals[3]["staple"] = "仅在饥饿时选择少量低糖水果或坚果"
    return {
        "title": {
            "blood_pressure": "控盐一日三餐参考",
            "throat": "温和吞咽三餐参考",
            "sleep": "助眠节律三餐参考",
            "shoulder": "肩颈不适日常饮食",
            "digestion": "清淡规律三餐参考",
            "glucose": "碳水定量三餐参考",
            "urgent": "先就医期间的饮食原则",
            "general": "一日三餐参考",
        }[focus],
        "focus": focus,
        "focus_title": focus_title,
        "focus_note": focus_note,
        "principles": principles,
        "meals": meals,
        "less_foods": list(dict.fromkeys(less_foods)),
        "allergy_note": (
            "已根据档案过敏与忌口尽量替换食材；进餐前仍需再次核对配料表。"
            if allergies.strip()
            else "档案未记录食物过敏。如有食物过敏，请先补充档案再使用本方案。"
        ),
    }


def _diet_focus(
    conditions: str,
    symptoms: str,
    records: list[dict[str, Any]],
    current_triage: dict[str, Any],
) -> str:
    if current_triage.get("level") in {"high", "emergency"}:
        return "urgent"
    text = f"{conditions} {symptoms}"
    latest = records[0] if records else {}
    try:
        systolic = float(latest.get("systolic") or 0)
        diastolic = float(latest.get("diastolic") or 0)
    except (TypeError, ValueError):
        systolic = diastolic = 0
    if re.search(r"血压|高压|低压", symptoms) or systolic >= 140 or diastolic >= 90:
        return "blood_pressure"
    if re.search(r"嗓子|喉咙|咽痛|咽部|声音嘶哑|吞咽", symptoms):
        return "throat"
    if re.search(r"失眠|睡眠不足|睡不好|熬夜|睡不着", symptoms):
        return "sleep"
    if re.search(r"反酸|烧心|胃痛|胃胀|腹胀|恶心|消化不良", symptoms):
        return "digestion"
    if re.search(r"血糖|糖尿病", text):
        return "glucose"
    if re.search(r"颈|肩|肩颈|脖子|斜方肌", symptoms):
        return "shoulder"
    return "general"


def _protein_choices(allergies: str) -> dict[str, str]:
    egg_allergy = bool(re.search(r"鸡蛋|蛋类|蛋过敏", allergies))
    dairy_allergy = bool(re.search(r"牛奶|乳制品|乳糖|奶过敏", allergies))
    fish_allergy = bool(re.search(r"鱼|海鲜|虾|蟹", allergies))
    soy_allergy = bool(re.search(r"大豆|豆制品|豆过敏", allergies))

    breakfast = "鸡蛋或无糖乳制品" if not egg_allergy else "瘦肉或豆制品"
    if dairy_allergy and not egg_allergy:
        breakfast = "鸡蛋和无糖豆浆"
    if egg_allergy and soy_allergy:
        breakfast = "瘦肉或其他已确认安全的蛋白来源"

    main = "清蒸鱼、豆腐或瘦肉" if not fish_allergy else "豆腐、鸡蛋或瘦肉"
    if fish_allergy and soy_allergy:
        main = "鸡蛋或瘦肉"

    dinner = "豆腐、鸡胸肉或鱼虾，按耐受选择" if not fish_allergy else "豆腐、鸡蛋或鸡肉"
    snack = "无糖酸奶或一小把坚果" if not dairy_allergy else "水果或少量坚果"
    return {
        "breakfast": breakfast,
        "main": main,
        "dinner": dinner,
        "snack": snack,
    }


def _build_movement_plan(
    symptoms: str,
    current_triage: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    if current_triage.get("level") in {"high", "emergency"}:
        return {
            "focus": "先处理当前风险",
            "title": "暂不提供运动或康复动作",
            "message": current_triage.get(
                "action", "当前存在需要优先就医的风险信号。"
            ),
            "items": [],
            "stop_signals": ["胸痛", "呼吸困难", "晕厥", "肢体无力或说话不清"],
        }
    if re.search(r"孕|怀孕|妊娠", " ".join(profile.get("conditions") or [])):
        return {
            "focus": "特殊人群",
            "title": "请先咨询产检医生",
            "message": "孕期运动方案需要结合孕周、并发症和既往运动习惯。",
            "items": [],
            "stop_signals": ["阴道出血", "持续腹痛", "头晕或胸闷", "胎动异常"],
        }
    if re.search(r"颈|肩|肩颈|脖子|斜方肌", symptoms):
        return {
            "focus": "肩颈舒缓",
            "title": "低强度肩颈活动",
            "message": "在无麻木、无力、眩晕和外伤的情况下，可尝试以下动作。",
            "items": [
                {
                    "name": "下巴微收",
                    "dose": "5–8 次 · 1–2 组",
                    "detail": "坐直，下巴水平向后收，保持 2–3 秒后放松。",
                },
                {
                    "name": "肩胛骨后缩",
                    "dose": "8–10 次 · 1–2 组",
                    "detail": "双臂自然下垂，肩胛骨轻轻向中间靠拢，不要耸肩。",
                },
                {
                    "name": "上斜方肌拉伸",
                    "dose": "每侧保持 15–20 秒 · 2 次",
                    "detail": "头轻轻偏向一侧，另一侧肩膀下沉，不追求疼痛感。",
                },
                {
                    "name": "颈部小范围转动",
                    "dose": "左右各 3–5 次",
                    "detail": "缓慢转动，只活动到舒适范围，不快速甩头。",
                },
            ],
            "stop_signals": [
                "疼痛明显加重",
                "手臂麻木或无力",
                "头晕、恶心或视物异常",
                "近期颈部外伤或手术后未经评估",
            ],
        }
    if re.search(r"嗓子|喉咙|咽痛|咽部|声音嘶哑", symptoms):
        return {
            "focus": "咽喉护理",
            "title": "不安排针对咽痛的康复动作",
            "message": "可适量饮水、避免烟酒和过度用嗓，并保持环境湿润。",
            "items": [],
            "stop_signals": [
                "呼吸困难或喘鸣",
                "无法吞咽唾液",
                "高热持续不退",
                "颈部明显肿胀",
            ],
        }
    return {
        "focus": "日常活动",
        "title": "低风险日常活动建议",
        "message": "可以从低强度活动开始，循序渐进，不追求一次完成大量运动。",
        "items": [
            {
                "name": "快走",
                "dose": "每次 10–20 分钟 · 每周逐步增加",
                "detail": "以能说完整句子但仍略微喘的强度为宜。",
            },
            {
                "name": "肩颈活动",
                "dose": "每个方向 5 次",
                "detail": "缓慢活动颈部与肩部，每小时久坐后起身一次。",
            },
        ],
        "stop_signals": ["胸闷", "胸痛", "明显气促", "头晕或晕厥"],
    }


def _build_safety_notes(
    current_triage: dict[str, Any],
    conditions: str,
    allergies: str,
    profile: dict[str, Any],
) -> list[str]:
    notes: list[str] = []
    if current_triage.get("level") in {"high", "emergency"}:
        notes.append("当前分诊提示高优先级风险，请先就医，不要用饮食或动作替代治疗。")
    if re.search(r"肾病|肾功能|透析|心衰|心功能不全", conditions):
        notes.append("存在可能影响蛋白质、钾、磷或液体限制的疾病，通用餐单不能直接执行。")
    if re.search(r"糖尿病|血糖高", conditions):
        notes.append("进餐份量应结合血糖监测、用药和医生或营养师建议调整。")
    if allergies.strip():
        notes.append("食物过敏必须核对配料表；出现口唇肿胀、喘鸣或全身风团时立即就医。")
    if re.search(r"孕|怀孕|妊娠", " ".join(profile.get("conditions") or [])):
        notes.append("孕期不要自行限制主食或蛋白质摄入，运动需先咨询产检医生。")
    if not notes:
        notes.append("如食用或活动后出现明显不适，请停止并咨询专业人员。")
    return notes


def _age_from_birth_date(value: str | None) -> int | None:
    if not value:
        return None
    try:
        birth = datetime.strptime(value[:10], "%Y-%m-%d")
        now = datetime.now()
        return now.year - birth.year - (
            (now.month, now.day) < (birth.month, birth.day)
        )
    except (TypeError, ValueError):
        return None
