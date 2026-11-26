"""Multi-timeframe technical analysis using completed Binance spot candles.

This module reports indicator evidence; it does not place orders or promise returns.
"""
from market_data import get_json

BASE_URL = "https://api.binance.com/api/v3/klines"
MARKETS = {
    "bitcoin": ("BTCUSDT", "بیت‌کوین"),
    "ethereum": ("ETHUSDT", "اتریوم"),
    "solana": ("SOLUSDT", "سولانا"),
}
TIMEFRAMES = {"1d": 3, "4h": 2, "1h": 1}


def _ema(values, period):
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1)
    result = sum(values[:period]) / period
    for value in values[period:]:
        result = value * alpha + result * (1 - alpha)
    return result


def _rsi(values, period=14):
    if len(values) <= period:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes[-period:]]
    losses = [max(-change, 0.0) for change in changes[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return 100 - (100 / (1 + avg_gain / avg_loss))


def _adx(highs, lows, closes, period=14):
    """Wilder's smoothed ADX; returns None until enough completed candles exist."""
    if len(closes) < (period * 2 + 1):
        return None
    true_ranges, plus_moves, minus_moves = [], [], []
    for i in range(1, len(closes)):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_moves.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_moves.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        true_ranges.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))

    tr_smooth = sum(true_ranges[:period])
    plus_smooth = sum(plus_moves[:period])
    minus_smooth = sum(minus_moves[:period])
    dx_values = []

    def dx_value(tr, plus, minus):
        if tr <= 0:
            return 0.0
        plus_di = 100 * plus / tr
        minus_di = 100 * minus / tr
        denominator = plus_di + minus_di
        return 100 * abs(plus_di - minus_di) / denominator if denominator else 0.0

    dx_values.append(dx_value(tr_smooth, plus_smooth, minus_smooth))
    for i in range(period, len(true_ranges)):
        tr_smooth = tr_smooth - (tr_smooth / period) + true_ranges[i]
        plus_smooth = plus_smooth - (plus_smooth / period) + plus_moves[i]
        minus_smooth = minus_smooth - (minus_smooth / period) + minus_moves[i]
        dx_values.append(dx_value(tr_smooth, plus_smooth, minus_smooth))

    if len(dx_values) < period:
        return None
    adx = sum(dx_values[:period]) / period
    for value in dx_values[period:]:
        adx = ((adx * (period - 1)) + value) / period
    return adx

def _indicators(candles):
    closes = [row["close"] for row in candles]
    highs = [row["high"] for row in candles]
    lows = [row["low"] for row in candles]
    volumes = [row["volume"] for row in candles]
    if len(closes) < 200:
        raise ValueError("حداقل ۲۰۰ کندل بسته‌شده برای تحلیل لازم است")

    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    ema200 = _ema(closes, 200)
    ema20_previous = _ema(closes[:-5], 20) if len(closes) > 205 else None
    ema50_previous = _ema(closes[:-5], 50) if len(closes) > 205 else None
    ema20_slope_pct = ((ema20 / ema20_previous) - 1) * 100 if ema20 and ema20_previous else None
    ema50_slope_pct = ((ema50 / ema50_previous) - 1) * 100 if ema50 and ema50_previous else None
    rsi = _rsi(closes)
    macd_line = _ema(closes, 12) - _ema(closes, 26)
    signal_series = []
    for end in range(26, len(closes) + 1):
        fast = _ema(closes[:end], 12)
        slow = _ema(closes[:end], 26)
        signal_series.append(fast - slow)
    macd_signal = _ema(signal_series, 9) if len(signal_series) >= 9 else None
    macd_hist = macd_line - macd_signal if macd_signal is not None else None

    true_ranges = []
    for i in range(1, len(candles)):
        true_ranges.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))
    atr = sum(true_ranges[-14:]) / 14 if len(true_ranges) >= 14 else None
    atr_pct = (atr / closes[-1] * 100) if atr is not None and closes[-1] else None
    adx = _adx(highs, lows, closes)
    range_width_pct = (
        (max(highs[-20:]) - min(lows[-20:])) / closes[-1] * 100
        if closes[-1] else None
    )
    previous_swing_high = max(highs[-20:-10])
    recent_swing_high = max(highs[-10:])
    previous_swing_low = min(lows[-20:-10])
    recent_swing_low = min(lows[-10:])
    structure_direction = (
        1 if recent_swing_high > previous_swing_high and recent_swing_low > previous_swing_low else
        -1 if recent_swing_high < previous_swing_high and recent_swing_low < previous_swing_low else
        0
    )
    volume_avg = sum(volumes[-21:-1]) / 20 if len(volumes) >= 21 else None
    volume_ratio = volumes[-1] / volume_avg if volume_avg else None

    score = 0
    if closes[-1] > ema20 > ema50 > ema200:
        score += 40
    elif closes[-1] < ema20 < ema50 < ema200:
        score -= 40
    else:
        score += 15 if closes[-1] > ema50 else -15
        score += 10 if ema20 > ema50 else -10
        score += 5 if ema50 > ema200 else -5

    if rsi is not None:
        if 55 <= rsi <= 70:
            score += 15
        elif 30 <= rsi < 45:
            score -= 15
        elif rsi > 75:
            score -= 8
        elif rsi < 25:
            score += 8

    if macd_hist is not None:
        if macd_hist > 1e-8:
            score += 20
        elif macd_hist < -1e-8:
            score -= 20

    if volume_ratio is not None and volume_ratio >= 1.5:
        score += 10 if closes[-1] > closes[-2] else -10 if closes[-1] < closes[-2] else 0

    score = max(-100, min(100, score))
    signal = "تمایل صعودی" if score >= 25 else "تمایل نزولی" if score <= -25 else "خنثی"
    return {
        "price": closes[-1],
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "ema20_slope_pct": ema20_slope_pct,
        "ema50_slope_pct": ema50_slope_pct,
        "rsi14": rsi,
        "macd_histogram": macd_hist,
        "atr14": atr,
        "atr_pct": atr_pct,
        "adx14": adx,
        "range_width_pct": range_width_pct,
        "structure_direction": structure_direction,
        "volume_ratio": volume_ratio,
        "score": score,
        "signal": signal,
        "candle_close_time": candles[-1]["close_time"],
    }


