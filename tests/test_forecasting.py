import unittest
from forecasting import forecast_scenarios


class ForecastingTests(unittest.TestCase):
    def test_probabilities_are_normalized(self):
        result = forecast_scenarios(
            45, {"trend": "صعودی"}, [], 6
        )
        self.assertTrue(result["available"])
        self.assertAlmostEqual(sum(result["probabilities"].values()), 100.0, places=1)
        self.assertFalse(result["calibrated"])

    def test_insufficient_data_does_not_forecast(self):
        self.assertFalse(forecast_scenarios(None, {}, [], 0)["available"])


if __name__ == "__main__":
    unittest.main()
