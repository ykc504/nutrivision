"""Additive analysis and risk classification engine."""

from services.additive_enrich import enrich_additive

# Comprehensive additive database
ADDITIVE_DATABASE = {
    # High risk additives
    "E102": {
        "name": "Tartrazine",
        "category": "Coloring",
        "risk": "high",
        "description": "Yellow synthetic dye",
        "health_concerns": "May cause hyperactivity in children, allergic reactions, asthma",
        "usage": "Soft drinks, candy, desserts"
    },
    "E110": {
        "name": "Sunset Yellow",
        "category": "Coloring",
        "risk": "high",
        "description": "Orange/yellow synthetic dye",
        "health_concerns": "Linked to hyperactivity, allergic reactions",
        "usage": "Orange drinks, candy, ice cream"
    },
    "E129": {
        "name": "Allura Red",
        "category": "Coloring",
        "risk": "high",
        "description": "Red synthetic dye",
        "health_concerns": "May cause hyperactivity, allergic reactions",
        "usage": "Candy, beverages, baked goods"
    },
    "E621": {
        "name": "Monosodium Glutamate (MSG)",
        "category": "Flavor Enhancer",
        "risk": "medium",
        "description": "Flavor enhancer",
        "health_concerns": "May cause headaches, nausea in sensitive individuals",
        "usage": "Savory snacks, soups, processed meats"
    },
    "E250": {
        "name": "Sodium Nitrite",
        "category": "Preservative",
        "risk": "medium",
        "description": "Preservative and color fixative",
        "health_concerns": "Possible link to cancer when consumed in large amounts",
        "usage": "Cured meats, bacon, hot dogs"
    },
    "E251": {
        "name": "Sodium Nitrate",
        "category": "Preservative",
        "risk": "medium",
        "description": "Preservative",
        "health_concerns": "Converts to nitrites, similar concerns as E250",
        "usage": "Cured meats"
    },
    "E320": {
        "name": "BHA (Butylated Hydroxyanisole)",
        "category": "Antioxidant",
        "risk": "high",
        "description": "Synthetic antioxidant",
        "health_concerns": "Possible carcinogen, endocrine disruptor",
        "usage": "Fats, oils, snack foods"
    },
    "E321": {
        "name": "BHT (Butylated Hydroxytoluene)",
        "category": "Antioxidant",
        "risk": "high",
        "description": "Synthetic antioxidant",
        "health_concerns": "Possible carcinogen, liver damage",
        "usage": "Cereals, chewing gum, potato chips"
    },
    
    # Medium risk additives
    "E211": {
        "name": "Sodium Benzoate",
        "category": "Preservative",
        "risk": "medium",
        "description": "Preservative",
        "health_concerns": "May form benzene when combined with vitamin C",
        "usage": "Soft drinks, pickles, sauces"
    },
    "E220": {
        "name": "Sulfur Dioxide",
        "category": "Preservative",
        "risk": "medium",
        "description": "Preservative and antioxidant",
        "health_concerns": "May trigger asthma, allergic reactions",
        "usage": "Dried fruits, wine, processed potatoes"
    },
    "E407": {
        "name": "Carrageenan",
        "category": "Thickener",
        "risk": "medium",
        "description": "Natural thickener from seaweed",
        "health_concerns": "Possible digestive inflammation",
        "usage": "Dairy products, plant-based milks"
    },
    
    # Low risk additives
    "E300": {
        "name": "Ascorbic Acid (Vitamin C)",
        "category": "Antioxidant",
        "risk": "low",
        "description": "Natural antioxidant",
        "health_concerns": "Generally safe, essential nutrient",
        "usage": "Wide variety of foods"
    },
    "E330": {
        "name": "Citric Acid",
        "category": "Acidity Regulator",
        "risk": "low",
        "description": "Natural acid",
        "health_concerns": "Generally safe, naturally occurring",
        "usage": "Beverages, candy, preserves"
    },
    "E440": {
        "name": "Pectin",
        "category": "Thickener",
        "risk": "low",
        "description": "Natural fiber from fruits",
        "health_concerns": "Generally safe, beneficial fiber",
        "usage": "Jams, jellies, yogurt"
    },
    "E322": {
        "name": "Lecithin",
        "category": "Emulsifier",
        "risk": "low",
        "description": "Natural emulsifier",
        "health_concerns": "Generally safe",
        "usage": "Chocolate, baked goods"
    }
}

