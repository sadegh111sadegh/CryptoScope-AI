import unittest

from technical_analysis import _daily_entry_setup, _ema, _indicators, _rsi


class TechnicalAnalysisTests(unittest.TestCase):
    def test_ema_returns_none_when_history_is_too_short(self):
        self.assertIsNone(_ema([1, 2, 3], 5))

    def test_rsi_detects_persistent_rise(self):
        values = [float(i) for i in range(1, 30)]
        self.assertEqual(_rsi(values), 100.0)

    def test_indicators_score_strong_uptrend_positively(self):
        candles = []
        for i in range(220):
            close = 100 + i
            candles.append({
                "close": close,
                "high": close + 2,
                "low": close - 2,
                "volume": 1000 + (100 if i == 219 else 0),
                "close_time": i,
            })
        result = _indicators(candles)
        self.assertGreater(result["score"], 0)
        self.assertEqual(result["signal"], "تمایل صعودی")
        self.assertIsNotNone(result["ema200"])
        self.assertIsNotNone(result["atr14"])


    def test_daily_entry_setup_returns_entry_stop_and_two_r_target(self):
        setup = _daily_entry_setup({
            "price": 120.0, "atr14": 4.0, "ema20": 115.0,
            "ema50": 110.0, "ema200": 100.0, "rsi14": 60.0,
            "macd_histogram": 1.2, "score": 70,
        })
        self.assertEqual(setup["entry"], 120.0)
        self.assertEqual(setup["stop_loss"], 114.0)
        self.assertEqual(setup["take_profit"], 132.0)
        self.assertEqual(setup["risk_reward"], "1:2")

    def test_daily_entry_setup_skips_overbought_or_misaligned_market(self):
        base = {
            "price": 120.0, "atr14": 4.0, "ema20": 115.0,
            "ema50": 110.0, "ema200": 100.0, "rsi14": 60.0,
            "macd_histogram": 1.2, "score": 70,
        }
        overbought = dict(base, rsi14=75.0)
        bearish = dict(base, ema20=105.0)
        self.assertIsNone(_daily_entry_setup(overbought))
        self.assertIsNone(_daily_entry_setup(bearish))

    def test_indicators_score_strong_downtrend_negatively(self):
        candles = []
        for i in range(220):
            close = 500 - i
            candles.append({
                "close": close,
                "high": close + 2,
                "low": close - 2,
                "volume": 1000,
                "close_time": i,
            })
        result = _indicators(candles)
        self.assertLess(result["score"], 0)
        self.assertEqual(result["signal"], "تمایل نزولی")


if __name__ == "__main__":
    unittest.main()
