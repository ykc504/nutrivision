# FILE: nutrition-app/services/microplastics.py
def detect_microplastics_risk(product: dict) -> list[str]:
    """
    Heuristic microplastics-related warnings (NOT lab measurement).
    Uses packaging + category cues when available.
    """
    warnings = []

    ingredients = (product.get("ingredients_text") or "").lower()
    categories = (product.get("categories") or "").lower()

    # Ingredient cues (rare in foods; more relevant to non-food but keep generic)
    if "polyethylene" in ingredients or "polypropylene" in ingredients or "microbead" in ingredients:
        warnings.append("Ingredient text suggests polymer-related additives (verify label).")

    # Packaging cues (Open Food Facts sometimes exposes packaging fields; your normalized product currently doesn't store them)
    packaging = (product.get("packaging") or "").lower()
    packaging_materials = (product.get("packaging_materials") or "").lower()

    plastic_terms = ["pet", "plastic", "pp", "hdpe", "ldpe", "pvc"]
    if any(t in packaging for t in plastic_terms) or any(t in packaging_materials for t in plastic_terms):
        warnings.append("Packaged in plastic (PET/PP/HDPE etc.). Some studies suggest possible microplastics exposure from plastic packaging.")

    # Category cue
    if "bottled" in categories or "soft drinks" in categories or "water" in categories:
        warnings.append("Bottled beverages can have higher microplastics exposure risk compared with non-plastic packaging (heuristic flag).")

    return warnings
