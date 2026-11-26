"""Transparent heuristic scenario probabilities; not a statistically calibrated model."""
from math import exp
from intelligence import number


def _sigmoid(value):
    value = max(-8.0, min(8.0, value))
    return 1.0 / (1.0 + exp(-value))


def forecast_scenarios(score, regime, divergences, coverage, horizon_hours=24):
    if score is None or coverage < 2:
        return {"available": False, "horizon_hours": horizon_hours,
                "reason": "برای برآورد سناریو حداقل دو عامل معتبر لازم است."}
    divergence_adjustment = sum(-1 if item.get("type") == "bearish" else 1 for item in divergences)
    regime_adjustment = 0.35 if regime.get("trend") == "صعودی" else -0.35 if regime.get("trend") == "نزولی" else 0
    latent = max(-3.0, min(3.0, float(score) / 28.0 + regime_adjustment + divergence_adjustment * 0.22))
    up = _sigmoid(latent)
    down = _sigmoid(-latent)
    neutral = max(0.12, 1.0 - abs(up - down))
    total = up + down + neutral
    up_pct = round(up / total * 100, 1)
    down_pct = round(down / total * 100, 1)
    # Make the displayed values sum to exactly 100.0 despite one-decimal rounding.
    probabilities = {"up": up_pct, "down": down_pct,
                     "neutral": round(100.0 - up_pct - down_pct, 1)}
    confidence = "محدود" if coverage < 4 else "متوسط"
    return {
        "available": True, "horizon_hours": horizon_hours,
        "probabilities": probabilities,
        "most_likely": max(probabilities, key=probabilities.get),
        "confidence": confidence,
        "method": "heuristic_v1",
        "calibrated": False,
        "note": "احتمال‌های اولیه مبتنی بر قواعد هستند و تا زمان ارزیابی خارج از نمونه، کالیبره‌شده محسوب نمی‌شوند."
    }
