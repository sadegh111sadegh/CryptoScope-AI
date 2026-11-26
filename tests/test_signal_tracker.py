import os
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

from signal_tracker import load_history, save_history, settle_forecasts, record_forecast, performance_summary
from adaptive_weights import calculate_adaptive_weights


class SignalTrackerTests(unittest.TestCase):
    def test_save_load_and_settle_forecast(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "history.json")
            now = datetime(2026, 1, 1, tzinfo=timezone.utc)
            forecast = {"available": True, "horizon_hours": 24,
                        "probabilities": {"up": 70, "down": 20, "neutral": 10}}
            history = record_forecast([], 100, forecast, {"trend": 50}, now)
            save_history(history, path)
            loaded = load_history(path)
            settled = settle_forecasts(loaded, 103, now + timedelta(hours=25))
            self.assertEqual(settled[0]["outcome"], "up")
            self.assertEqual(performance_summary(settled)["settled"], 1)

    def test_adaptive_weight_waits_for_minimum_sample(self):
        history = []
        for _ in range(3):
            history.append({"status": "settled", "outcome": "up", "factor_scores": {"trend": 20}})
        result = calculate_adaptive_weights(history, minimum_samples=10)
        self.assertEqual(result["weights"]["trend"], 1.0)
        self.assertFalse(result["diagnostics"]["trend"]["active"])


if __name__ == "__main__":
    unittest.main()
