import os
import json
import base64
import random
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ollama configuration (for local LLaVA model)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Gemini API key (fallback)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Try to import Gemini (optional, may not be installed)
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        print(f"Gemini API Configured with key: {GEMINI_API_KEY[:4]}...{GEMINI_API_KEY[-4:]}")
        GEMINI_AVAILABLE = True
    else:
        print("Gemini API Key missing. Gemini fallback disabled.")
        GEMINI_AVAILABLE = False
except ImportError:
    GEMINI_AVAILABLE = False
    print("google.generativeai not installed. Using Ollama only.")

print(f"Ollama Host configured: {OLLAMA_HOST}")

# Load Nutrition Database
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nutrition_db.json")
try:
    with open(DB_PATH, "r") as f:
        NUTRITION_DB = json.load(f)
except Exception as e:
    print(f"[NUTRITION] Warning: Could not load data/nutrition_db.json: {e}")
    NUTRITION_DB = {}


def get_grounding_data(query):
    """Fuzzy lookup in local database for grounding with word-level checking."""
    if not query: return None
    q_norm = query.lower().strip().replace("_", " ") 
    q_words = set(q_norm.split())
    
    # Priority 1: Exact Key Match
    if q_norm in NUTRITION_DB:
        print(f"[NUTRITION] Perfect Key Match: {q_norm}")
        return NUTRITION_DB[q_norm]

    # Priority 2: Key contained as a whole word in query (e.g. "Apple" in "Red Apple")
    for key, data in NUTRITION_DB.items():
        k_norm = key.replace("_", " ")
        k_words = k_norm.split()
        
        # If any word in the key matches any word in the query perfectly
        if any(kw in q_words for kw in k_words):
             print(f"[NUTRITION] Word-level Match (key): {key} for query: {query}")
             return data
             
        # Priority 3: Alias contained as a whole word
        for alias in data.get("aliases", []):
            a_norm = alias.lower()
            a_words = a_norm.split()
            if any(aw in q_words for aw in a_words):
                print(f"[NUTRITION] Word-level Match (alias): {alias} for query: {query}")
                return data
                
    return None


