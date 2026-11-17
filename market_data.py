
import os
import requests
from statistics import mean

BASE = "https://api.coingecko.com/api/v3"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "CryptoScope-AI/1.0"})

key = os.getenv("COINGECKO_DEMO_API_KEY", "")
if key:
    SESSION.headers["x-cg-demo-api-key"] = key


def get_data(url, params=None):
    response = SESSION.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def calculate_rsi(prices, period=14):
    if len(prices) <= period:
        return None

    changes = [
        prices[i] - prices[i - 1]
        for i in range(1, len(prices))
    ]

    gains = [max(x, 0) for x in changes[-period:]]
    losses = [abs(min(x, 0)) for x in changes[-period:]]

    avg_gain = mean(gains)
    avg_loss = mean(losses)

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def get_market_snapshot():

    result = {"errors": []}

    try:
        data = get_data(f"{BASE}/global")["data"]

        result.update({
            "market_cap_usd": data["total_market_cap"]["usd"],
            "volume_24h_usd": data["total_volume"]["usd"],
            "btc_dominance": data["market_cap_percentage"]["btc"],
            "eth_dominance": data["market_cap_percentage"]["eth"],
            "market_cap_change_24h_pct":
                data.get("market_cap_change_percentage_24h_usd")
        })

    except Exception as error:
        result["errors"].append(f"Market: {error}")

    try:
        coins = get_data(
            f"{BASE}/coins/markets",
            {
                "vs_currency": "usd",
                "ids": "bitcoin,ethereum,cardano,solana",
                "price_change_percentage": "1h,24h,7d"
            }
        )

        result["coins"] = {
            coin["id"]: {
                "name": coin["name"],
                "symbol": coin["symbol"].upper(),
                "price": coin["current_price"],
                "change_1h": coin.get(
                    "price_change_percentage_1h_in_currency"
                ),
                "change_24h": coin.get(
                    "price_change_percentage_24h_in_currency"
                ),
                "change_7d": coin.get(
                    "price_change_percentage_7d_in_currency"
                )
            }
            for coin in coins
        }

    except Exception as error:
        result["coins"] = {}
        result["errors"].append(f"Coins: {error}")

    try:
        fg = get_data(
            "https://api.alternative.me/fng/?limit=1&format=json"
        )

        item = fg["data"][0]

        result["fear_greed"] = {
            "value": int(item["value"]),
            "label": item["value_classification"]
        }

    except Exception as error:
        result["fear_greed"] = None
        result["errors"].append(f"Fear Greed: {error}")

    try:
        chart = get_data(
            f"{BASE}/coins/bitcoin/market_chart",
            {"vs_currency": "usd", "days": "14"}
        )

        prices = [p[1] for p in chart["prices"]]

        result["technical"] = {
            "rsi_14": calculate_rsi(prices),
            "sma_7": round(mean(prices[-7:]), 2),
            "sma_14": round(mean(prices[-14:]), 2)
        }

    except Exception as error:
        result["technical"] = {}
        result["errors"].append(f"Technical: {error}")

    return result
