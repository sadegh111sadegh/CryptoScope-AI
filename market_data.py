import requests
import os

BASE = "https://api.coingecko.com/api/v3"

def get_market_snapshot():
    headers = {}
    key = os.getenv("COINGECKO_DEMO_API_KEY", "")
    if key:
        headers["x-cg-demo-api-key"] = key

    response = requests.get(
        f"{BASE}/global",
        headers=headers,
        timeout=20
    )
    response.raise_for_status()

    data = response.json()["data"]

    return {
        "market_cap_usd": data["total_market_cap"]["usd"],
        "volume_24h_usd": data["total_volume"]["usd"],
        "btc_dominance": data["market_cap_percentage"]["btc"],
        "market_cap_change_24h_pct":
            data.get("market_cap_change_percentage_24h_usd")
    }
