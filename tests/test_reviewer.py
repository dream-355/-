from __future__ import annotations

import unittest

from backend.reviewer import review_answer, rule_check


EVIDENCE = {
    "citations": [
        {
            "id": "E1",
            "subject": "高血压",
            "predicate": "并发症",
            "object": "左心室肥厚",
        }
    ]
}


def run(answer: str, level: str = "low") -> dict:
    return review_answer(
        question="高血压并发症有哪些？",
        answer=answer,
        graph_context=EVIDENCE,
        triage_result={"level": level, "title": "测试"},
        use_llm=False,
    )


class ReviewerRuleTests(unittest.TestCase):
    def test_clean_answer_passes(self) -> None:
        answer = (
            "可能与高血压相关[E1]，需结合检查判断。\n\n"
            "以上为健康科普信息，不能替代医生诊断。"
        )
        result = run(answer)
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["high_issue_count"], 0)

    def test_certain_diagnosis_is_rewritten(self) -> None:
        result = run("你确诊为高血压。以上为健康科普信息，不能替代医生诊断。")
        self.assertIn("certain_diagnosis", [item["code"] for item in result["issues"]])
        self.assertNotIn("确诊为", result["content"])

    def test_dosage_is_removed(self) -> None:
        result = run(
            "建议每次服用 500mg 降压药。以上为健康科普信息，不能替代医生诊断。"
        )
        self.assertNotIn("500mg", result["content"])
        self.assertIn("遵医嘱", result["content"])

    def test_emergency_answer_gets_escalation_first(self) -> None:
        result = run("请多休息。以上为健康科普信息，不能替代医生诊断。", level="emergency")
        self.assertTrue(result["content"].lstrip().startswith("**建议立即拨打 120"))

    def test_unknown_citation_is_removed(self) -> None:
        result = run("高血压可能导致左心室肥厚[E9]。以上为健康科普信息，不能替代医生诊断。")
        self.assertNotIn("[E9]", result["content"])
        self.assertIn("unknown_citation", [item["code"] for item in result["issues"]])

    def test_missing_disclaimer_is_appended(self) -> None:
        result = run("可能与高血压相关[E1]，需结合检查判断。")
        self.assertIn("不能替代医生诊断", result["content"])

    def test_rule_check_reports_high_risk_without_escalation(self) -> None:
        issues = rule_check("请多喝水。", EVIDENCE, {"level": "high"})
        codes = {item["code"] for item in issues}
        self.assertIn("missing_escalation", codes)


if __name__ == "__main__":
    unittest.main()
