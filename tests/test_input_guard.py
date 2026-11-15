import unittest

from backend.input_guard import (
    contextual_health_question,
    history_has_health_context,
    is_health_related,
    needs_input_guidance,
)


class InputGuardTests(unittest.TestCase):
    def test_punctuation_emoji_and_greeting_do_not_reach_medical_generation(self) -> None:
        for message in ("?", "？？？？？？????", "……", "😀😀", "你好", "在吗"):
            with self.subTest(message=message):
                self.assertTrue(needs_input_guidance(message, history=[]))

    def test_unrelated_question_is_redirected_to_symptom_description(self) -> None:
        for message in ("今天天气怎么样", "帮我写一段代码", "你叫什么名字"):
            with self.subTest(message=message):
                self.assertTrue(needs_input_guidance(message, history=[]))

    def test_real_health_questions_are_allowed(self) -> None:
        for message in (
            "头痛",
            "最近睡不着，白天乏力",
            "帮我看看体检报告",
            "怎么判断自己是否发烧",
            "怎么判断我是否骨折",
            "怎么判断我是否有红斑狼疮",
            "我通过人体三维定位选择了左侧甲状腺",
        ):
            with self.subTest(message=message):
                self.assertFalse(needs_input_guidance(message, history=[]))

    def test_short_follow_up_requires_existing_health_context(self) -> None:
        history = [
            {"role": "user", "content": "我从昨天开始头痛，还有点恶心"},
            {"role": "assistant", "content": "请补充体温和疼痛程度。"},
        ]
        self.assertTrue(history_has_health_context(history))
        self.assertFalse(needs_input_guidance("是的", history=history))
        self.assertTrue(needs_input_guidance("是的", history=[]))
        self.assertTrue(needs_input_guidance("这是判断错误吗", history=[]))
        self.assertTrue(needs_input_guidance("今天天气怎么样", history=history))

    def test_contextual_follow_up_inherits_recent_health_topic(self) -> None:
        history = [
            {"role": "user", "content": "怎么判断我是否骨折"},
            {"role": "assistant", "content": "需要结合受伤过程、疼痛和活动情况判断。"},
        ]
        resolved = contextual_health_question("怎么避免", history)
        self.assertIn("骨折", resolved)
        self.assertIn("怎么避免", resolved)
        self.assertFalse(needs_input_guidance("怎么避免", history=history))

        for follow_up in ("怎么预防", "要注意什么", "严重吗", "怎么办"):
            with self.subTest(follow_up=follow_up):
                self.assertIn(
                    "骨折",
                    contextual_health_question(follow_up, history),
                )

    def test_context_resolution_does_not_absorb_unrelated_questions(self) -> None:
        history = [
            {"role": "user", "content": "怎么判断我是否骨折"},
            {"role": "assistant", "content": "请结合受伤经过判断。"},
        ]
        self.assertEqual(
            contextual_health_question("今天天气怎么样", history),
            "今天天气怎么样",
        )
        self.assertEqual(
            contextual_health_question("怎么预防感冒", history),
            "怎么预防感冒",
        )

    def test_image_or_symptom_single_character_is_allowed(self) -> None:
        self.assertFalse(needs_input_guidance("?", history=[], has_image=True))
        self.assertTrue(is_health_related("痛"))


if __name__ == "__main__":
    unittest.main()
