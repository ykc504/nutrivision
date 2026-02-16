
"""Disease compatibility scores (0-100).

Heuristic scores based on key nutrients; not medical advice.
"""

def _clamp(x): 
    return max(0, min(100, int(round(x))))

def diabetes_score(product: dict) -> int:
    sugar = float(product.get("sugar") or 0)  # g/100g
    score = 100 - sugar*5
    if int(product.get("nova_group") or 1) >= 3:
        score -= 10
    return _clamp(score)

def hypertension_score(product: dict) -> int:
    sodium = float(product.get("sodium") or 0)  # mg/100g
    score = 100 - sodium*0.12
    return _clamp(score)

def cholesterol_score(product: dict) -> int:
    sat_fat = float(product.get("saturated_fat") or 0)  # g/100g best-effort
    score = 100 - sat_fat*12
    if "palm" in (product.get("ingredients") or "").lower():
        score -= 8
    return _clamp(score)

def scores_for_conditions(product: dict, conditions: str) -> list[dict]:
    conds = [c.strip().lower() for c in (conditions or "").split(",") if c.strip()]
    panels = []
    if "diabetes" in conds:
        s = diabetes_score(product)
        panels.append({"condition":"Diabetes", "score": s, "label": "Avoid" if s<50 else "Caution" if s<70 else "OK"})
    if "hypertension" in conds:
        s = hypertension_score(product)
        panels.append({"condition":"Hypertension", "score": s, "label": "Avoid" if s<50 else "Caution" if s<70 else "OK"})
    if "high cholesterol" in conds or "cholesterol" in conds:
        s = cholesterol_score(product)
        panels.append({"condition":"Cholesterol", "score": s, "label": "Avoid" if s<50 else "Caution" if s<70 else "OK"})
    return panels
