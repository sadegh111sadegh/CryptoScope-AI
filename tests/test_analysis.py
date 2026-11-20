import unittest
from unittest.mock import patch

import analysis


class AnalysisTests(unittest.TestCase):
    def sample_market(self):
        return {
            "errors": [],
            "global": {"market_cap_change_24h": 1.2},
            "coins": {"bitcoin": {"change_7d": 4.0}},
            "stablecoins": {"change_7d": 0.5},
            "defi_tvl": {"change_7d": 2.0},
            "etf_flows": {"available": True, "assets": {"BTC": {"weekly_usd_m": 250.0}}},
            "bitcoin_network": {
                "n-transactions": {"change_7d": 3.0},
                "hash-rate": {"change_7d": 2.0},
            },
            "fear_greed": {"value": 68, "label": "Greed"},
        }

    @patch("analysis.analyze_market", return_value={"available": False, "assets": {}})
    @patch("analysis.fetch_news", return_value={"items": [], "available": True})
    @patch("analysis.get_market_snapshot")
    def test_onchain_and_etf_signals_are_included(self, get_market, _news, _technical):
        get_market.return_value = self.sample_market()
        report = analysis.build_report()
        names = [item["name"] for item in report["factors"]]
        self.assertIn("تعداد تراکنش‌های شبکه بیت‌کوین", names)
        self.assertIn("هش‌ریت شبکه بیت‌کوین", names)
        self.assertIn("جریان خالص هفتگی ETF بیت‌کوین", names)
        self.assertIsNotNone(report["score"])
        self.assertEqual(report["confidence"], "بالا")
        self.assertEqual(report["market"]["data_quality"]["available_factors"], 7)

    @patch("analysis.analyze_market", return_value={"available": False, "assets": {}})
    @patch("analysis.fetch_news", return_value={"items": [], "available": False})
    @patch("analysis.get_market_snapshot")
    def test_missing_data_is_not_fabricated(self, get_market, _news, _technical):
        get_market.return_value = {
            "errors": ["source unavailable"],
            "coins": {},
            "global": {},
            "stablecoins": None,
            "defi_tvl": None,
            "etf_flows": {"available": False, "assets": {}},
            "bitcoin_network": {},
            "fear_greed": None,
        }
        report = analysis.build_report()
        self.assertIsNone(report["score"])
        self.assertEqual(report["direction"], "داده کافی نیست")
        self.assertIn("داده کافی", report["horizon"])
        self.assertTrue(all(item["score"] is None for item in report["factors"]))

    @patch("analysis.analyze_market", return_value={"available": False, "assets": {}})
    @patch("analysis.fetch_news", return_value={"items": [], "available": True})
    @patch("analysis.get_market_snapshot")
    def test_news_is_filtered_by_importance(self, get_market, _news, _technical):
        get_market.return_value = self.sample_market()
        _news.return_value = {
            "available": True,
            "items": [
                {"title": "Routine update", "score": 35, "level": "پیگیری"},
                {"title": "Major sanctions", "score": 70, "level": "مهم"},
                {"title": "War begins", "score": 95, "level": "بحرانی"},
            ],
        }
        report = analysis.build_report()
        self.assertEqual(len(report["important_news"]), 2)
        self.assertEqual(len(report["critical_news"]), 1)


if __name__ == "__main__":
    unittest.main()
