from __future__ import annotations

import unittest

from backend.lifestyle import build_lifestyle_plan


class LifestylePlanTests(unittest.TestCase):
    def test_shoulder_discomfort_returns_reps_and_stop_signals(self) -> None:
        result = build_lifestyle_plan(
            {"conditions": [], "allergies": []},
            [],
            [],
            symptoms="最近肩颈酸痛，没有手麻",
        )
        self.assertEqual(result["movement"]["focus"], "肩颈舒缓")
        self.assertGreaterEqual(len(result["movement"]["items"]), 4)
        self.assertTrue(
            all(item["dose"] for item in result["movement"]["items"])
        )
        self.assertIn("手臂麻木或无力", result["movement"]["stop_signals"])

    def test_emergency_does_not_return_exercise(self) -> None:
        result = build_lifestyle_plan(
            {"conditions": [], "allergies": []},
            [],
            [],
            symptoms="突然胸痛，呼吸困难",
        )
        self.assertEqual(result["movement"]["items"], [])
        self.assertIn("立即", result["movement"]["message"])

    def test_hypertension_and_food_allergy_change_meal_guidance(self) -> None:
        result = build_lifestyle_plan(
            {"conditions": ["高血压"], "allergies": ["鸡蛋"]},
            [],
            [],
        )
        principles = [item["title"] for item in result["diet"]["principles"]]
        self.assertIn("控盐", principles)
        breakfast = result["diet"]["meals"][0]["protein"]
        self.assertNotIn("鸡蛋", breakfast)
        self.assertTrue(any("高盐" in item for item in result["diet"]["less_foods"]))

    def test_kidney_condition_adds_specialist_warning(self) -> None:
        result = build_lifestyle_plan(
            {"conditions": ["慢性肾病"], "allergies": []},
            [],
            [],
        )
        self.assertTrue(
            any("蛋白质、钾、磷" in note for note in result["safety"])
        )

    def test_throat_discomfort_is_not_presented_as_exercise(self) -> None:
        result = build_lifestyle_plan(
            {"conditions": [], "allergies": []},
            [],
            [],
            symptoms="嗓子疼，吞咽时明显",
        )
        self.assertEqual(result["movement"]["focus"], "咽喉护理")
        self.assertEqual(result["movement"]["items"], [])

    def test_different_symptoms_change_the_diet_plan(self) -> None:
        shoulder = build_lifestyle_plan(
            {"conditions": [], "allergies": []},
            [],
            [],
            symptoms="肩颈酸痛",
        )
        throat = build_lifestyle_plan(
            {"conditions": [], "allergies": []},
            [],
            [],
            symptoms="嗓子疼，吞咽不舒服",
        )
        blood_pressure = build_lifestyle_plan(
            {"conditions": [], "allergies": []},
            [{"systolic": 152, "diastolic": 94}],
            [],
            symptoms="最近血压偏高",
        )
        self.assertEqual(shoulder["diet"]["focus"], "shoulder")
        self.assertEqual(throat["diet"]["focus"], "throat")
        self.assertEqual(blood_pressure["diet"]["focus"], "blood_pressure")
        self.assertNotEqual(
            shoulder["diet"]["title"], throat["diet"]["title"]
        )
        self.assertNotEqual(
            shoulder["diet"]["meals"], throat["diet"]["meals"]
        )
        self.assertIn("控盐", blood_pressure["diet"]["title"])


if __name__ == "__main__":
    unittest.main()
