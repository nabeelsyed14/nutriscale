---


---


*   **Grounded ID:** AI identifies the food, but the **local authority database (8,900+ items)** dictates the nutritional density (Protein/Carbs/Fat/Fiber per 100g).

*   **Predictive ML:** Built-in Random Forest Regressor that predicts your daily health score trend based on historical intake.
*   **Actionable Insights:** Dynamic "AI Insight" cards on the dashboard provide real-time recommendations (e.g., *"Your sugar intake is dragging your score down—try adding fiber to stabilize."*).

### 3. Metabolic Metric Depth
*   **AMDR Logic:** Automatically calculates Acceptable Macronutrient Distribution Ranges for specialized goals (Weight Loss, Weight Gain, Muscle Build).
*   **Density Metrics:** Tracks Sodium and Fiber per 1000 kcal to prioritize **Dietary Quality** over simple caloric volume.

---

## 🛠️ Technical Stack
*   **Core:** Python 3.11 / Flask / SocketIO
*   **ML Engine:** Scikit-Learn / Joblib (Serialized Random Forest)
*   **Frontend:** "Emerald Glass" Design System (Vanilla CSS/JS, Premium Glassmorphism)
*   **Database:** SQLite (History) + JSON (Nutritional Grounding)

---

## 🔬 Research Suite
*   Feature Importance & Metabolic Narratives.
*   Residual & Error Distribution Analysis.
*   Counterfactual "What-If" Simulations for dietary interventions.

---

## 📦 Installation & Setup


# Pull the Vision Model (LLaVA)
ollama pull llava

cd nutriscale
chmod +x setup_pi.sh run_pi.sh
./setup_pi.sh
