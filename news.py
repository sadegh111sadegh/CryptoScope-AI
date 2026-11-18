
import requests
from datetime import datetime, timezone

URL = "https://api.gdeltproject.org/api/v2/doc/doc"

QUERY = (
    '(war OR invasion OR airstrike OR missile OR "military attack" '
    'OR "strait of hormuz" OR sanctions OR "oil supply" '
    'OR "Federal Reserve" OR "interest rate" OR inflation '
    'OR "Bitcoin ETF" OR crypto regulation OR "SEC crypto" '
    'OR "stablecoin" OR "bitcoin reserve")'
)

CRITICAL = [
    "invasion", "declares war", "war begins", "airstrike",
    "missile strike", "military attack", "nuclear", "strait of hormuz",
    "oil facility", "oil supply disruption", "emergency sanctions"
]

IMPORTANT = [
    "sanctions", "ceasefire", "peace talks", "federal reserve",
    "interest rate", "rate cut", "rate hike", "inflation",
    "bitcoin etf", "crypto regulation", "bitcoin reserve",
    "stablecoin", "exchange collapse", "bank failure"
]


def classify(title):
    t = title.lower()

    if any(word in t for word in CRITICAL):
        return 95, "بحرانی"
    if any(word in t for word in IMPORTANT):
        return 70, "مهم"
    return 35, "عادی"


def fetch_news(max_records=30):
    result = {
        "items": [],
        "available": False,
        "error": None,
        "checked_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        response = requests.get(
            URL,
            params={
                "query": QUERY,
                "mode": "ArtList",
                "format": "json",
                "sort": "DateDesc",
                "maxrecords": max_records,
                "timespan": "48h"
            },
            timeout=30
        )
        response.raise_for_status()

        articles = response.json().get("articles", [])
        result["available"] = True

        seen = set()
        for item in articles:
            title = item.get("title", "").strip()
            link = item.get("url", "")

            if not title or not link or link in seen:
                continue

            seen.add(link)
            score, level = classify(title)

            result["items"].append({
                "title": title,
                "url": link,
                "source": item.get("domain", "نامشخص"),
                "published": item.get("seendate", ""),
                "score": score,
                "level": level
            })

        result["items"].sort(
            key=lambda x: (x["score"], x["published"]),
            reverse=True
        )

    except Exception as e:
        result["error"] = str(e)

    return result
