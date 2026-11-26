"""Conservative adaptive factor weights from matured, out-of-sample forecasts."""
from collections import defaultdict


def calculate_adaptive_weights(history, minimum_samples=10):
    samples = defaultdict(list)
    for item in history:
        if item.get("status") != "settled" or item.get("outcome") not in ("up", "down"):
            continue
        outcome = 1 if item["outcome"] == "up" else -1
        for name, score in (item.get("factor_scores") or {}).items():
            try:
                value = float(score)
            except (TypeError, ValueError):
                continue
            if value:
                samples[name].append(1.0 if (1 if value > 0 else -1) == outcome else 0.0)
    weights, diagnostics = {}, {}
    for name, results in samples.items():
        n = len(results)
        accuracy = (sum(results) + 5.0) / (n + 10.0)  # Beta(5,5) shrinkage
        raw = 0.5 + accuracy
        weight = max(0.75, min(1.25, raw)) if n >= minimum_samples else 1.0
        weights[name] = round(weight, 3)
        diagnostics[name] = {"samples": n, "directional_accuracy_smoothed": round(accuracy, 3),
                             "active": n >= minimum_samples}
    return {"weights": weights, "diagnostics": diagnostics,
            "minimum_samples": minimum_samples}
