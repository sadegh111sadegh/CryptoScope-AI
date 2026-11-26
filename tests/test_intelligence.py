import unittest
from intelligence import detect_market_regime, detect_divergences


def timeframe(direction=1, adx=25, range_width=8, atr_pct=3):
    if direction > 0:
        price, ema20, ema50, ema200 = 110, 108, 105, 100
        slope20, slope50 = 1.2, 0.7
    elif direction < 0:
        price, ema20, ema50, ema200 = 90, 92, 95, 100
        slope20, slope50 = -1.2, -0.7
    else:
        price, ema20, ema50, ema200 = 100, 100, 100, 100
        slope20, slope50 = 0.0, 0.0
    return {
        "price": price, "ema20": ema20, "ema50": ema50, "ema200": ema200,
        "ema20_slope_pct": slope20, "ema50_slope_pct": slope50,
        "adx14": adx, "range_width_pct": range_width, "atr_pct": atr_pct,
        "structure_direction": direction,
    }


class IntelligenceTests(unittest.TestCase):
    def detect(self, daily, four_hour):
        technical = {"assets": {"bitcoin": {
            "score": 40 if daily["price"] > daily["ema20"] else -40,
            "timeframes": {"1d": daily, "4h": four_hour},
        }}}
        return detect_market_regime({}, technical)

    def test_regime_identifies_confirmed_uptrend(self):
        self.assertEqual(self.detect(timeframe(1), timeframe(1))["trend"], "صعودی")

    def test_regime_identifies_confirmed_downtrend(self):
        self.assertEqual(self.detect(timeframe(-1), timeframe(-1))["trend"], "نزولی")

    def test_regime_identifies_tight_low_adx_range(self):
        result = self.detect(
            timeframe(0, adx=14, range_width=7),
            timeframe(0, adx=15, range_width=7),
        )
        self.assertEqual(result["label"], "بازار رنج")

    def test_regime_identifies_pullback_inside_uptrend(self):
        result = self.detect(timeframe(1), timeframe(-1))
        self.assertEqual(result["label"], "اصلاح در ساختار بزرگ‌تر صعودی")
        self.assertEqual(result["trend"], "ترکیبی")

    def test_regime_is_unknown_without_daily_structure(self):
        result = detect_market_regime({}, {"assets": {"bitcoin": {"timeframes": {}}}})
        self.assertEqual(result["trend"], "نامشخص")

    def test_divergence_detects_positive_price_negative_etf_flow(self):
        market = {
            "coins": {"bitcoin": {"change_7d": 5.0}},
            "etf_flows": {"assets": {"BTC": {"weekly_usd_m": -100.0}}},
        }
        findings = detect_divergences(market, {"assets": {}})
        self.assertTrue(any(item["type"] == "bearish" for item in findings))


if __name__ == "__main__":
    unittest.main()
