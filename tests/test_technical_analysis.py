import unittest

from technical_analysis import _ema, _indicators, _rsi


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
