import unittest
from intelligence import detect_market_regime, detect_divergences


class IntelligenceTests(unittest.TestCase):
    def test_regime_identifies_uptrend(self):
        market = {"coins": {"bitcoin": {"change_24h": 2.0, "change_7d": 8.0}}}
        technical = {"assets": {"bitcoin": {"score": 60}}}
        self.assertEqual(detect_market_regime(market, technical)["trend"], "صعودی")

    def test_divergence_detects_positive_price_negative_etf_flow(self):
        market = {
            "coins": {"bitcoin": {"change_7d": 5.0}},
            "etf_flows": {"assets": {"BTC": {"weekly_usd_m": -100.0}}},
        }
        findings = detect_divergences(market, {"assets": {}})
        self.assertTrue(any(item["type"] == "bearish" for item in findings))


if __name__ == "__main__":
    unittest.main()
