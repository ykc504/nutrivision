"""AI Coach.

Default: rule-based (fast, deterministic, no paid APIs).

Optional: local HuggingFace text2text model (free) if transformers is installed.
Set env var USE_HF_COACH=1 to enable.
"""

from __future__ import annotations

import os

from services.llm import answer


_hf_generator = None


def _get_hf_generator():
    global _hf_generator
    if _hf_generator is not None:
        return _hf_generator
    if os.getenv("USE_HF_COACH", "0") != "1":
        return None
    try:
        from transformers import pipeline
        # Small, quick, free
        _hf_generator = pipeline("text2text-generation", model=os.getenv("HF_COACH_MODEL", "google/flan-t5-small"))
        return _hf_generator
    except Exception:
        return None

def generate_coach_response(user_profile, logs, query=""):
    """
    Generate personalized nutrition coaching response.
    
    Args:
        user_profile: User profile dictionary
        logs: Recent food logs
        query: Optional specific question from user
    
    Returns:
        Coach response string
    """
    # If user asks anything, answer via Groq (if configured) or local fallback.
    if query:
        targets = {
            "calories": user_profile.get("calorie_target"),
            "protein_g": user_profile.get("protein_target"),
            "carbs_g": user_profile.get("carb_target"),
            "fat_g": user_profile.get("fat_target"),
        }
        recent = logs[-12:] if logs else []
        prompt = f"""
You are NutriVision AI, a careful nutrition assistant.

User profile:
- Age: {user_profile.get('age')}
- Gender: {user_profile.get('gender')}
- Height_cm: {user_profile.get('height')}
- Weight_kg: {user_profile.get('weight')}
- Conditions: {user_profile.get('conditions')}
- Goal: {user_profile.get('goals')}
- Activity: {user_profile.get('activity_level')}
- Targets: {targets}

Recent logs (optional): {recent}

User question: {query}

Answer in:
1) Recommendation (1 line)
2) Why (2-4 bullets)
3) If relevant: safe max quantity OR avoid
4) Better swaps (1-3 bullets)

Avoid diagnosis. Be specific with numbers (sugar/sodium) when applicable.
"""
        return answer(prompt)

    query_lower = (query or "").lower()
    
    # FAQ responses
    if "lose weight" in query_lower or "weight loss" in query_lower:
        return get_weight_loss_advice(user_profile, logs)
    
    if "muscle" in query_lower or "gain" in query_lower:
        return get_muscle_gain_advice(user_profile, logs)
    
    if "protein" in query_lower:
        return get_protein_advice(user_profile, logs)
    
    if "sugar" in query_lower or "sweet" in query_lower:
        return get_sugar_advice(logs)
    
    if "meal plan" in query_lower or "what should i eat" in query_lower:
        return get_meal_suggestions(user_profile)
    
    if "additive" in query_lower or "processed" in query_lower:
        return get_processing_advice(logs)
    
    if "diabetes" in query_lower:
        return get_diabetes_advice()
    
    if "hypertension" in query_lower or "blood pressure" in query_lower:
        return get_hypertension_advice()
    
    # Default: Generate general weekly summary
    return generate_weekly_summary(user_profile, logs)

