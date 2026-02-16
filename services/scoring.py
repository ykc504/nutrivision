"""Personalized scoring engine for food products."""

from services.medical_rules import apply_medical_penalties
from services.additive_engine import classify_additives, calculate_additive_penalty

def compute_base_score(nutri_score, nova_group):
    """
    Compute base score from Nutri-Score and NOVA classification.
    
    Args:
        nutri_score: Grade A-E
        nova_group: Processing level 1-4
    
    Returns:
        Base score (0-100)
    """
    # Nutri-Score mapping
    nutri_map = {
        'A': 100, 'a': 100,
        'B': 80, 'b': 80,
        'C': 60, 'c': 60,
        'D': 40, 'd': 40,
        'E': 20, 'e': 20
    }
    
    # NOVA group mapping
    nova_map = {
        1: 100,  # Unprocessed
        2: 75,   # Processed culinary ingredients
        3: 50,   # Processed foods
        4: 20    # Ultra-processed
    }
    
    nutrition_score = nutri_map.get(nutri_score, 60)
    processing_score = nova_map.get(nova_group, 50)
    
    # Weighted average: 60% nutrition, 40% processing
    base = (nutrition_score * 0.6) + (processing_score * 0.4)
    
    return round(base)

def compute_personalized_score(product, user_profile):
    """
    Compute personalized score based on user health conditions and goals.
    
    Args:
        product: Product data dictionary
        user_profile: User profile dictionary with conditions and goals
    
    Returns:
        Tuple of (final_score, warnings, recommendations, breakdown)
    """
    # Start with base score
    base_score = compute_base_score(
        product.get('nutri_score', 'C'),
        product.get('nova_group', 3)
    )
    
    penalties = []
    warnings = []
    
    # Apply medical condition penalties
    if user_profile and user_profile.get('conditions'):
        medical_penalty, medical_warnings = apply_medical_penalties(
            product, 
            user_profile['conditions']
        )
        if medical_penalty > 0:
            penalties.append({
                'type': 'Medical Conditions',
                'amount': -medical_penalty,
                'reason': f"Based on your health conditions"
            })
        warnings.extend(medical_warnings)
    
    # Apply additive penalties
    additives_string = product.get('additives', '')
    if additives_string:
        additives_data = classify_additives(additives_string)
        additive_penalty = calculate_additive_penalty(additives_data)
        if additive_penalty > 0:
            penalties.append({
                'type': 'Harmful Additives',
                'amount': -additive_penalty,
                'reason': f"Contains {len(additives_data)} additives"
            })
    
    # Calculate final score
    total_penalty = sum(p['amount'] for p in penalties)
    final_score = max(base_score + total_penalty, 0)
    final_score = min(final_score, 100)
    
    # Score breakdown for transparency
    breakdown = {
        'base_score': base_score,
        'penalties': penalties,
        'final_score': round(final_score)
    }
    
    # Generate overall recommendation
    recommendation = get_overall_recommendation(final_score, warnings)
    
    return round(final_score), warnings, recommendation, breakdown

def get_overall_recommendation(score, warnings):
    """
    Generate overall recommendation based on score and warnings.
    
    Args:
        score: Final product score
        warnings: List of warning dictionaries
    
    Returns:
        Recommendation dictionary
    """
    if score >= 80:
        return {
            'level': 'excellent',
            'emoji': '🌟',
            'title': 'Excellent Choice',
            'message': 'This product is a great choice with high nutritional value and minimal processing.'
        }
    elif score >= 60:
        if len(warnings) == 0:
            return {
                'level': 'good',
                'emoji': '✅',
                'title': 'Good Choice',
                'message': 'This is a decent option. Balanced nutrition with acceptable processing levels.'
            }
        else:
            return {
                'level': 'moderate',
                'emoji': '⚠️',
                'title': 'Moderate Choice',
                'message': 'Acceptable nutritionally, but be aware of the warnings for your health profile.'
            }
    elif score >= 40:
        return {
            'level': 'caution',
            'emoji': '⚠️',
            'title': 'Use Caution',
            'message': 'This product has some concerns. Consider healthier alternatives when possible.'
        }
    else:
        return {
            'level': 'avoid',
            'emoji': '❌',
            'title': 'Not Recommended',
            'message': 'This product is not recommended based on your health profile. Look for better alternatives.'
        }

def get_score_color(score):
    """Get color class for score display."""
    if score >= 80:
        return 'excellent'  # Green
    elif score >= 60:
        return 'good'       # Light green
    elif score >= 40:
        return 'moderate'   # Yellow
    else:
        return 'poor'       # Red

def compare_products(product1, product2, user_profile):
    """
    Compare two products and determine which is better.
    
    Args:
        product1: First product dictionary
        product2: Second product dictionary
        user_profile: User profile dictionary
    
    Returns:
        Comparison result dictionary
    """
    score1, _, _, _ = compute_personalized_score(product1, user_profile)
    score2, _, _, _ = compute_personalized_score(product2, user_profile)
    
    difference = abs(score1 - score2)
    
    if score1 > score2:
        better = product1['name']
        message = f"{better} is better by {difference} points"
    elif score2 > score1:
        better = product2['name']
        message = f"{better} is better by {difference} points"
    else:
        message = "Both products are equally suitable"
    
    return {
        'better_product': better if score1 != score2 else None,
        'score_difference': difference,
        'message': message
    }
