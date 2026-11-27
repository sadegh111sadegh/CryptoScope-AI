import unittest
from datetime import datetime, timezone

from options_expiry import get_options_expiry_snapshot


class FakeResponse:
    def __init__(self, rows):
        self.rows = rows

    def raise_for_status(self):
        pass

    def json(self):
        return {"result": self.rows}


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        currency = params["currency"]
        return FakeResponse([
            row for row in self.rows
            if row["instrument_name"].startswith(currency + "-")
        ])


class OptionsExpiryTests(unittest.TestCase):
    def test_groups_open_interest_by_expiry_and_strike(self):
        rows = [
            {"instrument_name": "BTC-27NOV26-80000-C", "open_interest": 12,
             "underlying_price": 70000, "volume": 2},
            {"instrument_name": "BTC-27NOV26-70000-P", "open_interest": 8,
             "underlying_price": 70000, "volume": 3},
            {"instrument_name": "BTC-28NOV26-75000-C", "open_interest": 5,
             "underlying_price": 70000, "volume": 1},
            {"instrument_name": "BTC-20NOV26-70000-P", "open_interest": 99,
             "underlying_price": 70000, "volume": 9},
        ]
        session = FakeSession(rows)
        now = datetime(2026, 11, 27, 0, 0, tzinfo=timezone.utc)
        result = get_options_expiry_snapshot(now=now, session=session)

        btc = result["assets"]["BTC"]
        self.assertEqual(len(btc), 2)
        self.assertEqual(btc[0]["total_oi"], 20)
        self.assertEqual(btc[0]["call_oi"], 12)
        self.assertEqual(btc[0]["put_oi"], 8)
        self.assertEqual(btc[0]["top_strikes"][0]["strike"], "80000")
        self.assertEqual(btc[0]["oi_usd"], 1400000)
        self.assertTrue(result["available"])
        self.assertEqual(len(session.calls), 2)

    def test_empty_api_data_is_not_available(self):
        session = FakeSession([])
        now = datetime(2026, 11, 27, 0, 0, tzinfo=timezone.utc)
        result = get_options_expiry_snapshot(now=now, session=session)
        self.assertFalse(result["available"])
        self.assertEqual(result["expiry_risk"], "کم")


if __name__ == "__main__":
    unittest.main()
