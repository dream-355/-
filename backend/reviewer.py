from __future__ import annotations

import json
import re
from typing import Any

from backend.config import settings
from backend.llm import DeepSeekError, _call_deepseek


REVIEWER_SYSTEM_PROMPT = """你是医疗健康内容的独立质量审核员，只审核给定草稿是否符合下列硬性规则，不提供新的医学知识。

审核规则：
1. 草稿中的疾病关联必须表述为“可能相关/需结合检查”，不得出现“确诊为”“一定是”“可以确定”等结论性诊断。
2. 不得给出具体药物剂量、频次或疗程；只能建议按说明书或遵医嘱。
3. 若风险分诊等级为 emergency 或 high，草稿开头必须有明确就医或拨打 120 的提示。
4. 草稿不得出现用户未提供的具体数值、检查结果或病史。
5. 草稿必须声明不能替代医生诊断。
6. 草稿引用只能使用提供的证据编号，不得编造。

只输出 JSON，不要输出 Markdown 代码块或其他文字：
{"verdict":"pass"或"revise","issues":[{"severity":"high"或"medium","message":"问题描述"}],"revised_answer":"修正后的完整回答，无问题时空字符串"}
"""

DOSAGE_PATTERN = re.compile(
    r"\d+(?:\.\d+)?\s*(?:mg|毫克|g|克|ml|毫升|片|粒|袋|喷|滴)\s*(?:/|每|，|,|一次|一日|每日|每日)?",
    re.IGNORECASE,
)
DIAGNOSIS_PATTERN = re.compile(r"(确诊为|诊断为|可以确定|一定是|肯定是)")
DISCLAIMER_MARKERS = ("不能替代医生诊断", "不能替代专业诊疗", "不构成医学诊断", "仅供健康科普")
EMERGENCY_MARKERS = ("120", "急诊", "立即就医", "尽快就医")


