import requests
import os
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "CryptoScope-AI/3.0"})
_retry = Retry(total=3, connect=3, read=3, backoff_factor=0.7, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=frozenset(["GET"]))
SESSION.mount("https://", HTTPAdapter(max_retries=_retry))
TIMEOUT = 25

def get_json(url, params=None, headers=None):
    response = SESSION.get(url, params=params, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()

def pct_change(old, new):
    try:
        old, new = float(old), float(new)
        if old == 0:
            return None
        return round((new - old) / abs(old) * 100, 3)
    except (TypeError, ValueError):
        return None

def _stable_total(row):
    value = (row.get("totalCirculatingUSD") or {}).get("peggedUSD")
    if isinstance(value, dict):
        value = value.get("circulating")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _series_snapshot(rows, key):
    rows = sorted(rows, key=lambda item: item.get("date", 0))
    values = []
    for row in rows:
        try:
            values.append(float(row.get(key)))
        except (TypeError, ValueError):
            values.append(None)
    valid = [v for v in values if v is not None]
    if len(valid) < 8:
        return None
    return {
        "latest": valid[-1],
        "change_7d": pct_change(valid[-8], valid[-1]),
        "change_30d": pct_change(valid[-31], valid[-1]) if len(valid) >= 31 else None,
    }

def _fetch_etf_flows(data):
    api_key = os.getenv("CRYPTOETF_API_KEY", "").strip()
    if not api_key:
        data["etf_flows"] = {"available": False, "reason": "CRYPTOETF_API_KEY is not configured"}
        return
    result = {"available": True, "assets": {}, "source": "CryptoETF.today"}
    headers = {"Authorization": "Bearer " + api_key}
    for symbol, asset in (("BTC", "btc"), ("ETH", "eth"), ("SOL", "sol")):
        try:
            payload = get_json("https://api.cryptoetf.today/api/v1/flows/" + asset, headers=headers)
            days = payload.get("days") or []
            valid = [row for row in days if row.get("netFlowUsdM") is not None]
            valid.sort(key=lambda row: row.get("date", ""))
            if not valid:
                raise ValueError("No published flow records")
            latest = valid[-1]
            recent = valid[-7:]
            result["assets"][symbol] = {
                "date": latest.get("date"),
                "daily_usd_m": float(latest["netFlowUsdM"]),
                "weekly_usd_m": round(sum(float(row["netFlowUsdM"]) for row in recent), 2),
                "days_count": len(recent),
            }
            result["updated_at"] = payload.get("updatedAt") or result.get("updated_at")
        except Exception as exc:
            result["assets"][symbol] = None
            data["errors"].append("ETF " + symbol + " flows: " + str(exc))
    result["available"] = any(value is not None for value in result["assets"].values())
    data["etf_flows"] = result


def get_market_snapshot():
    data = {"errors": [], "coins": {}, "collected_at": datetime.now(timezone.utc).isoformat()}
    try:
        g = get_json("https://api.coingecko.com/api/v3/global")["data"]
        data["global"] = {
            "market_cap": g.get("total_market_cap", {}).get("usd"),
            "volume_24h": g.get("total_volume", {}).get("usd"),
            "btc_dominance": g.get("market_cap_percentage", {}).get("btc"),
            "market_cap_change_24h": g.get("market_cap_change_percentage_24h_usd"),
        }
    except Exception as exc:
        data["errors"].append("CoinGecko global: " + str(exc))
    try:
        coins = get_json("https://api.coingecko.com/api/v3/coins/markets", {
            "vs_currency": "usd", "ids": "bitcoin,ethereum,solana",
            "price_change_percentage": "24h,7d", "order": "market_cap_desc",
            "per_page": 10, "page": 1, "sparkline": "false",
        })
        for coin in coins:
            data["coins"][coin["id"]] = {
                "name": coin.get("name"), "price": coin.get("current_price"),
                "change_24h": coin.get("price_change_percentage_24h"),
                "change_7d": coin.get("price_change_percentage_7d_in_currency"),
            }
    except Exception as exc:
        data["errors"].append("CoinGecko assets: " + str(exc))
    try:
        row = get_json("https://api.alternative.me/fng/?limit=1")["data"][0]
        data["fear_greed"] = {"value": int(row["value"]), "label": row.get("value_classification", "")}
    except Exception as exc:
        data["fear_greed"] = None
        data["errors"].append("Fear & Greed: " + str(exc))
    try:
        rows = get_json("https://stablecoins.llama.fi/stablecoincharts/all")
        rows = sorted(rows, key=lambda item: item.get("date", 0))
        totals = [_stable_total(row) for row in rows]
        valid = [v for v in totals if v is not None]
        if len(valid) >= 8:
            data["stablecoins"] = {
                "latest": valid[-1], "change_7d": pct_change(valid[-8], valid[-1]),
                "change_30d": pct_change(valid[-31], valid[-1]) if len(valid) >= 31 else None,
            }
    except Exception as exc:
        data["stablecoins"] = None
        data["errors"].append("Stablecoin supply: " + str(exc))
    try:
        data["defi_tvl"] = _series_snapshot(get_json("https://api.llama.fi/v2/historicalChainTvl"), "tvl")
    except Exception as exc:
        data["defi_tvl"] = None
        data["errors"].append("DeFi TVL: " + str(exc))
    for chart in ("n-transactions", "hash-rate"):
        try:
            result = get_json("https://api.blockchain.info/charts/" + chart, {"timespan": "30days", "format": "json"})
            values = []
            for item in result.get("values", []):
                try:
                    values.append(float(item.get("y")))
                except (TypeError, ValueError):
                    pass
            if len(values) >= 8:
                data.setdefault("bitcoin_network", {})[chart] = {
                    "latest": values[-1], "change_7d": pct_change(values[-8], values[-1]),
                }
        except Exception as exc:
            data["errors"].append("Bitcoin " + chart + ": " + str(exc))
    _fetch_etf_flows(data)
    return data
