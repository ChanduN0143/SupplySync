import unittest

from business_rules import classify_change, schedule_impact


class TestBusinessRules(unittest.TestCase):

    def test_small_change(self):
        result = classify_change(
            100, 105,
            10.0, 10.2,
            "2026-11-10", "2026-11-12"
        )
        self.assertEqual(result, "AUTO_APPROVAL")

    def test_large_quantity_change(self):
        result = classify_change(
            100, 120,
            10.0, 10.0,
            "2026-11-10", "2026-11-12"
        )
        self.assertEqual(result, "MANUAL_APPROVAL")

    def test_large_price_change(self):
        result = classify_change(
            100, 100,
            10.0, 11.0,
            "2026-11-10", "2026-11-12"
        )
        self.assertEqual(result, "MANUAL_APPROVAL")

    def test_large_date_change(self):
        result = classify_change(
            100, 100,
            10.0, 10.0,
            "2026-11-10", "2026-11-20"
        )
        self.assertEqual(result, "MANUAL_APPROVAL")

    def test_schedule_shortage(self):
        result = schedule_impact(
            "2026-11-20", "2026-11-20", 100, 80
        )
        self.assertEqual(result["shortage_qty"], 20)
        self.assertEqual(result["status"], "SHORTAGE")

    def test_schedule_delay(self):
        result = schedule_impact(
            "2026-11-20", "2026-11-30", 100, 100
        )
        self.assertEqual(result["delay_days"], 10)
        self.assertEqual(result["status"], "DELAYED")

    def test_schedule_on_track(self):
        result = schedule_impact(
            "2026-11-20", "2026-11-18", 100, 100
        )
        self.assertEqual(result["status"], "ON_TRACK")


if __name__ == "__main__":
    unittest.main()