def generate_weekly_summary(user_profile, logs):
    """Generate weekly performance summary."""
    if not logs:
        return (
            "You're ready to go.\n\n"
            "• Start by scanning 2–3 packaged foods you eat often.\n"
            "• Log one normal meal today (even manually).\n"
            "• Then ask me: ‘Is this okay for my goal/condition?’ and I’ll tailor advice to you."
        )
    
    messages = []
    
    # Calculate weekly averages
    avg_calories = sum(log.get('calories', 0) for log in logs) / len(logs)
    avg_sugar = sum(log.get('sugar', 0) for log in logs) / len(logs)
    avg_protein = sum(log.get('protein', 0) for log in logs) / len(logs)
    total_additives = sum(log.get('additives_count', 0) for log in logs)
    
    target_calories = user_profile.get('calorie_target', 2000)
    target_protein = user_profile.get('protein_target', 50)
    
    # Calorie assessment
    cal_diff = ((avg_calories - target_calories) / target_calories) * 100
    if abs(cal_diff) < 10:
        messages.append("✅ Your calorie intake is right on target this week!")
    elif cal_diff > 10:
        messages.append(f"⚠️ You're consuming {abs(round(cal_diff))}% more calories than your target. Consider reducing portion sizes.")
    else:
        messages.append(f"⚠️ You're consuming {abs(round(cal_diff))}% fewer calories than your target. Make sure you're eating enough.")
    
    # Sugar assessment
    if avg_sugar > 40:
        messages.append(f"🍬 Your average sugar intake is high ({round(avg_sugar)}g/day). Try replacing sugary snacks with fruits or nuts.")
    elif avg_sugar < 25:
        messages.append("🌟 Excellent job keeping sugar intake low!")
    
    # Protein assessment
    protein_percentage = (avg_protein / target_protein) * 100
    if protein_percentage < 80:
        messages.append(f"🥩 Your protein intake is below target ({round(protein_percentage)}%). Add more lean meats, fish, eggs, or legumes.")
    elif protein_percentage >= 100:
        messages.append("💪 Great protein intake! This supports muscle maintenance and satiety.")
    
    # Processing assessment
    if total_additives > 15:
        messages.append(f"⚠️ You've consumed {total_additives} additives this week. Focus on whole, unprocessed foods when possible.")
    elif total_additives < 5:
        messages.append("🥗 Amazing! You're eating mostly whole foods. Keep it up!")
    
    # Goal-specific advice
    if user_profile.get('goals'):
        goals = user_profile['goals'].lower()
        if 'lose' in goals and cal_diff > 0:
            messages.append("💡 Tip for weight loss: Create a calorie deficit by choosing lower-calorie, high-fiber foods.")
        elif 'gain' in goals and protein_percentage < 100:
            messages.append("💡 Tip for muscle gain: Increase protein intake to support muscle growth.")
    
    return " ".join(messages)

def get_weight_loss_advice(user_profile, logs):
    """Specific advice for weight loss."""
    advice = [
        "🎯 For sustainable weight loss:",
        "",
        "1. Create a 500-calorie deficit (losing 0.5kg per week)",
        "2. Focus on high-protein foods (they keep you full longer)",
        "3. Eat more vegetables and fiber-rich foods",
        "4. Reduce ultra-processed foods and added sugars",
        "5. Stay hydrated with water instead of sugary drinks",
        "",
        "Remember: Slow and steady wins the race!"
    ]
    
    if logs:
        avg_sugar = sum(log.get('sugar', 0) for log in logs) / len(logs)
        if avg_sugar > 30:
            advice.append(f"\n⚠️ Your current sugar intake ({round(avg_sugar)}g/day) may hinder weight loss. Try cutting back on sweets and sodas.")
    
    return "\n".join(advice)

def get_muscle_gain_advice(user_profile, logs):
    """Specific advice for muscle gain."""
    target_protein = user_profile.get('protein_target', 50)
    
    advice = [
        "💪 For effective muscle gain:",
        "",
        f"1. Aim for {target_protein}g+ protein daily",
        "2. Eat in a slight calorie surplus (200-300 calories)",
        "3. Time protein intake around workouts",
        "4. Include complex carbs for energy",
        "5. Don't neglect healthy fats",
        "",
        "Best protein sources: chicken, fish, eggs, Greek yogurt, lentils, tofu"
    ]
    
    if logs:
        avg_protein = sum(log.get('protein', 0) for log in logs) / len(logs)
        if avg_protein < target_protein * 0.8:
            advice.append(f"\n⚠️ You're currently at {round(avg_protein)}g/day. Increase protein by adding a protein-rich snack.")
    
    return "\n".join(advice)

def get_protein_advice(user_profile, logs):
    """Advice about protein intake."""
    target_protein = user_profile.get('protein_target', 50)
    
    return f"""🥩 Protein Guide:

Target: {target_protein}g per day

High-protein foods (per 100g):
• Chicken breast: 31g
• Salmon: 25g
• Greek yogurt: 10g
• Eggs: 13g (per egg: 6g)
• Lentils: 9g
• Tofu: 8g
• Quinoa: 4g

Tip: Spread protein throughout the day for better absorption and sustained energy."""

def get_sugar_advice(logs):
    """Advice about sugar intake."""
    if logs:
        avg_sugar = sum(log.get('sugar', 0) for log in logs) / len(logs)
        status = "high" if avg_sugar > 30 else "good" if avg_sugar < 25 else "moderate"
    else:
        avg_sugar = 0
        status = "unknown"
    
    return f"""🍬 Sugar Management:

Current average: {round(avg_sugar)}g/day ({status})
Recommended: <25g/day (WHO guidelines)

Hidden sugar sources:
• Soft drinks (35g per can)
• Flavored yogurt (15-20g)
• Breakfast cereals (10-15g)
• Sauces and condiments (5-10g)

Healthy swaps:
❌ Soda → ✅ Sparkling water with lemon
❌ Candy → ✅ Fresh fruit
❌ Sweetened yogurt → ✅ Plain yogurt with berries
❌ Juice → ✅ Whole fruits"""

