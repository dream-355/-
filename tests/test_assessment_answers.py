import unittest

from backend.llm import _grounded_answer
from backend.graph import detect_intent
from backend.prompts import SYSTEM_PROMPT, build_user_prompt


class AssessmentAnswerTests(unittest.TestCase):
    @staticmethod
    def triage(**overrides):
        result = {
            "level": "low",
            "red_flags": [],
            "symptoms": [],
            "action": "居家观察并记录症状变化",
            "departments": ["全科医学科"],
        }
        result.update(overrides)
        return result

    def test_fever_question_gets_measurement_and_red_flag_guidance(self) -> None:
        context = {
            "intent": "assessment",
            "entities": [{"name": "发热", "type": "Symptom"}],
            "sections": {"症状与体征": ["发热", "乏力"]},
            "citations": [
                {
                    "id": "E1",
                    "subject": "发热",
                    "predicate": "症状与体征",
                    "object": "乏力",
                }
            ],
        }
        answer = _grounded_answer(
            "怎么判断自己是否发烧",
            context,
            self.triage(),
            {},
        )["content"]

        self.assertIn("规范测量体温", answer)
        self.assertIn("37.3", answer)
        self.assertIn("同一部位", answer)
        self.assertIn("呼吸困难", answer)
        self.assertIn("不能替代医生诊断", answer)
        self.assertNotIn("图谱提供的信息线索", answer)

    def test_other_assessment_questions_use_context_not_cold_template(self) -> None:
        context = {
            "intent": "assessment",
            "entities": [{"name": "痛风", "type": "Disease"}],
            "sections": {
                "症状与体征": ["关节红肿热痛", "突发单关节疼痛"],
            },
            "citations": [
                {
                    "id": "E1",
                    "subject": "痛风",
                    "predicate": "症状与体征",
                    "object": "关节红肿热痛",
                }
            ],
        }
        answer = _grounded_answer(
            "怎么判断自己是不是痛风",
            context,
            self.triage(),
            {},
        )["content"]

        self.assertIn("痛风", answer)
        self.assertIn("关节红肿热痛", answer)
        self.assertIn("自查", answer)
        self.assertIn("降低发生或加重风险", answer)
        self.assertNotIn("普通感冒", answer)
        self.assertNotIn("图谱提供的信息线索", answer)

    def test_prevention_follow_up_uses_inherited_fracture_topic(self) -> None:
        context = {
            "intent": "prevention",
            "entities": [{"name": "骨折", "type": "Disease"}],
            "sections": {
                "注意事项": ["避免跌倒和重复受伤"],
            },
            "citations": [],
        }
        answer = _grounded_answer(
            "怎么避免",
            context,
            self.triage(),
            {},
        )["content"]

        self.assertTrue(answer.startswith("**针对“骨折”"))
        self.assertIn("避免跌倒和重复受伤", answer)
        self.assertNotIn("尚未明确命中图谱实体", answer)

    def test_assessment_phrasings_are_all_classified_as_assessment(self) -> None:
        for question in (
            "怎么判断自己是否发烧",
            "我这是不是肺炎",
            "如何自查有没有贫血",
            "怎么区分流感和普通感冒",
        ):
            with self.subTest(question=question):
                self.assertEqual(detect_intent(question), "assessment")

    def test_prompt_includes_inherited_topic_and_prevention_requirement(self) -> None:
        prompt = build_user_prompt(
            question="怎么避免",
            graph_context={
                "facts": [],
                "sections": {},
                "retrieval": {},
                "entities": [{"name": "骨折", "type": "Disease"}],
                "intent": "prevention",
                "contextual_follow_up": True,
                "resolved_question": "怎么判断我是否骨折\n当前追问：怎么避免",
            },
            history=[],
            summary="",
            profile={},
            triage={"level": "low", "red_flags": []},
        )
        self.assertIn("怎么判断我是否骨折", prompt)
        self.assertIn("必须直接给出降低发生或加重风险的预防要点", prompt)
        self.assertIn("不能回答“尚未命中实体”", prompt)
        self.assertIn("不要等用户再次追问", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
