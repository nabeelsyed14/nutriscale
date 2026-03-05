import joblib
import os
import pandas as pd
import numpy as np

# Resolve path to the serialized model
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'health_model.joblib')

class MLEngine:
    def __init__(self):
        self.model = None
        self._load_model()
        
    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                print(f"[ML ENGINE] Model loaded successfully from {MODEL_PATH}")
            except Exception as e:
                print(f"[ML ENGINE] Error loading model: {e}")
        else:
            print(f"[ML ENGINE] Warning: Model file not found at {MODEL_PATH}")

    def predict_score(self, nutrient_data):
        """
        Predicts health score based on nutrient input.
        Input: {'total_calories': X, 'total_protein': X, ...}
        """
        if not self.model:
            return None

        # Prepare features in correct order
        try:
            # Create a localized dataframe for prediction
            input_df = pd.DataFrame([nutrient_data])
            input_df = input_df.fillna(0)
            
            # Feature Engineering: Match training features
            p = input_df['total_protein'].iloc[0]
            c = input_df['total_carbs'].iloc[0]
            f = input_df['total_fat'].iloc[0]
            total_ener = (p * 4) + (c * 4) + (f * 9)
            
            if total_ener > 0:
                input_df['p_pct'] = (p * 4) / total_ener
                input_df['f_pct'] = (f * 9) / total_ener
                input_df['c_pct'] = (c * 4) / total_ener
            else:
                input_df['p_pct'], input_df['f_pct'], input_df['c_pct'] = 0, 0, 0

            # Nutrient Densities (per 1000 kcal)
            cal = input_df['total_calories'].replace(0, 1)
            input_df['fiber_density'] = (input_df['fiber'] * 1000) / cal
            input_df['sugar_density'] = (input_df['sugar'] * 1000) / cal
            input_df['sodium_density'] = (input_df['sodium'] * 1000) / cal

            features = [
                'total_calories', 'total_protein', 'total_carbs', 'total_fat', 
                'sugar', 'fiber', 'sodium', 'p_pct', 'f_pct', 'c_pct',
                'fiber_density', 'sugar_density', 'sodium_density'
            ]
            
            # Reorder columns to match model training and avoid feature name warnings
            input_df = pd.DataFrame(input_df[features], columns=features)
            
            # DIAGNOSTIC LOGGING
            print(f"[ML ENGINE] Features for prediction: {input_df.iloc[0].to_dict()}")
            
            prediction = self.model.predict(input_df)[0]
            # Scale 0-10 prediction to 0-100 to match main dashboard
            scaled_prediction = min(100, max(0, round(float(prediction) * 10, 1)))
            print(f"[ML ENGINE] Raw Prediction: {prediction} -> Scaled: {scaled_prediction}")
            
            return scaled_prediction
        except Exception as e: 
            print(f"[ML ENGINE] Prediction Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_insight(self, totals, predicted_score):
        """
        Generates a proactive insight by comparing current totals to ideal patterns.
        """
        insights = []
        
        # 1. Prediction Message
        base_msg = f"AI Health Forecast: You are trending towards a {predicted_score}/100 Health Score today."
        
        # 2. Logic-based Proactive Suggestions (Detailed & Health-Centric)
    
        # Extract total energy for percentage calculations
        p = totals.get('total_protein', 0)
        c = totals.get('total_carbs', 0)
        f = totals.get('total_fat', 0)
        sugar = totals.get('sugar', 0)
        fiber = totals.get('fiber', 0)
        sodium = totals.get('sodium', 0)
        
        total_ener = (p * 4) + (c * 4) + (f * 9)
        
        if total_ener > 0:
            p_pct = (p * 4) / total_ener
            f_pct = (f * 9) / total_ener
            c_pct = (c * 4) / total_ener
            
            # High Fat (>35% AMDR upper limit)
            if f_pct > 0.35:
                insights.append("Your fat intake has crossed 35% of total energy. While healthy fats are vital, high fat density can lead to excessive calorie intake. Try balancing your next meal with fiber-rich complex carbs.")
                
            # Low Protein (<15% for active recovery)
            if p_pct < 0.15:
                insights.append("Protein is currently below 15% of your energy mix. Protein is essential for muscle tissue repair and maintaining satiety. Consider adding a lean protein source like lentils or Greek yogurt to your next log.")
                
            # High Carbs (>70% AMDR upper limit)
            if c_pct > 0.70:
                insights.append("Carbohydrates are dominating over 70% of your current profile. To avoid energy spikes and 'crashes,' try pairing your carbs with more protein or healthy fats in your upcoming meals.")

        # High Sugar (>50g WHO limit)
        if sugar > 50:
            insights.append("Sugar intake has exceeded the 50g daily threshold. High sugar consumption is a primary driver of insulin resistance and systemic inflammation. Swapping sugary snacks for whole fruits can help stabilize your blood sugar.")
            
        # Low Fiber (<25g goal)
        if fiber < 25:
            insights.append("Fiber is currently below the 25g target. Adequate fiber is crucial for gut microbiome health and efficient digestion. Adding more leafy greens or whole grains would significantly improve your long-term health outlook.")
            
        # High Sodium (>2300mg FDA limit)
        if sodium > 2300:
            insights.append("Sodium levels have surpassed 2,300mg. Excess sodium leads to water retention and puts added strain on your cardiovascular system. Focus on fresh, non-processed ingredients for your next few meals to reset.")

        # Good job message
        if not insights:
            if predicted_score > 80:
                insights.append("Excellent metabolic balance! Your current nutrient distribution is optimal for sustained energy and long-term vitality according to our predictive model.")
            else:
                insights.append("You are maintaining a steady nutritional baseline. For a 'boost' in vitality, aim to increase your fiber intake and keep added sugars minimal.")

        return {
            "predicted_score": predicted_score,
            "message": base_msg,
            "suggestions": insights
        }

# Singleton instance
ml_service = MLEngine()
