import requests

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

QUERIES = [
    '(war OR invasion OR missile OR airstrike OR "military attack")',
    '("Strait of Hormuz" OR sanctions OR "oil infrastructure")',
    '("crypto reserve" OR cryptocurrency OR Bitcoin OR Ethereum)'
]

def score_headline(title):
    title = title.lower()

    rules = [
        (100, ["declares war", "invasion", "war begins"]),
        (90, ["airstrike", "missile strike", "strait of hormuz"]),
        (75, ["military attack", "sanctions", "oil facility"]),
        (45, ["ceasefire", "peace talks", "threatens"]),
        (20, ["interest rate", "central bank", "inflation"])
    ]

    for score, words in rules:
        if any(word in title for word in words):
            return score

    return 10


def fetch_news(max_records=20):
    articles = {}

    for query in QUERIES:
        params = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "sort": "DateDesc",
            "maxrecords": max_records
        }

        try:
            response = requests.get(
                GDELT_URL,
                params=params,
                timeout=25
            )
            response.raise_for_status()

            for item in response.json().get("articles", []):
                url = item.get("url")
                if not url:
                    continue

                title = item.get("title", "")
                articles[url] = {
                    "title": title,
                    "url": url,
                    "source": item.get("domain", ""),
                    "published": item.get("seendate", ""),
                    "score": score_headline(title)
                }

        except Exception as error:
            print("News error:", error)

    return sorted(
        articles.values(),
        key=lambda x: x["score"],
        reverse=True
    )
