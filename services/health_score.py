"""Health score calculation and analytics engine."""

from datetime import datetime, timedelta

def calculate_health_score(logs, targets):
    """
    Calculate overall health score (0-100) based on food logs.
    
    Args:
        logs: List of food log dictionaries
        targets: User's nutritional targets
    
    Returns:
        Health score integer (0-100)
    """
    if not logs:
        return 50  # Neutral score if no data
    
    score = 100
    
    # 1. Calorie adherence (weight: 30%)
    avg_calories = sum(log.get('calories', 0) for log in logs) / len(logs)
    target_calories = targets.get('calorie_target', 2000)
    
    calorie_diff = abs(avg_calories - target_calories) / target_calories
    calorie_penalty = min(calorie_diff * 30, 30)
    score -= calorie_penalty
    
    # 2. Sugar control (weight: 25%)
    avg_sugar = sum(log.get('sugar', 0) for log in logs) / len(logs)
    if avg_sugar > 30:  # More than 30g/day average is concerning
        sugar_penalty = min((avg_sugar - 30) / 2, 25)
        score -= sugar_penalty
    
    # 3. Ultra-processed food intake (weight: 25%)
    total_additives = sum(log.get('additives_count', 0) for log in logs)
    additive_penalty = min(total_additives, 25)
    score -= additive_penalty
    
    # 4. Protein adequacy (weight: 10%)
    avg_protein = sum(log.get('protein', 0) for log in logs) / len(logs)
    target_protein = targets.get('protein_target', 50)
    
    if avg_protein < target_protein * 0.8:  # Less than 80% of target
        protein_penalty = 10
        score -= protein_penalty
    
    # 5. Fiber intake (weight: 10%)
    avg_fiber = sum(log.get('fiber', 0) for log in logs) / len(logs)
    if avg_fiber < 25:  # Recommended daily fiber
        fiber_penalty = min((25 - avg_fiber) / 2.5, 10)
        score -= fiber_penalty
    
    return max(min(round(score), 100), 0)

def get_weekly_stats(logs):
    """
    Calculate weekly statistics from food logs.
    
    Args:
        logs: List of food log dictionaries
    
    Returns:
        Dictionary with weekly stats
    """
    if not logs:
        return {
            'total_calories': 0,
            'avg_calories': 0,
            'total_protein': 0,
            'total_carbs': 0,
            'total_fat': 0,
            'total_sugar': 0,
            'days_logged': 0,
            'meals_logged': 0
        }
    
    return {
        'total_calories': sum(log.get('calories', 0) for log in logs),
        'avg_calories': sum(log.get('calories', 0) for log in logs) / len(logs),
        'total_protein': sum(log.get('protein', 0) for log in logs),
        'total_carbs': sum(log.get('carbs', 0) for log in logs),
        'total_fat': sum(log.get('fat', 0) for log in logs),
        'total_sugar': sum(log.get('sugar', 0) for log in logs),
        'days_logged': len(set(log.get('date') for log in logs if log.get('date'))),
        'meals_logged': len(logs)
    }

def get_macro_distribution(logs):
    """
    Calculate macronutrient distribution percentages.
    
    Args:
        logs: List of food log dictionaries
    
    Returns:
        Dictionary with percentage distribution
    """
    if not logs:
        return {'protein': 0, 'carbs': 0, 'fat': 0}
    
    total_protein = sum(log.get('protein', 0) for log in logs)
    total_carbs = sum(log.get('carbs', 0) for log in logs)
    total_fat = sum(log.get('fat', 0) for log in logs)
    
    # Convert to calories (protein: 4 cal/g, carbs: 4 cal/g, fat: 9 cal/g)
    protein_cal = total_protein * 4
    carbs_cal = total_carbs * 4
    fat_cal = total_fat * 9
    
    total_cal = protein_cal + carbs_cal + fat_cal
    
    if total_cal == 0:
        return {'protein': 0, 'carbs': 0, 'fat': 0}
    
    return {
        'protein': round((protein_cal / total_cal) * 100),
        'carbs': round((carbs_cal / total_cal) * 100),
        'fat': round((fat_cal / total_cal) * 100)
    }

