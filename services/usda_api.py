"""USDA FoodData Central (FDC) API integration.

Uses DEMO_KEY by default for exploration and hackathons.
For production, set env var FDC_API_KEY.
"""

from __future__ import annotations

import os
import requests


FDC_BASE = "https://api.nal.usda.gov/fdc/v1"


def _api_key() -> str:
    return os.getenv("FDC_API_KEY", "DEMO_KEY")


def search_food(query: str, page_size: int = 5) -> list[dict]:
    """Search FDC for foods; returns a small list of matches."""
    url = f"{FDC_BASE}/foods/search"
    payload = {
        "query": query,
        "pageSize": page_size,
        "pageNumber": 1,
        "requireAllWords": False,
    }
    r = requests.post(url, params={"api_key": _api_key()}, json=payload, timeout=8)
    r.raise_for_status()
    data = r.json() or {}
    return data.get("foods", []) or []


def get_food(fdc_id: int) -> dict:
    """Fetch full food details."""
    url = f"{FDC_BASE}/food/{fdc_id}"
    r = requests.get(url, params={"api_key": _api_key()}, timeout=8)
    r.raise_for_status()
    return r.json() or {}


def extract_macros(food: dict) -> dict:
    """Extract calories/macros from FDC food details.

    Returns per 100g approximate values when possible.
    """
    nutrients = food.get("foodNutrients", []) or []
    # FDC nutrient IDs vary by data type; fallback to names.
    by_name = {}
    for n in nutrients:
        name = (n.get("nutrient") or {}).get("name") or n.get("nutrientName")
        if not name:
            continue
        by_name[name.lower()] = n

    def val(keys: list[str]) -> float:
        for k in keys:
            n = by_name.get(k)
            if n is None:
                continue
            v = n.get("amount")
            if v is not None:
                try:
                    return float(v)
                except Exception:
                    pass
        return 0.0

    calories = val(["energy", "energy (kcal)"])
    protein = val(["protein"])
    carbs = val(["carbohydrate, by difference", "carbohydrate"])
    fat = val(["total lipid (fat)", "fat"])
    sugar = val(["sugars, total including nlea", "sugars, total"])
    sodium_mg = val(["sodium, na"])  # often mg

    return {
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "sugar": sugar,
        "sodium": sodium_mg,
    }


def fallback_nutrition_for_name(name: str) -> dict | None:
    """Try to find nutrition for a product name via FDC search."""
    foods = search_food(name, page_size=3)
    if not foods:
        return None
    # Prefer branded food results when available
    best = foods[0]
    fdc_id = best.get("fdcId")
    if not fdc_id:
        return None
    detail = get_food(int(fdc_id))
    macros = extract_macros(detail)
    return macros
