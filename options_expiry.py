"""Deribit options-expiry snapshot for BTC and ETH.

Open interest is reported in the option's underlying currency by Deribit.
USD notionals are approximate (OI * underlying price); OI concentration is
not a directional signal by itself.
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import requests

API = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"
TIMEOUT = 15


def _expiry_from_instrument(name):
    # Deribit option names: BTC-27NOV26-60000-C
    try:
        parts = name.split("-")
        return datetime.strptime(parts[1].upper(), "%d%b%y").replace(
            hour=8, minute=0, second=0, tzinfo=timezone.utc
        )
    except (IndexError, ValueError, TypeError):
        return None


def _number(value):
    try:
        result = float(value)
        return result if result >= 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def _asset_snapshot(currency, now, session=requests):
    response = session.get(
        API, params={"currency": currency, "kind": "option"}, timeout=TIMEOUT
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise ValueError(str(payload["error"]))
    rows = (payload.get("result") or [])
    expiries = defaultdict(lambda: {
        "call_oi": 0.0, "put_oi": 0.0, "underlying_price": 0.0,
        "strikes": defaultdict(lambda: {"call": 0.0, "put": 0.0}),
        "volume": 0.0,
    })
    for row in rows:
        name = row.get("instrument_name", "")
        expiry = _expiry_from_instrument(name)
        if not expiry or expiry <= now:
            continue
        parts = name.split("-")
        if len(parts) != 4 or parts[3] not in ("C", "P"):
            continue
        strike = parts[2]
        side = "call" if parts[3] == "C" else "put"
        oi = _number(row.get("open_interest"))
        bucket = expiries[expiry]
        bucket[side + "_oi"] += oi
        bucket["strikes"][strike][side] += oi
        bucket["underlying_price"] = max(
            bucket["underlying_price"], _number(row.get("underlying_price"))
        )
        bucket["volume"] += _number(row.get("volume"))

    result = []
    for expiry, bucket in sorted(expiries.items()):
        call_oi, put_oi = bucket["call_oi"], bucket["put_oi"]
        total = call_oi + put_oi
        if total <= 0:
            continue
        top_strikes = sorted(
            (
                {"strike": strike, "oi": values["call"] + values["put"],
                 "call_oi": values["call"], "put_oi": values["put"]}
                for strike, values in bucket["strikes"].items()
            ),
            key=lambda item: item["oi"], reverse=True
        )[:3]
        result.append({
            "expiry": expiry.isoformat(),
            "expiry_date": expiry.strftime("%Y-%m-%d"),
            "hours_to_expiry": round((expiry - now).total_seconds() / 3600, 1),
            "call_oi": round(call_oi, 4),
            "put_oi": round(put_oi, 4),
            "total_oi": round(total, 4),
            "oi_usd": round(total * bucket["underlying_price"], 2),
            "underlying_price": bucket["underlying_price"],
            "put_call_ratio": round(put_oi / call_oi, 3) if call_oi else None,
            "volume": round(bucket["volume"], 4),
            "top_strikes": top_strikes,
        })
    return result


def get_options_expiry_snapshot(now=None, session=requests):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    assets, errors = {}, []
    for currency in ("BTC", "ETH"):
        try:
            assets[currency] = _asset_snapshot(currency, now, session)
        except Exception as exc:
            assets[currency] = []
            errors.append(f"{currency}: {exc}")

    all_items = [
        (symbol, item)
        for symbol, expiries in assets.items()
        for item in expiries
    ]
    total_oi_usd = sum(item["oi_usd"] for _, item in all_items)
    near_24h = sum(
        item["oi_usd"] for _, item in all_items
        if item["hours_to_expiry"] <= 24
    )
    near_72h = sum(
        item["oi_usd"] for _, item in all_items
        if item["hours_to_expiry"] <= 72
    )
    pct_24h = near_24h / total_oi_usd * 100 if total_oi_usd else 0
    risk = "زیاد" if pct_24h >= 25 else "متوسط" if pct_24h >= 10 else "کم"
    return {
        "available": bool(all_items),
        "source": "Deribit",
        "updated_at": now.isoformat(),
        "assets": assets,
        "total_oi_usd": round(total_oi_usd, 2),
        "oi_expiring_24h_usd": round(near_24h, 2),
        "oi_expiring_72h_usd": round(near_72h, 2),
        "oi_expiring_24h_pct": round(pct_24h, 1),
        "expiry_risk": risk,
        "errors": errors,
    }
