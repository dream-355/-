from __future__ import annotations

import re
import urllib.parse
from typing import Any


PRICE_SNAPSHOT_DATE = "2026-10-31"


OTC_CATALOG: list[dict[str, Any]] = [
    {
        "id": "watermelon-frost-throat",
        "name": "西瓜霜清咽含片",
        "generic": "西瓜霜清咽含片",
        "spec": "32 片/盒",
        "category": "咽部含片",
        "conditions": ["sore_throat"],
        "price_min": 12.9,
        "price_max": 19.9,
        "reason": "适用于咽部不适、咽干或轻度咽痛的对症缓解。",
        "cautions": "含服，不吞服；儿童、孕期、哺乳期或有基础疾病者先咨询药师。",
        "avoid": ["对成分过敏"],
        "search_term": "西瓜霜清咽含片",
    },
    {
        "id": "iodine-throat",
        "name": "西地碘含片",
        "generic": "西地碘含片",
        "spec": "1.5 毫克 × 30 片",
        "category": "咽部含片",
        "conditions": ["sore_throat"],
        "price_min": 16.0,
        "price_max": 28.0,
        "reason": "适用于部分咽部炎症相关不适，可作为咽部局部对症选项。",
        "cautions": "碘过敏、甲状腺疾病患者不宜自行使用；孕期和哺乳期先咨询医生。",
        "avoid": ["碘过敏", "甲状腺疾病", "孕期或哺乳期"],
        "search_term": "西地碘含片",
    },
    {
        "id": "cold-granules",
        "name": "感冒灵颗粒",
        "generic": "复方感冒制剂",
        "spec": "10 克 × 9 袋",
        "category": "复方感冒药",
        "conditions": ["common_cold", "fever_pain"],
        "price_min": 10.8,
        "price_max": 16.9,
        "reason": "用于普通感冒相关头痛、发热、鼻塞、咽痛等症状的复方对症选择。",
        "cautions": "通常含对乙酰氨基酚和抗组胺成分；不得与其他含对乙酰氨基酚药物叠加，服药后避免饮酒和驾驶。",
        "avoid": ["肝病", "正在使用其他复方感冒药", "饮酒"],
        "search_term": "感冒灵颗粒",
    },
    {
        "id": "acetaminophen",
        "name": "对乙酰氨基酚片",
        "generic": "对乙酰氨基酚",
        "spec": "0.5 克 × 20 片",
        "category": "解热镇痛药",
        "conditions": ["fever_pain"],
        "price_min": 6.8,
        "price_max": 13.5,
        "reason": "可在明确发热或轻中度疼痛时作为单一成分对症选项。",
        "cautions": "注意所有感冒药中的重复成分；肝病患者、频繁饮酒者先咨询医生。",
        "avoid": ["严重肝病", "同时服用含对乙酰氨基酚的复方感冒药"],
        "search_term": "对乙酰氨基酚片",
    },
    {
        "id": "loratadine",
        "name": "氯雷他定片",
        "generic": "氯雷他定",
        "spec": "10 毫克 × 6 片",
        "category": "抗过敏药",
        "conditions": ["allergy"],
        "price_min": 8.5,
        "price_max": 17.9,
        "reason": "可用于过敏性鼻炎或荨麻疹相关喷嚏、流涕、瘙痒等症状。",
        "cautions": "孕期、哺乳期、肝肾功能异常或正在使用其他抗过敏药时先咨询医生或药师。",
        "avoid": ["对本品过敏", "孕期或哺乳期未咨询医生"],
        "search_term": "氯雷他定片",
    },
    {
        "id": "saline-spray",
        "name": "生理性海水鼻腔喷雾",
        "generic": "鼻腔冲洗护理",
        "spec": "50 毫升/瓶",
        "category": "鼻腔护理",
        "conditions": ["common_cold", "allergy"],
        "price_min": 24.0,
        "price_max": 45.0,
        "reason": "用于鼻腔清洁和湿润，不涉及全身用药，适用于鼻塞或鼻部过敏症状辅助护理。",
        "cautions": "按照产品说明使用；婴幼儿使用需选择对应规格并咨询专业人员。",
        "avoid": ["鼻腔明显出血或近期鼻部手术后未咨询医生"],
        "search_term": "生理性海水鼻腔喷雾",
    },
    {
        "id": "montmorillonite",
        "name": "蒙脱石散",
        "generic": "蒙脱石",
        "spec": "3 克 × 10 袋",
        "category": "止泻药",
        "conditions": ["diarrhea"],
        "price_min": 12.0,
        "price_max": 22.5,
        "reason": "可用于部分急性腹泻的对症处理，但需要同时关注补液和病因。",
        "cautions": "与其他口服药需错开服用；高热、血便、严重脱水或持续腹泻应就医。",
        "avoid": ["血便", "高热伴腹泻", "严重脱水"],
        "search_term": "蒙脱石散",
    },
    {
        "id": "ors-iii",
        "name": "口服补液盐 III",
        "generic": "口服补液盐",
        "spec": "5.125 克 × 6 袋",
        "category": "补液",
        "conditions": ["diarrhea"],
        "price_min": 14.0,
        "price_max": 25.0,
        "reason": "腹泻时可用于补充水和电解质，是腹泻管理的重要基础措施。",
        "cautions": "严格按包装说明配制，不自行改变浓度；少尿、水肿或心肾功能异常者先咨询医生。",
        "avoid": ["少尿", "严重心肾功能异常"],
        "search_term": "口服补液盐III",
    },
    {
        "id": "hydrotalcite",
        "name": "铝碳酸镁咀嚼片",
        "generic": "铝碳酸镁",
        "spec": "0.5 克 × 20 片",
        "category": "胃部对症药",
        "conditions": ["reflux"],
        "price_min": 18.0,
        "price_max": 30.0,
        "reason": "可用于餐后反酸、烧心等胃部不适的短期对症选择。",
        "cautions": "肾功能异常者慎用；吞咽困难、黑便、呕血或体重明显下降时应就医。",
        "avoid": ["严重肾功能异常", "消化道出血表现"],
        "search_term": "铝碳酸镁咀嚼片",
    },
]


