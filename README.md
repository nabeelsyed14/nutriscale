# 🍎 NutriScale v3: IoT Health Intelligence Ecosystem

NutriScale v3 is an **IoT-Powered Smart Meal Tracker** that removes the friction of dietary logging while providing scientifically grounded health intelligence.

---

## 🌟 The Vision
Most calorie-tracking apps are tedious and inaccurate. **NutriScale** solves this by using physical hardware (a scale) and AI Vision to automate the entire process. It ensures accuracy by combining **real-time weight data** with a **trusted local nutritional database**, effectively "grounding" the AI to prevent numerical hallucinations.

---

## 🚀 Key Features (v3)

### 1. Precision Vision-Grounding
*   **Grounded ID:** AI identifies the food, but the **local authority database (8,900+ items)** dictates the nutritional density (Protein/Carbs/Fat/Fiber per 100g).
*   **Precision Math:** Calculates calories and macros using [(Trusted Density) × (Measured Load Cell Weight)]

### 2. Proactive AI Intelligence
*   **Predictive ML:** Built-in Random Forest Regressor that predicts your daily health score trend based on historical intake.
*   **Actionable Insights:** Dynamic "AI Insight" cards on the dashboard provide real-time recommendations (e.g., *"Your sugar intake is dragging your score down—try adding fiber to stabilize."*).

### 3. Metabolic Metric Depth
*   **AMDR Logic:** Automatically calculates Acceptable Macronutrient Distribution Ranges for specialized goals (Weight Loss, Weight Gain, Muscle Build).
*   **Density Metrics:** Tracks Sodium and Fiber per 1000 kcal to prioritize **Dietary Quality** over simple caloric volume.

---

## 🛠️ Technical Stack
*   **Core:** Python 3.11 / Flask / SocketIO
*   **Hardware:** Raspberry Pi 5 + HX711 Load Cell + Pi Camera Module v2
*   **ML Engine:** Scikit-Learn / Joblib (Serialized Random Forest)
*   **Frontend:** "Emerald Glass" Design System (Vanilla CSS/JS, Premium Glassmorphism)
*   **Database:** SQLite (History) + JSON (Nutritional Grounding)

---

## 🔬 Research Suite
The project includes a comprehensive **Academic Research Suite** ([ml/nutriscale_ml_suite.ipynb] documenting:
*   Feature Importance & Metabolic Narratives.
*   Residual & Error Distribution Analysis.
*   Counterfactual "What-If" Simulations for dietary interventions.

---

## 📦 Installation & Setup


### 1. System Requirements
*   **Operating System:** Raspberry Pi OS (64-bit recommended)
*   **Hardware:** Raspberry Pi 5, HX711 Load Cell, Pi Camera Module 3
*   **Local AI Vision:** Ollama (for local LLaVA processing)

### 2. Core Dependencies
      Install **Ollama** to handle local food identification:
      
      # Install Ollama
      curl -fsSL [https://ollama.com/install.sh](https://ollama.com/install.sh) | sh
      
      # Pull the Vision Model (LLaVA)
      ollama pull llava

### 3. Clone the Repo:
      git clone [https://github.com/nabeelsyed14/nutriscale.git](https://github.com/nabeelsyed14/nutriscale.git)
      cd nutriscale
### 4. Run Environment Setup:
      chmod +x setup_pi.sh run_pi.sh
      ./setup_pi.sh
### 5. Launch:
      ./run_pi.sh