def _issue(code: str, severity: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def rule_check(
    answer: str,
    graph_context: dict[str, Any],
    triage_result: dict[str, Any],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    text = answer or ""

    if DIAGNOSIS_PATTERN.search(text):
        issues.append(
            _issue("certain_diagnosis", "high", "出现结论性诊断措辞，需改为可能性表述")
        )
    if DOSAGE_PATTERN.search(text) and re.search(
        r"(服用|用药|剂量|一次|每日|每天)", text
    ):
        issues.append(
            _issue("dosage_advice", "high", "出现具体药物剂量或频次，需改为遵医嘱")
        )
    if not any(marker in text for marker in DISCLAIMER_MARKERS):
        issues.append(
            _issue("missing_disclaimer", "medium", "缺少不能替代医生诊断的声明")
        )
    if triage_result.get("level") in {"emergency", "high"} and not any(
        marker in text[:220] for marker in EMERGENCY_MARKERS
    ):
        issues.append(
            _issue("missing_escalation", "high", "风险等级较高但缺少就医或急救提示")
        )

    valid_ids = {item["id"] for item in graph_context.get("citations", [])}
    cited = {f"E{number}" for number in re.findall(r"\[E(\d+)\]", text)}
    unknown = cited - valid_ids
    if unknown:
        issues.append(
            _issue(
                "unknown_citation",
                "high",
                "引用了不存在的证据编号：" + "、".join(sorted(unknown)),
            )
        )
    if valid_ids and not cited:
        issues.append(
            _issue("no_citation_used", "medium", "存在可用证据但回答未标注证据编号")
        )
    return issues


def _repair(
    answer: str,
    issues: list[dict[str, str]],
    triage_result: dict[str, Any],
) -> tuple[str, list[str]]:
    """Deterministic fixes that never invent medical content."""
    text = answer.strip()
    applied: list[str] = []
    codes = {issue["code"] for issue in issues}

    if "certain_diagnosis" in codes:
        for source, target in (
            ("确诊为", "可能提示"),
            ("诊断为", "可能提示"),
            ("可以确定", "需要结合检查才能判断"),
            ("一定是", "可能是"),
            ("肯定是", "可能是"),
        ):
            text = text.replace(source, target)
        applied.append("将结论性诊断措辞改为可能性表述")
    if "dosage_advice" in codes:
        text = DOSAGE_PATTERN.sub("", text)
        text = text.replace("每次服用", "如需对症用药").replace("每日服用", "如需对症用药")
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = text.rstrip() + "\n\n具体药物剂量与频次请按说明书或遵医嘱。"
        applied.append("移除具体药物剂量与频次")
    if "missing_escalation" in codes:
        prefix = (
            "**建议立即拨打 120 或尽快前往急诊评估。**\n\n"
            if triage_result.get("level") == "emergency"
            else "**建议尽快联系医生或前往门诊评估。**\n\n"
        )
        text = prefix + text
        applied.append("补充就医提示")
    if "missing_disclaimer" in codes:
        text = text.rstrip() + "\n\n以上为健康科普信息，不能替代医生诊断。"
        applied.append("补充不能替代医生诊断的声明")
    if "unknown_citation" in codes:
        text = re.sub(r"\[E\d+\]", "", text)
        text = re.sub(r"[ \t]{2,}", " ", text).strip()
        applied.append("移除不存在的证据编号")
    return text, applied


def _llm_review(
    question: str,
    answer: str,
    evidence: list[dict[str, Any]],
    triage_result: dict[str, Any],
) -> dict[str, Any] | None:
    if not settings.deepseek_api_key:
        return None
    compact_evidence = [
        {
            "id": item.get("id"),
            "fact": f"{item.get('subject')} - {item.get('predicate')} -> {item.get('object')}",
        }
        for item in evidence[:16]
    ]
    payload = (
        f"用户问题：{question}\n\n"
        f"风险分诊等级：{triage_result.get('level')}（{triage_result.get('title')}）\n\n"
        f"可用证据：{json.dumps(compact_evidence, ensure_ascii=False)}\n\n"
        f"待审核草稿：\n{answer}"
    )
    try:
        raw = _call_deepseek(
            [
                {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
                {"role": "user", "content": payload},
            ],
            max_tokens=900,
        )
    except DeepSeekError:
        return None
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    verdict = parsed.get("verdict")
    if verdict not in {"pass", "revise"}:
        return None
    issues: list[dict[str, str]] = []
    for item in parsed.get("issues") or []:
        if not isinstance(item, dict):
            continue
        severity = item.get("severity")
        message = str(item.get("message") or "").strip()
        if severity not in {"high", "medium"} or not message:
            continue
        issues.append(_issue("llm_review", severity, message[:220]))
    revised = parsed.get("revised_answer")
    return {
        "verdict": verdict,
        "issues": issues,
        "revised_answer": revised if isinstance(revised, str) else "",
    }


def review_answer(
    *,
    question: str,
    answer: str,
    graph_context: dict[str, Any],
    triage_result: dict[str, Any],
    use_llm: bool = True,
) -> dict[str, Any]:
    """Two-stage review: deterministic safety rules, then optional LLM critique.

    The returned content is always safe to display: rule violations are fixed
    deterministically, and LLM rewrites are only accepted when they pass the
    same rule set afterwards.
    """
    rule_issues = rule_check(answer, graph_context, triage_result)
    content, applied = _repair(answer, rule_issues, triage_result)
    review: dict[str, Any] = {
        "reviewer": "rule-engine",
        "verdict": "pass" if not rule_issues else "revised",
        "issues": rule_issues,
        "applied_fixes": applied,
        "llm_used": False,
    }

    if use_llm and settings.review_llm_enabled and settings.deepseek_api_key:
        llm_review = _llm_review(
            question,
            content,
            graph_context.get("citations", []),
            triage_result,
        )
        if llm_review:
            review["llm_used"] = True
            review["reviewer"] = "rule-engine + llm-reviewer"
            review["issues"].extend(llm_review["issues"])
            candidate = llm_review.get("revised_answer") or ""
            if llm_review["verdict"] == "revise" and candidate.strip():
                candidate_issues = rule_check(candidate, graph_context, triage_result)
                if not any(issue["severity"] == "high" for issue in candidate_issues):
                    rechecked, extra_fixes = _repair(
                        candidate, candidate_issues, triage_result
                    )
                    content = rechecked
                    review["applied_fixes"].extend(
                        ["模型复核改写"] + extra_fixes
                    )
                    review["issues"].extend(candidate_issues)
            if {
                issue["code"] for issue in review["issues"]
            } - {issue["code"] for issue in rule_issues}:
                review["verdict"] = "revised"

    high_issues = [item for item in review["issues"] if item["severity"] == "high"]
    if high_issues and not applied:
        review["verdict"] = "warn"
    review["issue_count"] = len(review["issues"])
    review["high_issue_count"] = len(high_issues)
    review["content"] = content
    review["checked_at"] = __import__("datetime").datetime.now().astimezone().isoformat()
    return review