def _detect_conditions(text: str) -> list[str]:
    conditions: list[str] = []
    patterns = {
        "sore_throat": r"嗓子疼|嗓子痒|喉咙痛|喉咙痒|咽痛|咽痒|咽喉",
        "common_cold": r"感冒|着凉|受凉|鼻塞|流涕|流鼻涕|打喷嚏",
        "fever_pain": r"发热|发烧|头痛|肌肉酸痛|全身酸痛",
        "allergy": r"过敏|花粉|眼痒|过敏性鼻炎",
        "diarrhea": r"腹泻|拉肚子|水样便",
        "reflux": r"反酸|烧心|胃酸|胃部灼热",
    }
    for condition, pattern in patterns.items():
        if re.search(pattern, text):
            conditions.append(condition)
    return conditions


def _possible_conditions(conditions: list[str]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    if "sore_throat" in conditions and "common_cold" in conditions:
        results.append(
            {
                "name": "普通感冒样上呼吸道症状",
                "confidence": "表现相关",
                "note": "症状组合与常见上呼吸道感染相似，但仍需结合体温、病程和检查判断。",
            }
        )
        results.append(
            {
                "name": "急性咽炎可能",
                "confidence": "不能仅凭症状确诊",
                "note": "咽痛、咽痒常见于病毒性上呼吸道感染，也可能是环境干燥或其他刺激。",
            }
        )
    elif "common_cold" in conditions:
        results.append(
            {
                "name": "上呼吸道感染样表现",
                "confidence": "表现相关",
                "note": "当前信息不足以判断病原体，不建议自行使用抗生素。",
            }
        )
    elif "sore_throat" in conditions:
        results.append(
            {
                "name": "咽部刺激或咽炎样表现",
                "confidence": "需继续观察",
                "note": "持续高热、吞咽困难或扁桃体明显肿大时需要就医。",
            }
        )
    elif "allergy" in conditions:
        results.append(
            {
                "name": "过敏相关症状可能",
                "confidence": "需结合诱因",
                "note": "如与花粉、尘螨等接触相关，可记录暴露和缓解规律。",
            }
        )
    elif "diarrhea" in conditions:
        results.append(
            {
                "name": "急性腹泻样表现",
                "confidence": "需观察脱水",
                "note": "重点关注尿量、精神状态、血便和高热。",
            }
        )
    if not results:
        results.append(
            {
                "name": "症状尚不足以判断具体问题",
                "confidence": "证据有限",
                "note": "请补充体温、持续时间、伴随症状和既往病史。",
            }
        )
    return results


def recommend_medications(
    symptoms_text: str,
    triage_result: dict[str, Any],
    *,
    age: int | None = None,
    pregnancy: bool = False,
    allergies: list[str] | None = None,
    conditions: list[str] | None = None,
) -> dict[str, Any]:
    text = symptoms_text or ""
    detected = _detect_conditions(text)
    allergy_text = " ".join(allergies or [])
    condition_text = " ".join(conditions or [])
    possible = _possible_conditions(detected)

    basis = [
        f"识别症状：{'、'.join(triage_result.get('symptoms', [])) or '未匹配标准词'}",
        f"持续时间：{triage_result.get('duration_days', '未提供')}",
        f"危险信号：{'、'.join(triage_result.get('red_flags', [])) or '未识别'}",
    ]
    summary = {
        "possible_conditions": possible,
        "assessment_basis": basis,
        "symptom_categories": detected,
    }

    if triage_result.get("level") == "emergency":
        return {
            **summary,
            "available": False,
            "title": "当前不建议自行用药",
            "message": "存在急症风险，请先完成急救或急诊评估。自行服药可能掩盖病情。",
            "items": [],
            "safety_notes": ["立即拨打 120 或前往急诊", "携带正在使用的药物清单"],
            "price_note": "急症场景不提供药品选购建议。",
        }

    if pregnancy:
        return {
            **summary,
            "available": False,
            "title": "孕期请先咨询医生或药师",
            "message": "孕期用药需要结合孕周和基础疾病评估，本系统不提供自行购药建议。",
            "items": [],
            "safety_notes": ["可先采用补液、休息等非药物护理", "不要自行使用复方感冒药或止痛药"],
            "price_note": "",
        }

    selected: list[dict[str, Any]] = []
    for item in OTC_CATALOG:
        if not set(item["conditions"]).intersection(detected):
            continue
        avoid_reasons = set(item.get("avoid", []))
        if "碘过敏" in avoid_reasons and "碘" in allergy_text:
            continue
        if "肝病" in avoid_reasons and re.search(r"肝|肝炎|肝硬化", condition_text):
            continue
        if item["id"] in {"acetaminophen", "cold-granules"} and re.search(
            r"肝|肝炎|肝硬化", condition_text
        ):
            continue
        if age is not None and age < 18 and item["id"] in {"cold-granules", "iodine-throat"}:
            continue
        selected.append(
            {
                **item,
                "otc": True,
                "price": f"¥{item['price_min']:.1f}–{item['price_max']:.1f}",
                "price_label": "今日线上零售参考区间",
                "price_updated_at": PRICE_SNAPSHOT_DATE,
                "price_source": "公开零售价快照",
                "search_url": (
                    "https://so.m.jd.com/ware/search.action?keyword="
                    + urllib.parse.quote(item["search_term"])
                ),
            }
        )
        if len(selected) >= 4:
            break

    safety_notes = [
        "一次只选择一种复方感冒药，避免成分重复。",
        "本页不提供剂量、处方或抗生素建议，请按说明书或药师指导使用。",
        "若症状持续加重、出现高热、呼吸困难或无法进食，应停止自行处理并及时就医。",
    ]
    if "sore_throat" in detected:
        safety_notes.insert(
            0,
            "两种咽部含片属于同类替代选择，不建议同时使用。",
        )
    if not selected:
        return {
            **summary,
            "available": False,
            "title": "暂无可安全推荐的药品",
            "message": "当前症状组合或个人信息不适合自动推荐，请咨询药师或医生。",
            "items": [],
            "safety_notes": safety_notes,
            "price_note": "未匹配到适合当前症状的非处方药。",
        }

    return {
        **summary,
        "available": True,
        "title": "非处方对症用药参考",
        "message": "以下仅为症状匹配的购药信息，不是处方；请先核对过敏史、基础病和正在使用的药物。",
        "items": selected,
        "safety_notes": safety_notes,
        "price_note": (
            f"价格为 {PRICE_SNAPSHOT_DATE} 线上零售参考区间，受规格、地区、"
            "门店与促销影响，实际价格以实时页面或线下药房为准。"
        ),
    }

