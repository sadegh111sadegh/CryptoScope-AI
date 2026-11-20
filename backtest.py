"""Historical, long-only spot backtest with next-candle execution.

The strategy is deliberately transparent: EMA trend filter + RSI confirmation,
ATR stop/target, taker fees and slippage on both entry and exit. It is a
research tool, not a live trading engine.
"""
from datetime import datetime, timezone

from market_data import get_json

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"


def _ema(values, period):
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1)
    value = sum(values[:period]) / period
    for item in values[period:]:
        value = item * alpha + value * (1 - alpha)
    return value


def _rsi(values, period=14):
    if len(values) <= period:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes[-period:]]
    losses = [max(-change, 0.0) for change in changes[-period:]]
    avg_gain, avg_loss = sum(gains) / period, sum(losses) / period
    if avg_loss == 0:
        return 100.0 if avg_gain else 50.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


def _atr(candles, period=14):
    if len(candles) <= period:
        return None
    ranges = []
    for i in range(1, len(candles)):
        ranges.append(max(
            candles[i]["high"] - candles[i]["low"],
            abs(candles[i]["high"] - candles[i - 1]["close"]),
            abs(candles[i]["low"] - candles[i - 1]["close"]),
        ))
    return sum(ranges[-period:]) / period


def fetch_candles(symbol="BTCUSDT", interval="4h", limit=1000):
    """Fetch recent historical Binance spot candles; discard the live candle."""
    raw = get_json(BINANCE_KLINES, {
        "symbol": symbol, "interval": interval, "limit": min(max(int(limit), 250), 1000),
    })
    if not isinstance(raw, list) or len(raw) < 220:
        raise ValueError("تعداد کندل‌های تاریخی برای بک‌تست کافی نیست")
    rows = raw[:-1]
    return [{
        "open_time": int(row[0]),
        "open": float(row[1]),
        "high": float(row[2]),
        "low": float(row[3]),
        "close": float(row[4]),
        "volume": float(row[5]),
        "close_time": int(row[6]),
    } for row in rows]