def get_meal_suggestions(user_profile):
    """Generate meal suggestions based on profile."""
    conditions = user_profile.get('conditions', '').lower() if user_profile.get('conditions') else ''
    goals = user_profile.get('goals', '').lower() if user_profile.get('goals') else ''
    
    suggestions = ["🍽️ Personalized Meal Suggestions:\n"]
    
    # Breakfast
    suggestions.append("Breakfast Options:")
    if 'diabetes' in conditions:
        suggestions.append("• Greek yogurt with nuts and berries (low sugar)")
        suggestions.append("• Veggie omelet with whole grain toast")
    else:
        suggestions.append("• Oatmeal with banana and almond butter")
        suggestions.append("• Whole grain toast with avocado and egg")
    
    # Lunch
    suggestions.append("\nLunch Options:")
    if 'lose' in goals:
        suggestions.append("• Large salad with grilled chicken and olive oil")
        suggestions.append("• Vegetable soup with legumes")
    else:
        suggestions.append("• Quinoa bowl with roasted vegetables and tahini")
        suggestions.append("• Whole wheat wrap with turkey and veggies")
    
    # Dinner
    suggestions.append("\nDinner Options:")
    if 'hypertension' in conditions:
        suggestions.append("• Baked salmon with roasted vegetables (low sodium)")
        suggestions.append("• Chicken stir-fry with brown rice")
    else:
        suggestions.append("• Grilled fish with sweet potato and broccoli")
        suggestions.append("• Lentil curry with brown rice")
    
    suggestions.append("\n💡 Remember: Portion control and whole foods are key!")
    
    return "\n".join(suggestions)

def get_processing_advice(logs):
    """Advice about processed foods."""
    if logs:
        total_additives = sum(log.get('additives_count', 0) for log in logs)
    else:
        total_additives = 0
    
    return f"""⚠️ Ultra-Processed Foods Guide:

This week: {total_additives} additives consumed

NOVA Classification:
1️⃣ Unprocessed/Minimally Processed (Best)
   Fresh fruits, vegetables, meat, eggs, milk

2️⃣ Processed Culinary Ingredients (Good)
   Oils, butter, sugar, salt (use in cooking)

3️⃣ Processed Foods (Moderate)
   Canned vegetables, cheese, fresh bread

4️⃣ Ultra-Processed (Limit)
   Soft drinks, chips, instant noodles, packaged snacks

Why avoid ultra-processed:
• High in additives and preservatives
• Often high in sugar, salt, and unhealthy fats
• Linked to obesity and chronic diseases
• Low in essential nutrients

Simple rule: If you can't pronounce the ingredients, reconsider!"""

def get_diabetes_advice():
    """Advice for diabetics."""
    return """🩺 Diabetes Management Tips:

Blood Sugar Control:
• Choose low GI foods (whole grains, legumes)
• Pair carbs with protein/fat to slow absorption
• Limit added sugars and refined carbs
• Eat regular meals to avoid spikes

Foods to Prioritize:
✅ Non-starchy vegetables
✅ Lean proteins
✅ Whole grains (moderate portions)
✅ Nuts and seeds
✅ Healthy fats (avocado, olive oil)

Foods to Limit:
❌ Sugary drinks and desserts
❌ White bread, white rice
❌ Processed snacks
❌ High-sugar fruits (in large amounts)

⚠️ Always consult your healthcare provider for personalized advice!"""

def get_hypertension_advice():
    """Advice for hypertension."""
    return """🩺 Blood Pressure Management:

DASH Diet Principles:
• Reduce sodium to <2,300mg/day
• Increase potassium-rich foods
• Focus on whole grains, fruits, vegetables
• Choose lean proteins
• Limit saturated fats

Sodium Sources to Avoid:
❌ Processed meats (bacon, deli meat)
❌ Canned soups and vegetables
❌ Fast food
❌ Salty snacks
❌ Condiments and sauces

Potassium-Rich Foods (help lower BP):
✅ Bananas, oranges
✅ Potatoes, sweet potatoes
✅ Spinach, beans
✅ Yogurt, fish

⚠️ Always consult your healthcare provider for personalized advice!"""