def classify_additives(additives_string):
    """
    Classify additives and return detailed information.
    
    Args:
        additives_string: Comma-separated string of E-numbers or additive names
    
    Returns:
        List of dictionaries with additive details
    """
    if not additives_string:
        return []
    
    results = []
    additives_list = [a.strip().upper() for a in str(additives_string).split(',')]
    
    for additive in additives_list:
        # Try to find E-number
        if additive in ADDITIVE_DATABASE:
            info = ADDITIVE_DATABASE[additive].copy()
            info['code'] = additive
            # Enrich concerns if missing / generic
            if not info.get('health_concerns') or info.get('health_concerns') == 'Information not available':
                enriched = enrich_additive(additive, name=info.get('name', ''), risk=info.get('risk', 'unknown'))
                info['health_concerns'] = enriched.get('concerns')
                info['sources'] = enriched.get('sources', [])
            results.append(info)
        else:
            # Unknown additive -> optional Tavily/Groq enrichment
            enriched = enrich_additive(additive)
            results.append({
                'code': additive,
                'name': additive,
                'category': 'Unknown',
                'risk': 'unknown',
                'description': 'Additive not in database',
                'health_concerns': enriched.get('concerns', 'Information not available'),
                'sources': enriched.get('sources', []),
                'usage': 'Unknown'
            })
    
    return results

def calculate_additive_penalty(additives_data):
    """
    Calculate penalty score based on additives.
    
    Args:
        additives_data: List of additive dictionaries
    
    Returns:
        Penalty score (0-30)
    """
    penalty = 0
    
    for additive in additives_data:
        risk = additive.get('risk', 'unknown')
        if risk == 'high':
            penalty += 10
        elif risk == 'medium':
            penalty += 5
        elif risk == 'unknown':
            penalty += 2
    
    return min(penalty, 30)  # Cap at 30

def get_additive_summary(additives_data):
    """
    Generate a summary of additive risks.
    
    Args:
        additives_data: List of additive dictionaries
    
    Returns:
        Dictionary with summary statistics
    """
    high_risk = sum(1 for a in additives_data if a.get('risk') == 'high')
    medium_risk = sum(1 for a in additives_data if a.get('risk') == 'medium')
    low_risk = sum(1 for a in additives_data if a.get('risk') == 'low')
    unknown = sum(1 for a in additives_data if a.get('risk') == 'unknown')
    
    return {
        'total_count': len(additives_data),
        'high_risk_count': high_risk,
        'medium_risk_count': medium_risk,
        'low_risk_count': low_risk,
        'unknown_count': unknown,
        'has_concerns': high_risk > 0 or medium_risk > 0
    }

def detect_harmful_chemicals(product):
    """
    Detect other harmful chemicals beyond E-numbers.
    
    Args:
        product: Product dictionary
    
    Returns:
        List of harmful chemical warnings
    """
    warnings = []
    
    # Check for artificial sweeteners
    ingredients = product.get('ingredients_text', '').lower()
    
    sweeteners = ['aspartame', 'sucralose', 'acesulfame', 'saccharin']
    for sweetener in sweeteners:
        if sweetener in ingredients:
            warnings.append({
                'type': 'Artificial Sweetener',
                'name': sweetener.title(),
                'concern': 'May affect gut bacteria and glucose metabolism'
            })
    
    # Check for palm oil
    if 'palm oil' in ingredients or 'palm fat' in ingredients:
        warnings.append({
            'type': 'Palm Oil',
            'name': 'Palm Oil',
            'concern': 'Environmental concerns, high in saturated fat'
        })
    
    # Check for trans fats
    if 'partially hydrogenated' in ingredients:
        warnings.append({
            'type': 'Trans Fat',
            'name': 'Partially Hydrogenated Oil',
            'concern': 'Trans fats increase bad cholesterol and heart disease risk'
        })
    
    # Check for high fructose corn syrup
    if 'high fructose corn syrup' in ingredients or 'glucose-fructose' in ingredients:
        warnings.append({
            'type': 'Sweetener',
            'name': 'High Fructose Corn Syrup',
            'concern': 'Linked to obesity, diabetes, and metabolic syndrome'
        })
    
    return warnings
