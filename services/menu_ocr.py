"""Restaurant menu OCR + ranking.

Uses pytesseract if available (requires system Tesseract installed).
If OCR fails, returns empty list.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None


def ocr_menu_items(image_bytes: bytes) -> list[str]:
    if not image_bytes:
        return []
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return []

    if pytesseract is None:
        return []

    text = pytesseract.image_to_string(img)
    lines = [l.strip() for l in text.splitlines()]
    # Keep plausible dish lines
    items: list[str] = []
    for l in lines:
        if len(l) < 3:
            continue
        if any(ch.isalpha() for ch in l) and sum(ch.isalpha() for ch in l) >= 3:
            items.append(l)
    # De-dup (preserve order)
    seen = set()
    out = []
    for it in items:
        key = it.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out[:30]


def recommend_menu_items(items: list[str], profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Heuristic ranking (fast) with consumer-friendly color levels + explanations."""

    goal = (profile.get("goals") or "").lower()
    cond = (profile.get("conditions") or "").lower()

    good_kw = ["salad", "grilled", "steam", "steamed", "baked", "soup", "vegetable", "lentil", "dal", "fish", "chicken", "yogurt", "roasted"]
    high_sugar_kw = ["sweet", "sugar", "dessert", "cake", "cola", "juice", "ice cream", "milkshake", "donut"]
    high_sodium_kw = ["salt", "fried", "pickle", "chips", "processed", "sausage", "bacon", "ramen", "noodles", "soy sauce"]
    fried_fast_kw = ["fried", "burger", "fries", "pizza"]

    def evaluate(it: str) -> dict[str, Any]:
        t = it.lower()
        score = 70
        reasons: list[str] = []

        if any(k in t for k in good_kw):
            score += 12
            reasons.append("Likely lighter prep (grilled/steamed/baked).")
        if any(k in t for k in fried_fast_kw):
            score -= 22
            reasons.append("Often calorie-dense / higher saturated fat (fried/fast food).")

        if "diabetes" in cond and any(k in t for k in high_sugar_kw):
            score -= 35
            reasons.append("High sugar risk — not diabetes-friendly.")
        if "hypertension" in cond and any(k in t for k in high_sodium_kw):
            score -= 28
            reasons.append("Likely high sodium — caution for hypertension.")

        if ("lose" in goal) and any(k in t for k in ["fried", "cream", "cheese", "pizza"]):
            score -= 10
            reasons.append("May slow fat-loss due to calories/fats.")

        if ("gain" in goal or "muscle" in goal) and any(k in t for k in ["chicken", "fish", "egg", "paneer", "lentil", "dal"]):
            score += 8
            reasons.append("Likely higher protein." )

        score = max(0, min(100, score))
        if score >= 80:
            level = "good"
            label = "Recommended"
        elif score >= 60:
            level = "caution"
            label = "Caution"
        else:
            level = "avoid"
            label = "Not recommended"

        if not reasons:
            reasons.append("General estimate — sauces/portion size can change the impact.")

        return {"item": it, "score": score, "level": level, "label": label, "reasons": reasons}

    ranked = sorted([evaluate(x) for x in items], key=lambda d: d["score"], reverse=True)
    return ranked[:12]
