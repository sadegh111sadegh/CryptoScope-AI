
import requests
from datetime import datetime, timezone

S = requests.Session()
S.headers.update({"User-Agent": "CryptoScope-AI/2.0"})
TIMEOUT = 20


def get_json(url, params=None):
    r = S.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def pct_change(old, new):
    if old in (None, 0) or new is None:
        return None
    return round((new - old) / abs(old) * 100, 2)


def get_market_snapshot():
    data = {"errors": [], "coins": {}, "collected_at": datetime.now(timezone.utc).isoformat()}

    # Global crypto market and asset data
    try:
        g = get_json("https://api.coingecko.com/api/v3/global")["data"]
        data["global"] = {
            "market_cap": g["total_market_cap"]["usd"],
            "volume_24h": g["total_volume"]["usd"],
            "btc_dominance": g["market_cap_percentage"]["btc"],
            "market_cap_change_24h": g.get("market_cap_change_percentage_24h_usd")
        }
    except Exception as e:
        data["errors"].append("CoinGecko global: " + str(e))

    try:
        coins = get_json(
            "https://api.coingecko.com/api/v3/coins/markets",
            {
                "vs_currency": "usd",
                "ids": "bitcoin,ethereum,solana",
                "price_change_percentage": "24h,7d"
            }
        )
        for c in coins:
            data["coins"][c["id"]] = {
                "name": c["name"],
                "price": c.get("current_price"),
                "change_24h": c.get("price_change_percentage_24h"),
                "change_7d": c.get("price_change_percentage_7d_in_currency")
            }
    except Exception as e:
        data["errors"].append("CoinGecko coins: " + str(e))

    # Fear and Greed
    try:
        fg = get_json("https://api.alternative.me/fng/?limit=1")["data"][0]
        data["fear_greed"] = {
            "value": int(fg["value"]),
            "label": fg["value_classification"]
        }
    except Exception as e:
        data["fear_greed"] = None
        data["errors"].append("Fear and Greed: " + str(e))

    # Stablecoin supply: liquidity proxy
    try:
        rows = get_json("https://stablecoins.llama.fi/stablecoincharts/all")
        rows = sorted(rows, key=lambda x: x.get("date", 0))
        if len(rows) >= 8:
            latest = rows[-1].get("totalCirculatingUSD", {}).get("peggedUSD")
            week = rows[-8].get("totalCirculatingUSD", {}).get("peggedUSD")
            month = rows[-31].get("totalCirculatingUSD", {}).get("peggedUSD") if len(rows) >= 31 else None
            data["stablecoins"] = {
                "latest": latest,
                "change_7d": pct_change(week, latest),
                "change_30d": pct_change(month, latest)
            }
    except Exception as e:
        data["stablecoins"] = None
        data["errors"].append("Stablecoin data: " + str(e))

    # DeFi TVL: capital deployed in DeFi protocols
    try:
        tvl = get_json("https://api.llama.fi/v2/historicalChainTvl")
        tvl = sorted(tvl, key=lambda x: x.get("date", 0))
        if len(tvl) >= 8:
            latest = tvl[-1].get("tvl")
            week = tvl[-8].get("tvl")
            month = tvl[-31].get("tvl") if len(tvl) >= 31 else None
            data["defi_tvl"] = {
                "latest": latest,
                "change_7d": pct_change(week, latest),
                "change_30d": pct_change(month, latest)
            }
    except Exception as e:
        data["defi_tvl"] = None
        data["errors"].append("DeFi TVL: " + str(e))

    # Bitcoin network activity
    for chart in ("n-transactions", "hash-rate"):
        try:
            result = get_json(
                f"https://api.blockchain.info/charts/{chart}",
                {"timespan": "30days", "format": "json"}
            )
            values = [x["y"] for x in result.get("values", [])]
            if len(values) >= 8:
                data.setdefault("bitcoin_network", {})[chart] = {
                    "change_7d": pct_change(values[-8], values[-1]),
                    "latest": values[-1]
                }
        except Exception as e:
            data["errors"].append(f"Bitcoin {chart}: {e}")

    return data
