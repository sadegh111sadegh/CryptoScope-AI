import unittest

from backtest import run_backtest


def make_candles(closes):
    candles = []
    for i, close in enumerate(closes):
        candles.append({
            "open_time": i * 14400000,
            "close_time": (i + 1) * 14400000 - 1,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1000.0,
        })
    return candles


class BacktestTests(unittest.TestCase):
    def test_flat_market_does_not_create_trades(self):
        candles = make_candles([100.0] * 260)
        result = run_backtest(candles)
        self.assertEqual(result["trades"], 0)
        self.assertAlmostEqual(result["return_pct"], 0.0)
        self.assertEqual(result["max_drawdown_pct"], 0.0)

    def test_backtest_reports_costs_and_benchmark(self):
        closes = [100.0 + i * 0.2 for i in range(260)]
        result = run_backtest(
            make_candles(closes),
            initial_balance=5000,
            fee_rate=0.001,
            slippage_rate=0.0005,
        )
        self.assertEqual(result["initial_balance"], 5000)
        self.assertIn("buy_hold_return_pct", result)
        self.assertIn("max_drawdown_pct", result)
        self.assertEqual(result["assumptions"]["execution"], "next candle open")
        self.assertGreaterEqual(result["trades"], 0)

    def test_invalid_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            run_backtest(make_candles([100.0] * 260), initial_balance=0)


if __name__ == "__main__":
    unittest.main()
