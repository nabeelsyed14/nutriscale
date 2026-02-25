# 🍎 NutriScale: IoT Health Intelligence Ecosystem

NutriScale is an **AIoT-Powered Smart Meal Tracker** that removes the friction of dietary logging while providing scientifically grounded health intelligence.

---

## 🌟 Dual Operation Modes

This project is designed to be flexible and can be run in two distinct modes:

### 1. **Standalone Mode (Software-Only)**
*   **Ideal for:** Demonstration, development, and research.
*   **Operation:** Run on any Windows/macOS/Linux machine. Users can manually select foods from the database via the PWA. All ML insights, health scoring, and data visualization features are fully functional.
*   **Requirements:** Any modern computer with Python 3.11+.

### 2. **IoT Mode (Full Sensor Integration)**
*   **Ideal for:** Seamless, physical nutritional tracking.
*   **Operation:** Uses a Raspberry Pi to merge physical weight data with vision-based food identification. The "Grounded Intelligence" loop ensures 100% mathematical accuracy.
*   **Requirements:** Raspberry Pi 5, HX711 Load Cell (5kg), Pi Camera Module 3.

---

## 🚀 Key Features

### 1. Precision Vision-Grounding (IoT Mode)
*   **Grounded ID:** AI identifies the food, but the **local authority database (8,900+ items)** dictates the nutritional density (Protein/Carbs/Fat/Fiber per 100g).
*   **Precision Math:** Calculates calories and macros using `(Trusted Density) × (Measured Load Cell Weight)`.

### 2. Proactive AI Intelligence (All Modes)
*   **Predictive ML:** Built-in Random Forest Regressor that predicts your daily health score trend based on historical intake.
*   **Actionable Insights:** Dynamic "AI Insight" cards on the dashboard provide real-time recommendations (e.g., *"Your sugar intake is dragging your score down—try adding fiber to stabilize."*).

### 3. Metabolic Metric Depth
*   **AMDR Logic:** Automatically calculates Acceptable Macronutrient Distribution Ranges for specialized goals (Weight Loss, Weight Gain, Muscle Build).
*   **Density Metrics:** Tracks Sodium and Fiber per 1000 kcal to prioritize **Dietary Quality** over simple caloric volume.

---

## 🛠️ Technical Stack
*   **Core:** Python 3.11 / Flask / SocketIO
*   **Hardware (Optional):** Raspberry Pi 5 + HX711 Load Cell + Pi Camera Module 3
*   **ML Engine:** Scikit-Learn / Joblib (Serialized Random Forest)
*   **Frontend:** "Emerald Glass" Design System (Vanilla CSS/JS, Premium Glassmorphism)
*   **Database:** SQLite (History) + JSON (Nutritional Grounding)

---

## 🔬 Research Suite
The project includes a comprehensive **Academic Research Suite** (`ml/nutriscale_ml_suite.ipynb`) documenting:
*   Feature Importance & Metabolic Narratives.
*   Residual & Error Distribution Analysis.
*   Counterfactual "What-If" Simulations for dietary interventions.

---

## 📦 Installation & Setup

### 1. Basic Software Setup (All Modes)
Ensure **Ollama** is installed for local food identification:
```bash
# Install Ollama (Linux/macOS)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the Vision Model (LLaVA)
ollama pull llava
```

### 2. Application Setup
```bash
# Clone the Repo
git clone https://github.com/nabeelsyed14/nutriscale.git
cd nutriscale

# Install Dependencies
pip install -r requirements.txt
```

### 3. Launching

#### **On Windows (Standalone Mode):**
Simply run the provided batch file:
```cmd
run_pc.bat
```

#### **On Raspberry Pi (IoT Mode):**
Ensure hardware is connected and run the shell scripts:
```bash
chmod +x setup_pi.sh run_pi.sh
./setup_pi.sh
./run_pi.sh
```

---

## ⚖️ License
MIT License - 2026 NutriScale Project
