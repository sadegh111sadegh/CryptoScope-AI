
from market_data import get_market_snapshot
from news import fetch_news


def score_change(value, scale=5):

    if value is None:
        return None

    return max(-100, min(100, round(value * scale)))


def build_report():

    market = get_market_snapshot()
    headlines = fetch_news()

    factors = []

    change = market.get("market_cap_change_24h_pct")

    factors.append((
        "وضعیت کل بازار",
        score_change(change),
        f"تغییر بازار: {change:.2f}%"
        if change is not None else "داده موجود نیست"
    ))

    fg = market.get("fear_greed")

    fg_score = (
        round((fg["value"] - 50) * 2)
        if fg else None
    )

    factors.append((
        "ترس و طمع",
        fg_score,
        f'{fg["value"]}/100'
        if fg else "داده موجود نیست"
    ))

    btc = market.get("coins", {}).get("bitcoin", {})

    factors.append((
        "قدرت بیت‌کوین",
        score_change(btc.get("change_24h")),
        "تغییر ۲۴ ساعته بیت‌کوین"
    ))

    rsi = market.get("technical", {}).get("rsi_14")

    technical_score = (
        max(-100, min(100, round((rsi - 50) * 2)))
        if rsi is not None else None
    )

    factors.append((
        "تکنیکال بیت‌کوین",
        technical_score,
        f"RSI: {rsi}" if rsi is not None else "ناموجود"
    ))

    scored = [
        value for _, value, _ in factors
        if value is not None
    ]

    score = (
        round(sum(scored) / len(scored))
        if scored else None
    )

    if score is None:
        direction = "نامشخص"
    elif score >= 20:
        direction = "صعودی"
    elif score <= -20:
        direction = "نزولی"
    else:
        direction = "خنثی"

    high = [
        item for item in headlines
        if item.get("score", 0) >= 70
    ][:5]

    return market, direction, score, factors, headlines, high
