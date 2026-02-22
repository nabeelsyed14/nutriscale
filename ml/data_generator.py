import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

def generate_user_data(num_users=20, days=28):
    users = []
    logs = []
    
    start_date = datetime.now() - timedelta(days=days)
    
    for user_id in range(1, num_users + 1):
        # User PROFILE
        age = random.randint(18, 65)
        gender = random.choice(['male', 'female', 'other'])
        height_cm = random.randint(155, 195)
        initial_weight = random.randint(60, 110)
        activity_level = random.choice(['sedentary', 'light', 'moderate', 'active'])
        
        # Base BMR calculation (Mifflin-St Jeor)
        if gender == 'male':
            bmr = 10 * initial_weight + 6.25 * height_cm - 5 * age + 5
        else:
            bmr = 10 * initial_weight + 6.25 * height_cm - 5 * age - 161
            
        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725
        }
        tdee = bmr * activity_multipliers[activity_level]
        
        current_weight = initial_weight
        
        for day in range(days):
            log_date = start_date + timedelta(days=day)
            
            # Simulate daily intake with some noise
            # Goal is a mix of health-conscious and not
            is_healthy_day = random.random() > 0.3
            
            if is_healthy_day:
                calories = tdee + random.randint(-500, 100) # Slight deficit/maintenance
                protein_pct = random.uniform(0.20, 0.35)
                fat_pct = random.uniform(0.20, 0.30)
                sugar = random.randint(20, 50)
                fiber = random.randint(25, 40)
            else:
                calories = tdee + random.randint(200, 800) # Surplus
                protein_pct = random.uniform(0.10, 0.15)
                fat_pct = random.uniform(0.35, 0.50)
                sugar = random.randint(60, 150)
                fiber = random.randint(5, 15)
            
            carbs_pct = 1.0 - (protein_pct + fat_pct)
            
            protein = (calories * protein_pct) / 4
            fat = (calories * fat_pct) / 9
            carbs = (calories * carbs_pct) / 4
            sodium = random.randint(1500, 5000)
            
            # Macro Percentages
            total_ener = (protein * 4) + (carbs * 4) + (fat * 9)
            if total_ener > 0:
                p_pct = (protein * 4) / total_ener
                f_pct = (fat * 9) / total_ener
                c_pct = (carbs * 4) / total_ener
            else:
                p_pct, f_pct, c_pct = 0, 0, 0

            # Advanced health score logic (0-10)
            score = 9.0  # Base 9
            
            # 1. Macro Imbalances (More aggressive penalties)
            if f_pct > 0.40: score -= 3.0    # Heavy Fat Penalty
            if p_pct < 0.12: score -= 2.5    # Low Protein Penalty
            if c_pct > 0.75: score -= 1.5    # Extreme Carb Penalty
            if c_pct < 0.20: score -= 1.0    # Very Low Carb Penalty (imbalance)
            
            # 2. Refined Sugar & Sodium
            if sugar > 60: score -= 2.0
            if sodium > 4000: score -= 1.0
            
            # 3. Fiber Bonus/Deficit
            if fiber < 15: score -= 2.0
            if fiber > 30: score += 1.0     # High Fiber Reward
            
            # 4. Calorie Surplus Penalty
            if calories > tdee + 400: score -= 2.0
            
            # Clamp and Add subtle noise
            score = max(1.0, min(10.0, score + random.uniform(-0.3, 0.3)))
            
            # Simulate weight change (3500 kcal = 1lb ~= 0.45kg)
            calorie_delta = calories - tdee
            weight_change = (calorie_delta / 7700) # kg
            current_weight += weight_change
            
            logs.append({
                'user_id': user_id,
                'date': log_date.strftime('%Y-%m-%d'),
                'age': age,
                'gender': gender,
                'height_cm': height_cm,
                'activity_level': activity_level,
                'total_calories': round(calories, 1),
                'total_protein': round(protein, 1),
                'total_carbs': round(carbs, 1),
                'total_fat': round(fat, 1),
                'sugar': round(sugar, 1),
                'fiber': round(fiber, 1),
                'sodium': round(sodium, 1),
                'health_score': round(score, 1),
                'weight_kg': round(current_weight, 2)
            })
            
    return pd.DataFrame(logs)

if __name__ == "__main__":
    print("Generating synthesized data...")
    df = generate_user_data(num_users=100, days=30)
    output_path = os.path.join('ml', 'user_logs.csv')
    df.to_csv(output_path, index=False)
    print(f"Succefully generated {len(df)} logs for {df['user_id'].nunique()} users.")
    print(f"Data saved to {output_path}")
