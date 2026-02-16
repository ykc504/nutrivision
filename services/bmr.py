"""BMR and TDEE calculation service."""

def calculate_bmr(weight, height, age, gender):
    """
    Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation.
    
    Args:
        weight: Weight in kg
        height: Height in cm
        age: Age in years
        gender: 'male' or 'female'
    
    Returns:
        BMR in calories/day
    """
    if gender.lower() == "male":
        return (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        return (10 * weight) + (6.25 * height) - (5 * age) - 161

def calculate_tdee(bmr, activity_level):
    """
    Calculate Total Daily Energy Expenditure.
    
    Args:
        bmr: Basal Metabolic Rate
        activity_level: Activity level string
    
    Returns:
        TDEE in calories/day
    """
    activity_factors = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }
    return bmr * activity_factors.get(activity_level.lower(), 1.2)

def generate_macro_targets(calories, goal):
    """
    Generate macronutrient targets based on calorie goal.
    
    Args:
        calories: TDEE calories
        goal: Goal type ('lose', 'gain', 'maintain')
    
    Returns:
        Tuple of (adjusted_calories, protein_g, carbs_g, fat_g)
    """
    # Adjust calories based on goal
    if goal == "lose":
        calories -= 500  # 500 calorie deficit
    elif goal == "gain":
        calories += 300  # 300 calorie surplus
    
    # Calculate macros (30% protein, 40% carbs, 30% fat)
    protein_g = (calories * 0.30) / 4  # 4 cal/g
    carbs_g = (calories * 0.40) / 4    # 4 cal/g
    fat_g = (calories * 0.30) / 9      # 9 cal/g
    
    return round(calories), round(protein_g), round(carbs_g), round(fat_g)

def calculate_user_targets(age, gender, height, weight, activity_level, goal):
    """
    Calculate complete nutritional targets for a user.
    
    Returns:
        Dictionary with calorie and macro targets
    """
    bmr = calculate_bmr(weight, height, age, gender)
    tdee = calculate_tdee(bmr, activity_level)
    calories, protein, carbs, fat = generate_macro_targets(tdee, goal)
    
    return {
        'bmr': round(bmr),
        'tdee': round(tdee),
        'calorie_target': calories,
        'protein_target': protein,
        'carb_target': carbs,
        'fat_target': fat
    }
