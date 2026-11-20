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
        score += 20 if macd_hist > 0 else -20 if macd_hist < 0 else 0

    if volume_ratio is not None and volume_ratio >= 1.5:
        score += 10 if closes[-1] > closes[-2] else -10 if closes[-1] < closes[-2] else 0

    score = max(-100, min(100, score))
    signal = "تمایل صعودی" if score >= 25 else "تمایل نزولی" if score <= -25 else "خنثی"
    return {
        "price": closes[-1],
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200,
        "rsi14": rsi,
        "macd_histogram": macd_hist,
        "atr14": atr,
        "volume_ratio": volume_ratio,
        "score": score,
        "signal": signal,
        "candle_close_time": candles[-1]["close_time"],
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
                # The last Binance candle can still be forming; never score it.
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
