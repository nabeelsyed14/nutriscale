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
            
            prediction = self.model.predict(input_df)[0]
            return round(float(prediction), 2)
        except Exception as e:
            print(f"[ML ENGINE] Prediction Error: {e}")
            return None

    def generate_insight(self, totals, predicted_score):
        """
        Generates a proactive insight by comparing current totals to ideal patterns.
        """
        insights = []
        
        # 1. Prediction Message
        base_msg = f"AI Prediction: You are on track for a {predicted_score}/10 Health Score today."
        
        # 2. Logic-based Proactive Suggestions
    
        # Extract total energy for percentage calculations
        # Using Atwater factors: p=4, c=4, f=9
        p = totals.get('total_protein', 0)
        c = totals.get('total_carbs', 0)
        f = totals.get('total_fat', 0)
        total_ener = (p * 4) + (c * 4) + (f * 9)
        
        if total_ener > 0:
            p_pct = (p * 4) / total_ener
            f_pct = (f * 9) / total_ener
            c_pct = (c * 4) / total_ener
            
            # High Fat
            if f_pct > 0.35:
                insights.append("Your fat intake is above 35% of total energy—try choosing leaner protein sources.")
                
            # Low Protein
            if p_pct < 0.15:
                insights.append("Protein intake is below 15%—this may affect muscle recovery and satiety.")
                
            # High Carbs
            if c_pct > 0.70:
                insights.append("Carbs are making up over 70% of your day—consider balancing with more protein.")

        # High Sugar (Legacy but still relevant)
        if totals.get('sugar', 0) > 40:
            insights.append("Your sugar intake is high. This is a primary driver dragging your predicted score down.")
            
        # Low Fiber
        if totals.get('fiber', 0) < 15:
            insights.append("Increasing fiber (e.g., adding vegetables) would boost your predicted score significantly.")
            
        # High Sodium
        if totals.get('sodium', 0) > 2500:
            insights.append("Sodium levels are elevated. Reducing salt in your next meal will help maintain your trend.")

        # Good job message
        if not insights:
            if predicted_score > 8.0:
                insights.append("Excellent balance! Your current nutrient mix is optimal according to the predictive model.")
            else:
                insights.append("You are maintaining a steady baseline. Aim for a balanced macro-mix and more fiber.")

        return {
            "predicted_score": predicted_score,
            "message": base_msg,
            "suggestions": insights
        }

# Singleton instance
ml_service = MLEngine()
