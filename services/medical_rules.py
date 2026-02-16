"""Medical condition rules engine for personalized warnings."""

def apply_medical_penalties(product, user_conditions):
    """
    Apply penalties and generate warnings based on user medical conditions.
    
    Args:
        product: Product data dictionary
        user_conditions: Comma-separated string or list of conditions
    
    Returns:
        Tuple of (penalty_score, warnings_list)
    """
    if isinstance(user_conditions, str):
        conditions = [c.strip().lower() for c in user_conditions.split(',') if c.strip()]
    else:
        conditions = [c.lower() for c in user_conditions]
    
    penalty = 0
    warnings = []
    
    # Diabetes rules
    if 'diabetes' in conditions:
        sugar = product.get('sugar', 0)
        if sugar > 15:
            penalty += 25
            warnings.append({
                'severity': 'high',
                'condition': 'Diabetes',
                'message': f'Very high sugar content ({sugar}g/100g) - Not recommended for diabetics'
            })
        elif sugar > 10:
            penalty += 15
            warnings.append({
                'severity': 'medium',
                'condition': 'Diabetes',
                'message': f'High sugar content ({sugar}g/100g) - Use caution if diabetic'
            })
        
        # Check for high glycemic carbs
        if product.get('nova_group', 1) >= 3:
            penalty += 10
            warnings.append({
                'severity': 'medium',
                'condition': 'Diabetes',
                'message': 'Processed foods may cause rapid blood sugar spikes'
            })
    
    # Hypertension rules
    if 'hypertension' in conditions:
        sodium = product.get('sodium', 0)
        if sodium > 500:
            penalty += 25
            warnings.append({
                'severity': 'high',
                'condition': 'Hypertension',
                'message': f'Very high sodium ({sodium}mg/100g) - May increase blood pressure'
            })
        elif sodium > 300:
            penalty += 15
            warnings.append({
                'severity': 'medium',
                'condition': 'Hypertension',
                'message': f'High sodium content ({sodium}mg/100g) - Monitor intake'
            })
    
    # High cholesterol rules
    if 'cholesterol' in conditions or 'high cholesterol' in conditions:
        fat = product.get('fat', 0)
        saturated_fat = product.get('saturated_fat', fat * 0.3)  # Estimate if not available
        
        if saturated_fat > 5:
            penalty += 20
            warnings.append({
                'severity': 'high',
                'condition': 'High Cholesterol',
                'message': f'High saturated fat content - May raise LDL cholesterol'
            })
        
        if fat > 20:
            penalty += 10
            warnings.append({
                'severity': 'medium',
                'condition': 'High Cholesterol',
                'message': 'High total fat content - Monitor portion sizes'
            })
    
    # PCOS rules
    if 'pcos' in conditions:
        sugar = product.get('sugar', 0)
        if sugar > 10:
            penalty += 15
            warnings.append({
                'severity': 'medium',
                'condition': 'PCOS',
                'message': 'High sugar may worsen insulin resistance associated with PCOS'
            })
    
    # Allergen checks
    allergens = product.get('allergens', '')
    if allergens and isinstance(allergens, str):
        allergen_list = [a.strip().lower() for a in allergens.split(',')]
        
        for condition in conditions:
            if any(allergen in condition for allergen in allergen_list):
                penalty += 50
                warnings.append({
                    'severity': 'critical',
                    'condition': 'Allergen Alert',
                    'message': f'Contains potential allergen: {allergens}'
                })
    
    return penalty, warnings

def get_dietary_recommendations(product, user_goals):
    """
    Generate dietary recommendations based on user goals.
    
    Args:
        product: Product data dictionary
        user_goals: Comma-separated string or list of goals
    
    Returns:
        List of recommendation dictionaries
    """
    if isinstance(user_goals, str):
        goals = [g.strip().lower() for g in user_goals.split(',') if g.strip()]
    else:
        goals = [g.lower() for g in user_goals]
    
    recommendations = []
    
    # Weight loss goals
    if 'lose weight' in goals or 'weight loss' in goals:
        calories = product.get('calories', 0)
        if calories > 300:
            recommendations.append({
                'goal': 'Weight Loss',
                'message': f'High calorie density ({calories} kcal/100g) - Consider smaller portions'
            })
        
        if product.get('nova_group', 1) >= 3:
            recommendations.append({
                'goal': 'Weight Loss',
                'message': 'Ultra-processed foods may hinder weight loss goals'
            })
    
    # Muscle gain goals
    if 'gain muscle' in goals or 'muscle gain' in goals:
        protein = product.get('protein', 0)
        if protein < 10:
            recommendations.append({
                'goal': 'Muscle Gain',
                'message': f'Low protein content ({protein}g/100g) - Look for higher protein options'
            })
    
    # Avoid sugar goals
    if 'avoid sugar' in goals or 'reduce sugar' in goals:
        sugar = product.get('sugar', 0)
        if sugar > 5:
            recommendations.append({
                'goal': 'Reduce Sugar',
                'message': f'Contains {sugar}g sugar per 100g - Not aligned with your goal'
            })
    
    # Avoid processed foods
    if 'avoid processed' in goals or 'clean eating' in goals:
        if product.get('nova_group', 1) >= 3:
            recommendations.append({
                'goal': 'Avoid Processed Foods',
                'message': 'This is an ultra-processed food - Consider whole food alternatives'
            })
    
    return recommendations
