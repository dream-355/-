from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.llm import DeepSeekError, extract_health_metrics


class HealthMetricsVisionTests(unittest.TestCase):
    def test_extracts_and_validates_structured_metrics(self) -> None:
        response = """```json
        {
          "systolic": 118,
          "diastolic": "76",
          "heart_rate": 72,
          "glucose": 5.4,
          "spo2": 98,
          "weight_kg": 52.3,
          "sleep_hours": 7.5,
          "steps": 8210,
          "confidence": "high",
          "notes": ["截图左侧边缘轻微反光"],
          "measured_at": "2026-11-02T08:30:00+08:00",
          "unexpected": "ignored"
        }
        ```"""
        fake_settings = SimpleNamespace(
            deepseek_api_key="test-key",
            deepseek_vision_model="vision-test",
        )
        with (
            patch("backend.llm.settings", fake_settings),
            patch("backend.llm._call_deepseek", return_value=response),
        ):
            result = extract_health_metrics("data:image/jpeg;base64,test")

        self.assertEqual(result["metrics"]["systolic"], 118)
        self.assertEqual(result["metrics"]["diastolic"], 76)
        self.assertEqual(result["metrics"]["heart_rate"], 72)
        self.assertEqual(result["metrics"]["glucose"], 5.4)
        self.assertEqual(result["confidence"], "high")
        self.assertNotIn("unexpected", result["metrics"])

    def test_discards_out_of_range_and_non_numeric_values(self) -> None:
        response = (
            '{"systolic": 999, "diastolic": "unknown", '
            '"heart_rate": 72.5, "spo2": 98, "confidence": "invalid"}'
        )
        fake_settings = SimpleNamespace(
            deepseek_api_key="test-key",
            deepseek_vision_model="vision-test",
        )
        with (
            patch("backend.llm.settings", fake_settings),
            patch("backend.llm._call_deepseek", return_value=response),
        ):
            result = extract_health_metrics("data:image/jpeg;base64,test")

        self.assertEqual(result["metrics"], {"spo2": 98})
        self.assertEqual(result["confidence"], "low")

    def test_rejects_non_json_response(self) -> None:
        fake_settings = SimpleNamespace(
            deepseek_api_key="test-key",
            deepseek_vision_model="vision-test",
        )
        with (
            patch("backend.llm.settings", fake_settings),
            patch("backend.llm._call_deepseek", return_value="无法识别"),
        ):
            with self.assertRaises(DeepSeekError):
                extract_health_metrics("data:image/jpeg;base64,test")


if __name__ == "__main__":
    unittest.main()