def run_backtest(candles, initial_balance=10000.0, fee_rate=0.001, slippage_rate=0.0005,
                 atr_multiple=2.0, reward_risk=2.0):
    """Run an all-in long-only strategy, executing signals on the next candle.

    If stop and target are both touched in one candle, stop is assumed first
    (conservative intrabar ordering). Open positions are liquidated at the
    final close, including exit costs.
    """
    if len(candles) < 220:
        raise ValueError("حداقل ۲۲۰ کندل لازم است")
    if initial_balance <= 0 or not 0 <= fee_rate < 0.1 or not 0 <= slippage_rate < 0.1:
        raise ValueError("پارامترهای سرمایه، کارمزد یا لغزش قیمت معتبر نیستند")

    balance = float(initial_balance)
    position = None
    trades = []
    equity_curve = []
    closes = []

    for i, candle in enumerate(candles):
        closes.append(candle["close"])
        equity = balance
        if position:
            equity = position["quantity"] * candle["close"]
        equity_curve.append({"time": candle.get("close_time", i), "equity": equity})

        if position:
            stop_hit = candle["low"] <= position["stop"]
            target_hit = candle["high"] >= position["target"]
            exit_reason = None
            raw_exit = None
            if stop_hit:
                raw_exit, exit_reason = position["stop"], "stop"
            elif target_hit:
                raw_exit, exit_reason = position["target"], "target"
            elif i > position["entry_index"] and closes[-1] < position["ema50_at_signal"]:
                raw_exit, exit_reason = candle["close"], "ema_exit"

            if raw_exit is not None:
                fill = raw_exit * (1 - slippage_rate)
                proceeds = position["quantity"] * fill * (1 - fee_rate)
                pnl = proceeds - position["cost_basis"]
                trades.append({
                    "entry_time": position["entry_time"],
                    "exit_time": candle.get("close_time", i),
                    "entry_price": position["entry_price"],
                    "exit_price": fill,
                    "pnl": pnl,
                    "return_pct": pnl / position["cost_basis"] * 100,
                    "reason": exit_reason,
                })
                balance = proceeds
                position = None
                equity_curve[-1]["equity"] = balance
                continue

        # Indicators at candle i are used only to decide an entry at candle i+1 open.
        if position is None and i < len(candles) - 1 and i >= 200:
            history = closes[:i + 1]
            ema50 = _ema(history, 50)
            ema200 = _ema(history, 200)
            rsi = _rsi(history, 14)
            atr = _atr(candles[:i + 1], 14)
            if (ema50 is not None and ema200 is not None and rsi is not None and atr
                    and candle["close"] > ema50 > ema200 and 50 <= rsi <= 70):
                next_candle = candles[i + 1]
                raw_entry = next_candle["open"]
                entry_price = raw_entry * (1 + slippage_rate)
                quantity = balance / (entry_price * (1 + fee_rate))
                cost_basis = balance
                stop = entry_price - atr_multiple * atr
                risk = entry_price - stop
                target = entry_price + reward_risk * risk
                position = {
                    "quantity": quantity,
                    "cost_basis": cost_basis,
                    "entry_price": entry_price,
                    "entry_time": next_candle.get("open_time", i + 1),
                    "entry_index": i + 1,
                    "stop": stop,
                    "target": target,
                    "ema50_at_signal": ema50,
                }
                balance = 0.0

    if position:
        last = candles[-1]
        fill = last["close"] * (1 - slippage_rate)
        proceeds = position["quantity"] * fill * (1 - fee_rate)
        pnl = proceeds - position["cost_basis"]
        trades.append({
            "entry_time": position["entry_time"],
            "exit_time": last.get("close_time", len(candles) - 1),
            "entry_price": position["entry_price"],
            "exit_price": fill,
            "pnl": pnl,
            "return_pct": pnl / position["cost_basis"] * 100,
            "reason": "end_of_test",
        })
        balance = proceeds
        equity_curve[-1]["equity"] = balance

    final_equity = balance
    peak = float(initial_balance)
    max_drawdown = 0.0
    for point in equity_curve:
        peak = max(peak, point["equity"])
        if peak:
            max_drawdown = min(max_drawdown, (point["equity"] / peak - 1) * 100)

    wins = [trade for trade in trades if trade["pnl"] > 0]
    losses = [trade for trade in trades if trade["pnl"] < 0]
    gross_profit = sum(trade["pnl"] for trade in wins)
    gross_loss = abs(sum(trade["pnl"] for trade in losses))
    first_close, last_close = candles[0]["close"], candles[-1]["close"]
    buy_hold = initial_balance * (last_close / first_close) if first_close else initial_balance
    start_ts = candles[0].get("open_time")
    end_ts = candles[-1].get("close_time")
    return {
        "symbol": candles[0].get("symbol", "BTCUSDT"),
        "interval": candles[0].get("interval", "4h"),
        "candles": len(candles),
        "start": datetime.fromtimestamp(start_ts / 1000, timezone.utc).isoformat() if start_ts else None,
        "end": datetime.fromtimestamp(end_ts / 1000, timezone.utc).isoformat() if end_ts else None,
        "initial_balance": initial_balance,
        "final_balance": final_equity,
        "net_profit": final_equity - initial_balance,
        "return_pct": (final_equity / initial_balance - 1) * 100,
        "buy_hold_return_pct": (buy_hold / initial_balance - 1) * 100,
        "max_drawdown_pct": max_drawdown,
        "trades": len(trades),
        "win_rate_pct": len(wins) / len(trades) * 100 if trades else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else (None if not gross_profit else float("inf")),
        "trades_detail": trades,
        "equity_curve": equity_curve,
        "assumptions": {
            "fee_rate_each_side": fee_rate,
            "slippage_each_side": slippage_rate,
            "stop_atr_multiple": atr_multiple,
            "reward_risk": reward_risk,
            "execution": "next candle open",
            "same_candle_stop_and_target": "stop first",
        },
    }


def run_market_backtest(symbol="BTCUSDT", interval="4h", limit=1000,
                        initial_balance=10000.0, fee_rate=0.001, slippage_rate=0.0005):
    candles = fetch_candles(symbol=symbol, interval=interval, limit=limit)
    for candle in candles:
        candle["symbol"] = symbol
        candle["interval"] = interval
    return run_backtest(candles, initial_balance, fee_rate, slippage_rate)
