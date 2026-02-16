"""Simple WHO-aligned dietary guideline checks.

This is NOT medical advice. It's a practical rule set for feedback:
 - Free sugars: aim <10% of total energy (stronger target 5%).
 - Sodium: WHO suggests <2g sodium/day (~5g salt).

We use these as informative flags.
"""

from __future__ import annotations


def daily_limits() -> dict:
    return {
        "sodium_mg": 2000.0,  # 2g sodium
        "free_sugar_g": None,  # needs calories
    }


def free_sugar_limit_g(calorie_target: float, pct: float = 0.10) -> float:
    # 1g sugar ~ 4 kcal
    return max(0.0, (calorie_target * pct) / 4.0)


def day_guideline_warnings(day_totals: dict, calorie_target: float) -> list[str]:
    warnings: list[str] = []
    sodium_mg = float(day_totals.get("sodium", 0) or 0)
    sugar_g = float(day_totals.get("sugar", 0) or 0)
    cal = float(day_totals.get("calories", 0) or 0)

    sodium_limit = daily_limits()["sodium_mg"]
    if sodium_mg > sodium_limit:
        warnings.append("Sodium is above WHO daily limit (2,000 mg). Consider lower-sodium choices.")

    # Use calorie_target if available; else use consumed calories
    base = calorie_target if calorie_target else max(cal, 1.0)
    sugar_limit_10 = free_sugar_limit_g(base, 0.10)
    if sugar_g > sugar_limit_10:
        warnings.append("Free sugar is likely above WHO <10% energy guidance. Consider less sugary snacks/drinks.")

    return warnings
