from __future__ import annotations

import unittest

from backend.medications import recommend_medications
from backend.safety import health_overview, triage


class TriageSafetyTests(unittest.TestCase):
    def test_chest_pain_with_breathing_difficulty_is_emergency(self) -> None:
        result = triage("突然胸痛，呼吸困难，还一直出汗", age=52)
        self.assertEqual(result["level"], "emergency")
        self.assertIn("胸痛伴呼吸困难", result["red_flags"])
        self.assertIn("120", result["action"])

    def test_stroke_like_signal_is_emergency(self) -> None:
        result = triage("突然口角歪斜，右侧肢体无力", age=63)
        self.assertEqual(result["level"], "emergency")
        self.assertIn("卒中样表现", result["red_flags"])

    def test_self_harm_signal_is_emergency(self) -> None:
        result = triage("最近一直不想活了，有伤害自己的念头")
        self.assertEqual(result["level"], "emergency")
        self.assertIn("自伤风险", result["red_flags"])

    def test_mild_dizziness_is_not_emergency(self) -> None:
        result = triage("起床时偶尔头晕，休息后可以缓解", duration_days=2)
        self.assertEqual(result["level"], "low")
        self.assertEqual(result["red_flags"], [])

    def test_vitals_raise_priority(self) -> None:
        result = triage(
            "感觉有点不舒服",
            vitals={"systolic": 185, "diastolic": 121, "spo2": 89},
        )
        self.assertIn(result["level"], {"high", "emergency"})
        self.assertGreaterEqual(len(result["vital_alerts"]), 3)

    def test_health_overview_detects_low_sleep(self) -> None:
        records = [
            {
                "systolic": 118,
                "diastolic": 76,
                "heart_rate": 72,
                "glucose": 5.2,
                "spo2": 99,
                "sleep_hours": 5.4,
            },
            {
                "systolic": 120,
                "diastolic": 78,
                "heart_rate": 74,
                "glucose": 5.4,
                "spo2": 98,
                "sleep_hours": 5.8,
            },
        ]
        result = health_overview(records)
        self.assertLess(result["score"], 95)
        self.assertTrue(any(alert["metric"] == "睡眠" for alert in result["alerts"]))

    def test_sore_throat_cold_recognizes_symptoms_and_medications(self) -> None:
        result = triage("早上起来嗓子疼，有点痒，好像感冒了", duration_days=5)
        self.assertIn("咽痛", result["symptoms"])
        self.assertIn("感冒样症状", result["symptoms"])
        self.assertNotEqual(result["score"], 0)
        advice = recommend_medications(
            "早上起来嗓子疼，有点痒，好像感冒了",
            result,
            age=20,
            pregnancy=False,
            allergies=["青霉素"],
            conditions=["轻度缺铁性贫血"],
        )
        self.assertTrue(advice["available"])
        self.assertTrue(any(item["conditions"] for item in advice["items"]))
        self.assertTrue(all(item["price"].startswith("¥") for item in advice["items"]))

    def test_emergency_triage_does_not_recommend_medicine(self) -> None:
        result = triage("突然胸痛并且呼吸困难")
        advice = recommend_medications("突然胸痛并且呼吸困难", result)
        self.assertFalse(advice["available"])
        self.assertEqual(advice["items"], [])


if __name__ == "__main__":
    unittest.main()