def _daily_entry_setup(indicators):
    """Return a conservative long setup only when the completed daily trend aligns."""
    entry = indicators.get("price")
    atr = indicators.get("atr14")
    ema20 = indicators.get("ema20")
    ema50 = indicators.get("ema50")
    ema200 = indicators.get("ema200")
    rsi = indicators.get("rsi14")
    macd_hist = indicators.get("macd_histogram")
    score = indicators.get("score")

    if not all(value is not None for value in (
        entry, atr, ema20, ema50, ema200, rsi, macd_hist, score
    )):
        return None
    if not (score >= 50 and entry > ema20 > ema50 > ema200):
        return None
    if not (50 <= rsi <= 68 and macd_hist > 0 and atr > 0):
        return None

    stop_loss = entry - (1.5 * atr)
    risk = entry - stop_loss
    if stop_loss <= 0 or risk <= 0:
        return None
    return {
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": entry + (2 * risk),
        "risk_reward": "1:2",
        "basis": "daily_close_atr",
    }


def analyze_market():
    """Return per-asset, per-timeframe indicators and weighted consensus."""
    result = {"available": False, "assets": {}, "source": "Binance Spot"}
    for asset_id, (symbol, name) in MARKETS.items():
        timeframes = {}
        errors = []
        for interval, weight in TIMEFRAMES.items():
            try:
                raw = get_json(BASE_URL, {
                    "symbol": symbol, "interval": interval, "limit": 220,
                })
                rows = raw[:-1]
                candles = [{
                    "close": float(row[4]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "volume": float(row[5]),
                    "close_time": int(row[6]),
                } for row in rows]
                indicators = _indicators(candles)
                indicators["weight"] = weight
                if interval == "1d":
                    indicators["entry_setup"] = _daily_entry_setup(indicators)
                timeframes[interval] = indicators
            except Exception as exc:
                errors.append(interval + ": " + str(exc))

        valid = list(timeframes.values())
        consensus = None
        if len(valid) >= 2:
            total_weight = sum(item["weight"] for item in valid)
            consensus = round(sum(item["score"] * item["weight"] for item in valid) / total_weight)
        result["assets"][asset_id] = {
            "symbol": symbol,
            "name": name,
            "timeframes": timeframes,
            "score": consensus,
            "signal": (
                "تمایل صعودی" if consensus is not None and consensus >= 25 else
                "تمایل نزولی" if consensus is not None and consensus <= -25 else
                "خنثی" if consensus is not None else "داده کافی نیست"
            ),
            "errors": errors,
        }
    result["available"] = any(item["score"] is not None for item in result["assets"].values())
    return result