def calculate_bmr(weight_kg, height_cm, age, gender):
    """Mifflin-St Jeor Equation"""
    if gender == 'male':
        return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        return (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161


def calculate_tdee(bmr, activity_level):
    multipliers = {
        'low': 1.2,
        'moderate': 1.55,
        'high': 1.725
    }
    return int(bmr * multipliers.get(activity_level, 1.2))


def calculate_target_calories(tdee, goal):
    adjustments = {
        'lose': -500,
        'maintain': 0,
        'gain': 500,
        'muscle': 250
    }
    return tdee + adjustments.get(goal, 0)


def calculate_health_score(calories, protein, carbs, fat, user_goal):
    """Simple heuristic health score (0-100)."""
    score = 100
    
    if calories > 1000:
        score -= 20
    elif calories > 800:
        score -= 10
        
    if user_goal == 'lose':
        if calories > 600: score -= 15
        if fat > 30: score -= 10
    elif user_goal == 'muscle':
        if protein < 20: score -= 20
        
    return max(0, min(100, score))


def get_health_emoji(score):
    if score >= 80:
        return "🟢 🥗"
    elif score >= 50:
        return "🟡 🙂"
    else:
        return "🔴 🍟"


def estimate_nutrition_from_image(image_path, weight_g, user_goal="maintain"):
    """
    Server-side Nutrition Authority.
    """
    print(f"\n[NUTRITION] >>> NEW ANALYSIS: {image_path} ({weight_g}g)", flush=True)
    
    # Try AI identification
    raw_est = _identify_and_estimate_density(image_path)
    
    if not raw_est:
        print("[NUTRITION] !! AI IDENTIFICATION TOTALLY FAILED. Using Mock fallback.", flush=True)
        raw_est = _mock_density_estimate()

    food_name = raw_est.get("food_name", "Unknown Food")
    print(f"[NUTRITION] AI identified food: '{food_name}'", flush=True)
    
    # Grounding: Prefer DB values for matched foods
    grounded_density = get_grounding_data(food_name)
    if grounded_density:
        print(f"[NUTRITION] MATCHED DB: Using trusted values for '{food_name}'", flush=True)
        density = grounded_density
    else:
        print(f"[NUTRITION] NO DB MATCH: Using AI's density estimate for '{food_name}'", flush=True)
        density = raw_est

    # CALCULATION AUTHORITY
    ratio = weight_g / 100.0
    result = {
        "food_name": str(food_name).title(),
        "weight_g": weight_g,
        "calories": int(float(density.get("cals", 0)) * ratio),
        "protein_g": round(float(density.get("p", 0)) * ratio, 1),
        "carbs_g": round(float(density.get("c", 0)) * ratio, 1),
        "fat_g": round(float(density.get("f", 0)) * ratio, 1),
        "sugar_g": round(float(density.get("sug", 0)) * ratio, 1),
        "fiber_g": round(float(density.get("fib", 0)) * ratio, 1),
        "sodium_mg": round(float(density.get("na", 0)) * ratio, 1),
        "saturated_fat_g": round(float(density.get("sf", 0)) * ratio, 1),
        "is_ultra_processed": bool(density.get("upf", False))
    }
    
    # Calculate health score
    score_data = calculate_smart_health_score(result, user_goal, weight_g)
    result.update(score_data)
    
    print(f"[NUTRITION] Final Authority Result: {result['food_name']} = {result['calories']} cal", flush=True)
    return result


def _identify_and_estimate_density(image_path):
    """Orchestrate AI pass for density identification."""
    result = _try_ollama_density(image_path)
    if not result and GEMINI_AVAILABLE:
        result = _try_gemini_density(image_path)
    return result


def calculate_smart_health_score(data, user_goal, weight_g):
    """
    Advanced adaptive scoring logic.
    Returns {health_score, health_emoji}
    """
    score = 80  # Base score
    
    # Extract values with defaults
    calories = data.get('calories', 0)
    protein = data.get('protein_g', 0)
    sugar = data.get('sugar_g', 0)
    fiber = data.get('fiber_g', 0)
    sodium = data.get('sodium_mg', 0)
    sat_fat = data.get('saturated_fat_g', 0)
    is_processed = data.get('is_ultra_processed', False)
    
    # 1. Processing Penalty (Heavy)
    if is_processed:
        score -= 25
        
    # 2. Nutrient Density Bonus
    if fiber > 3: score += 5
    if protein > 15: score += 5
    
    # 3. Junk Markers Penalties
    if sugar > 15: score -= 10
    if sodium > 600: score -= 10
    if sat_fat > 10: score -= 10
    
    # 4. Energy Density Penalty (Calories per gram)
    if weight_g > 0:
        density = calories / weight_g
        if density > 4: score -= 15  # Very calorie dense
    
    # 5. Goal Adaptation
    if user_goal == 'lose':
        if calories > 600: score -= 10
        if sugar > 10: score -= 10  # Stricter on sugar
        if density > 3: score -= 10 # Stricter on density
    elif user_goal == 'muscle' or user_goal == 'gain':
        if protein > 20: score += 10 # Reward high protein
        if calories > 800: score += 5 # Reward high energy for gaining
    
    # Clamp and Emoji
    final_score = max(0, min(100, score))
    
    emoji = "🔴 🍟"
    if final_score >= 80: emoji = "🟢 🥗"
    elif final_score >= 50: emoji = "🟡 🙂"
    
    return {"health_score": final_score, "health_emoji": emoji}


def _try_ollama_density(image_path):
    """Identify food and get density PER 100G from Ollama."""
    try:
        print(f"[NUTRITION] Trying Ollama: {OLLAMA_HOST}...", flush=True)
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        prompt = """Analyze food PER 100 GRAMS. Return raw JSON ONLY:
{"food_name": "...", "cals": 0.0, "p": 0.0, "c": 0.0, "f": 0.0, "sug": 0.0, "fib": 0.0, "na": 0.0, "sf": 0.0, "upf": false}
"""
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "llava",
                "prompt": prompt,
                "images": [image_data],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 256}
            },
            timeout=45
        )
        if response.status_code == 200:
            text = response.json().get("response", "").strip()
            print(f"[NUTRITION] Ollama RAW: {text}", flush=True)
            res = _extract_json(text)
            if res: return res
        print(f"[NUTRITION] Ollama failed with status: {response.status_code}", flush=True)
        return None
    except Exception as e:
        print(f"[NUTRITION] Ollama Error: {e}", flush=True)
        return None


def _try_gemini_density(image_path):
    """Identify food and get density PER 100G from Gemini."""
    try:
        print("[NUTRITION] Trying Gemini...", flush=True)
        from PIL import Image
        img = Image.open(image_path)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = """Identify food and nutrients PER 100 GRAMS. 
Return raw JSON ONLY:
{"food_name": "...", "cals": 0, "p": 0, "c": 0, "f": 0, "sug": 0, "fib": 0, "na": 0, "sf": 0, "upf": false}
"""
        response = model.generate_content([prompt, img])
        if response and response.candidates:
            text = response.text.strip()
            print(f"[NUTRITION] Gemini RAW: {text}", flush=True)
            return _extract_json(text)
        return None
    except Exception as e:
        print(f"[NUTRITION] Gemini Error: {e}", flush=True)
        return None


def _extract_json(text):
    """Extract JSON from text that might contain markdown."""
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except:
        pass
    return None


def _mock_density_estimate():
    """Density fallback for mock mode."""
    # Define with proper types to satisfy linter
    mock_densities: dict[str, dict] = {
        "Steamed Veggies": {"cals": 40.0, "p": 2.8, "c": 7.0, "f": 0.4, "fib": 2.6, "sug": 1.7, "na": 33.0, "sf": 0.0, "upf": False},
        "Fast Food Burger": {"cals": 260.0, "p": 13.0, "c": 30.0, "f": 11.0, "fib": 1.1, "sug": 6.0, "na": 480.0, "sf": 3.0, "upf": True},
        "Fresh Apple": {"cals": 52.0, "p": 0.3, "c": 14.0, "f": 0.2, "fib": 2.4, "sug": 10.0, "na": 1.0, "sf": 0.1, "upf": False}
    }
    name, density_raw = random.choice(list(mock_densities.items()))
    density = density_raw.copy()
    density["food_name"] = "Mock " + name
    return density
