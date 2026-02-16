
"""What-happens-if simulator.

Heuristic 30-day projections for eating a product daily (1 serving/day).

Not medical advice; provides understandable estimates.
"""

from __future__ import annotations
from services.who_guidelines import day_guideline_warnings

def simulate_daily(product: dict, user_profile: dict, *, days: int = 30) -> dict:
    # Best-effort serving size
    serving_g = float(product.get("serving_quantity") or 100)
    factor = serving_g / 100.0

    kcal = float(product.get("calories") or 0) * factor
    sugar_g = float(product.get("sugar") or 0) * factor
    sodium_mg = float(product.get("sodium") or 0) * factor

    total_kcal = kcal * days
    total_sugar = sugar_g * days
    total_sodium = sodium_mg * days

    # Weight change estimate: 7700 kcal ~ 1 kg fat (very rough)
    weight_change_kg = (total_kcal / 7700.0)

    # Disease impact messages
    notes = []
    cond = (user_profile.get("conditions") or "").lower()
    if "diabetes" in cond and sugar_g >= 15:
        notes.append("For diabetes: sugar per serving is high; daily use may worsen glucose control.")
    if "hypertension" in cond and sodium_mg >= 500:
        notes.append("For hypertension: sodium per serving is high; daily use may raise BP risk.")

    warnings = day_guideline_warnings({
        "sugar": sugar_g,
        "sodium": sodium_mg,
        "fiber": float(product.get("fiber") or 0) * factor,
    })

    return {
        "days": days,
        "per_day": {"kcal": round(kcal,1), "sugar_g": round(sugar_g,1), "sodium_mg": round(sodium_mg,0)},
        "totals": {"kcal": round(total_kcal,0), "sugar_g": round(total_sugar,0), "sodium_mg": round(total_sodium,0)},
        "weight_change_kg_est": round(weight_change_kg,2),
        "notes": notes,
        "who_warnings": warnings or [],
    }
