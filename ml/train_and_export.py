import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import os

def train_and_export():
    # 1. Load the synthetic 3,000-log dataset
    csv_path = os.path.join('ml', 'user_logs.csv')
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run ml/data_generator.py first.")
        return

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} logs for training...")

    # 2. Feature Engineering: Macro Percentages and Densities
    # We explicitly calculate ratios so the Random Forest learns them better
    df = df.copy()
    total_ener = (df['total_protein'] * 4) + (df['total_carbs'] * 4) + (df['total_fat'] * 9)
    df['p_pct'] = (df['total_protein'] * 4) / total_ener.replace(0, 1)
    df['f_pct'] = (df['total_fat'] * 9) / total_ener.replace(0, 1)
    df['c_pct'] = (df['total_carbs'] * 4) / total_ener.replace(0, 1)
    
    # Nutrient Densities (per 1000 kcal)
    df['fiber_density'] = (df['fiber'] * 1000) / df['total_calories'].replace(0, 1)
    df['sugar_density'] = (df['sugar'] * 1000) / df['total_calories'].replace(0, 1)
    df['sodium_density'] = (df['sodium'] * 1000) / df['total_calories'].replace(0, 1)

    features = [
        'total_calories', 'total_protein', 'total_carbs', 'total_fat', 
        'sugar', 'fiber', 'sodium', 'p_pct', 'f_pct', 'c_pct',
        'fiber_density', 'sugar_density', 'sodium_density'
    ]
    X = df[features]
    y = df['health_score']

    # 3. Train the model
    print("Training Macro-Aware Random Forest Regressor...")
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    # 4. Export the model to the backend services data folder
    export_dir = os.path.join('backend', 'data')
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, 'health_model.joblib')
    
    joblib.dump(model, export_path)
    print(f"Successfully exported model to: {export_path}")

if __name__ == "__main__":
    train_and_export()
