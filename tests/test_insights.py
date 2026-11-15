from __future__ import annotations

import unittest

from backend.safety import longitudinal_insights


class LongitudinalInsightTests(unittest.TestCase):
    def test_short_sleep_and_dizziness_are_correlated(self) -> None:
        records = [
            {"measured_at": "2026-10-30T08:00:00+08:00", "sleep_hours": 5.2, "systolic": 142},
            {"measured_at": "2026-10-31T08:00:00+08:00", "sleep_hours": 5.8, "systolic": 120},
        ]
        conversations = [
            {"title": "最近头晕怎么办", "updated_at": "2026-10-30T09:00:00+08:00"},
            {"title": "头晕持续", "updated_at": "2026-10-31T09:00:00+08:00"},
        ]
        insights = longitudinal_insights(records, conversations)
        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]["title"], "头晕头痛")
        self.assertEqual(insights[0]["evidence"]["consultations"], 2)
        self.assertEqual(insights[0]["evidence"]["low_sleep_days"], 2)

    def test_single_mention_does_not_produce_insight(self) -> None:
        records = [{"measured_at": "2026-10-30T08:00:00+08:00", "sleep_hours": 5.0}]
        conversations = [
            {"title": "头晕", "updated_at": "2026-10-30T09:00:00+08:00"},
            {"title": "体检报告解读", "updated_at": "2026-10-30T10:00:00+08:00"},
        ]
        self.assertEqual(longitudinal_insights(records, conversations), [])

    def test_missing_data_returns_empty(self) -> None:
        self.assertEqual(longitudinal_insights([], []), [])


if __name__ == "__main__":
    unittest.main()
