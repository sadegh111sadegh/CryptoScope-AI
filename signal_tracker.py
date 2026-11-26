"""Persistent forecast journal with horizon settlement and Brier scoring."""
import json
import os
import tempfile
from datetime import datetime, timezone


DEFAULT_PATH = os.getenv("CRYPTOSCOPE_HISTORY_PATH", "data/forecast_history.json")


def _parse_time(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None


def load_history(path=DEFAULT_PATH):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, list) else []
    except (OSError, ValueError, TypeError):
        return []


def save_history(history, path=DEFAULT_PATH):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="cryptoscope-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(history[-2000:], handle, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def settle_forecasts(history, current_price, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        current_price = float(current_price)
    except (TypeError, ValueError):
        return history
    if current_price <= 0:
        return history
    for item in history:
        if item.get("status") != "pending":
            continue
        created = _parse_time(item.get("created_at"))
        if created is None or (now - created).total_seconds() < int(item.get("horizon_hours", 24)) * 3600:
            continue
        start = item.get("reference_price")
        try:
            change = (current_price / float(start) - 1) * 100
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        outcome = "up" if change > 0.25 else "down" if change < -0.25 else "neutral"
        item.update({"status": "settled", "settled_at": now.isoformat(),
                     "settlement_price": current_price, "realized_change_pct": round(change, 4),
                     "outcome": outcome})
    return history


def record_forecast(history, price, forecast, factor_scores, now=None):
    if not forecast.get("available"):
        return history
    try:
        price = float(price)
    except (TypeError, ValueError):
        return history
    if price <= 0:
        return history
    now = now or datetime.now(timezone.utc)
    created = now.isoformat()
    # Idempotency: do not duplicate the same horizon forecast in the same UTC hour.
    hour_key = now.strftime("%Y-%m-%dT%H")
    if any(x.get("status") == "pending" and x.get("hour_key") == hour_key
           and x.get("horizon_hours") == forecast.get("horizon_hours") for x in history):
        return history
    history.append({
        "created_at": created, "hour_key": hour_key,
        "reference_price": price, "horizon_hours": int(forecast.get("horizon_hours", 24)),
        "probabilities": forecast.get("probabilities", {}),
        "factor_scores": factor_scores, "status": "pending",
        "method": forecast.get("method", "heuristic_v1")
    })
    return history[-2000:]


def performance_summary(history):
    settled = [x for x in history if x.get("status") == "settled" and x.get("outcome")]
    if not settled:
        return {"settled": 0, "pending": sum(x.get("status") == "pending" for x in history),
                "brier_score": None, "directional_accuracy": None}
    briers, correct = [], 0
    for item in settled:
        probs = item.get("probabilities") or {}
        actual = item["outcome"]
        keys = ("up", "down", "neutral")
        try:
            briers.append(sum(((float(probs.get(k, 0)) / 100) - (1.0 if k == actual else 0.0)) ** 2 for k in keys))
        except (TypeError, ValueError):
            continue
        if max(probs, key=lambda k: float(probs.get(k, 0))) == actual:
            correct += 1
    return {"settled": len(settled), "pending": sum(x.get("status") == "pending" for x in history),
            "brier_score": round(sum(briers) / len(briers), 4) if briers else None,
            "directional_accuracy": round(correct / len(settled) * 100, 1) if settled else None}
