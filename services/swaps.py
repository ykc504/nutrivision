
"""Smart swaps engine (Yuka-style).

Uses Open Food Facts search within the same category string (best-effort),
then ranks candidates by:
- higher personalized score
- better Nutri-Score (A best)
- lower sugar + sodium
"""

from __future__ import annotations
from services.food_api import search_products
from services.scoring import compute_personalized_score

_NUTRI_ORDER = {"A":0, "B":1, "C":2, "D":3, "E":4}

def _pick_category(categories: str) -> str:
    if not categories:
        return ""
    # categories often like "Spreads, Sweet spreads, Hazelnut spreads"
    parts = [p.strip() for p in categories.split(",") if p.strip()]
    return parts[0] if parts else ""

def find_swaps(product: dict, user_profile: dict, *, limit: int = 3) -> list[dict]:
    cat = _pick_category(product.get("categories",""))
    q = cat or (product.get("name","").split(" ")[0] if product.get("name") else "")
    if not q:
        return []

    candidates = search_products(q, page_size=12)
    swaps = []
    for c in candidates:
        if not c.get("barcode") or c.get("barcode") == product.get("barcode"):
            continue
        score, breakdown = compute_personalized_score(c, user_profile)
        swaps.append({
            "barcode": c.get("barcode"),
            "name": c.get("name"),
            "brand": c.get("brand"),
            "image_url": c.get("image_url"),
            "score": int(score),
            "nutri_score": c.get("nutri_score","C"),
            "nova_group": c.get("nova_group",3),
            "sugar": float(c.get("sugar") or 0),
            "sodium": float(c.get("sodium") or 0),
            "why": breakdown.get("verdict","Better choice") if isinstance(breakdown, dict) else "Better choice",
        })

    swaps.sort(key=lambda x: (
        -x["score"],
        _NUTRI_ORDER.get(str(x.get("nutri_score","C")).upper(), 9),
        x["sugar"],
        x["sodium"],
    ))
    return swaps[:limit]
