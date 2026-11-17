from market_data import get_market_snapshot
from news import fetch_news

def build_report():
    market = get_market_snapshot()
    headlines = fetch_news()

    change = market.get("market_cap_change_24h_pct")

    if change is None:
        score = None
        direction = "UNKNOWN"
    else:
        score = max(-100, min(100, round(change * 10)))

        if score > 10:
            direction = "BULLISH"
        elif score < -10:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

    rows = [
        ("MACRO", "N/A"),
        ("FOREX", "N/A"),
        ("ON-CHAIN", "N/A"),
        ("ETF FLOW", "N/A"),
        ("DERIVATIVES", "N/A"),
        ("TECHNICAL", "N/A"),
        ("GEOPOLITICS", "N/A"),
        ("NEWS", "N/A")
    ]

    high = [
        item for item in headlines
        if item["score"] >= 75
    ][:5]

    return market, direction, score, rows, headlines, high
