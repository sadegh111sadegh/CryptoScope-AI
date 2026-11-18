import requests
from datetime import datetime, timezone

URL = "https://api.gdeltproject.org/api/v2/doc/doc"
QUERIES = {
    "ژئوپلیتیک و انرژی": '(war OR invasion OR airstrike OR missile OR "military attack" OR "strait of hormuz" OR sanctions OR "oil supply disruption")',
    "اقتصاد کلان": '("Federal Reserve" OR "interest rate" OR inflation OR recession OR "central bank" OR "oil prices")',
    "کریپتو و مقررات": '("Bitcoin ETF" OR "crypto regulation" OR "SEC crypto" OR stablecoin OR "bitcoin reserve" OR exchange hack OR crypto exchange)',
}
CRITICAL = ("invasion", "declares war", "war begins", "airstrike", "missile strike", "military attack", "nuclear", "strait of hormuz", "oil facility", "oil supply disruption", "exchange collapse", "bank failure")
IMPORTANT = ("sanctions", "ceasefire", "peace talks", "federal reserve", "interest rate", "rate cut", "rate hike", "inflation", "bitcoin etf", "crypto regulation", "bitcoin reserve", "stablecoin", "exchange hack", "sec ")

def classify(title):
    text = title.casefold()
    if any(term in text for term in CRITICAL):
        return 95, "بحرانی"
    if any(term in text for term in IMPORTANT):
        return 70, "مهم"
    return 35, "پیگیری"

def fetch_news(max_records=25):
    result = {"items": [], "available": False, "feeds_ok": 0, "feeds_total": len(QUERIES),
              "errors": [], "checked_at": datetime.now(timezone.utc).isoformat()}
    session = requests.Session()
    session.headers.update({"User-Agent": "CryptoScope-AI/3.0"})
    seen = set()
    for category, query in QUERIES.items():
        try:
            response = session.get(URL, params={
                "query": query, "mode": "ArtList", "format": "json",
                "sort": "DateDesc", "maxrecords": max_records, "timespan": "48h",
            }, timeout=25)
            response.raise_for_status()
            payload = response.json()
            result["feeds_ok"] += 1
            for article in payload.get("articles", []):
                title = (article.get("title") or "").strip()
                link = (article.get("url") or "").strip()
                if not title or not link or link in seen or not link.startswith(("https://", "http://")):
                    continue
                seen.add(link)
                score, level = classify(title)
                result["items"].append({
                    "title": title, "url": link, "source": article.get("domain") or "منبع نامشخص",
                    "published": article.get("seendate") or "", "category": category,
                    "score": score, "level": level,
                })
        except Exception as exc:
            result["errors"].append(category + ": " + str(exc))
    result["available"] = result["feeds_ok"] > 0
    result["items"].sort(key=lambda item: (item["score"], item["published"]), reverse=True)
    return result