def get_trends(logs):
    """
    Analyze trends in eating patterns.
    
    Args:
        logs: List of food log dictionaries
    
    Returns:
        Dictionary with trend insights
    """
    if len(logs) < 2:
        return {'trends': []}
    
    trends = []
    
    # Sort logs by date
    sorted_logs = sorted(logs, key=lambda x: x.get('date', ''))
    
    # Calculate recent vs older averages
    mid_point = len(sorted_logs) // 2
    recent_logs = sorted_logs[mid_point:]
    older_logs = sorted_logs[:mid_point]
    
    # Calorie trend
    recent_cal = sum(log.get('calories', 0) for log in recent_logs) / len(recent_logs)
    older_cal = sum(log.get('calories', 0) for log in older_logs) / len(older_logs)
    
    cal_change = ((recent_cal - older_cal) / older_cal) * 100 if older_cal > 0 else 0
    
    if abs(cal_change) > 10:
        direction = "increasing" if cal_change > 0 else "decreasing"
        trends.append({
            'metric': 'Calorie Intake',
            'direction': direction,
            'change': abs(round(cal_change)),
            'message': f"Your calorie intake is {direction} by {abs(round(cal_change))}%"
        })
    
    # Sugar trend
    recent_sugar = sum(log.get('sugar', 0) for log in recent_logs) / len(recent_logs)
    older_sugar = sum(log.get('sugar', 0) for log in older_logs) / len(older_logs)
    
    sugar_change = ((recent_sugar - older_sugar) / older_sugar) * 100 if older_sugar > 0 else 0
    
    if abs(sugar_change) > 15:
        direction = "increasing" if sugar_change > 0 else "decreasing"
        trends.append({
            'metric': 'Sugar Intake',
            'direction': direction,
            'change': abs(round(sugar_change)),
            'message': f"Your sugar consumption is {direction} by {abs(round(sugar_change))}%"
        })
    
    return {'trends': trends}

def generate_daily_insight(logs, targets):
    """
    Generate AI-powered daily insight based on food logs.
    
    Args:
        logs: Today's food log dictionaries
        targets: User's nutritional targets
    
    Returns:
        Insight message string
    """
    if not logs:
        return "Start logging your meals to get personalized insights!"
    
    insights = []
    
    # Calculate today's totals
    total_calories = sum(log.get('calories', 0) for log in logs)
    total_sugar = sum(log.get('sugar', 0) for log in logs)
    total_protein = sum(log.get('protein', 0) for log in logs)
    total_additives = sum(log.get('additives_count', 0) for log in logs)
    
    # Calorie insight
    target_calories = targets.get('calorie_target', 2000)
    cal_percentage = (total_calories / target_calories) * 100
    
    if cal_percentage < 50:
        insights.append("You're under your calorie target. Make sure to eat enough to maintain energy.")
    elif cal_percentage > 110:
        insights.append(f"You've exceeded your calorie target by {round(cal_percentage - 100)}%. Consider lighter options for your next meal.")
    else:
        insights.append("Your calorie intake is well-balanced today!")
    
    # Sugar insight
    if total_sugar > 50:
        insights.append(f"High sugar intake detected ({round(total_sugar)}g). Try to reduce sugary foods and beverages.")
    elif total_sugar < 25:
        insights.append("Great job keeping sugar intake low!")
    
    # Protein insight
    target_protein = targets.get('protein_target', 50)
    if total_protein < target_protein * 0.7:
        insights.append(f"Low protein intake today. Consider adding lean meats, fish, eggs, or legumes.")
    elif total_protein >= target_protein:
        insights.append("Excellent protein intake today!")
    
    # Processing insight
    if total_additives > 5:
        insights.append(f"You've consumed {total_additives} additives today. Try choosing more whole foods.")
    elif total_additives == 0:
        insights.append("Amazing! You've eaten only whole, unprocessed foods today.")
    
    return " ".join(insights)
