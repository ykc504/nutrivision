"""Daily Risk Exposure Index.

Differentiator metric:
  Sugar Load + Sodium Load + Ultra-processed Exposure + Additive Exposure + Disease Conflict.
"""

from __future__ import annotations

from typing import Any


def _has(cond_str: str, key: str) -> bool:
    return key.lower() in (cond_str or "").lower()


def compute_daily_risk(day_logs: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    sugar = sum(float(l.get("sugar", 0) or 0) for l in day_logs)
    sodium = sum(float(l.get("sodium", 0) or 0) for l in day_logs)
    additives = sum(int(l.get("additives_count", 0) or 0) for l in day_logs)
    nova4 = sum(1 for l in day_logs if int(l.get("nova_group") or 0) == 4)

    conditions = profile.get("conditions", "")
    disease_penalty = 0.0
    if _has(conditions, "diabetes"):
        disease_penalty += sugar * 0.5
    if _has(conditions, "hypertension"):
        disease_penalty += sodium * 0.3
    if _has(conditions, "high_cholesterol"):
        disease_penalty += nova4 * 8

    score = sugar * 0.2 + sodium * 0.1 + nova4 * 10 + additives * 2 + disease_penalty

    if score < 40:
        level = "Low"
        color = "text-emerald-400"
    elif score < 80:
        level = "Moderate"
        color = "text-amber-400"
    else:
        level = "High"
        color = "text-red-400"

    return {
        "score": round(score, 1),
        "level": level,
        "color": color,
        "components": {
            "sugar": round(sugar, 1),
            "sodium": round(sodium, 1),
            "nova4_count": int(nova4),
            "additives_count": int(additives),
            "disease_penalty": round(disease_penalty, 1),
        },
    }
