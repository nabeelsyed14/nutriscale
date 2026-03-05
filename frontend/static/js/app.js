const API_URL = '/api';

// State
let currentUser = null;
let allUsers = [];
let currentMealAnalysis = null;
let currentCameraSource = 'pi';
let currentWeightSource = 'scale';
let selectedImageFile = null;
let weightChart = null;
let calorieChart = null; // New chart variable

// DOM Elements
const views = {
    onboarding: document.getElementById('view-onboarding'),
    dashboard: document.getElementById('view-dashboard'),
    capture: document.getElementById('view-capture'),
    settings: document.getElementById('view-settings'),
    users: document.getElementById('view-users'),
    meal_details: document.getElementById('view-meal-details'),
    modalReview: document.getElementById('modal-review')
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    init();
    // Register Service Worker for PWA
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(() => console.log("Service Worker Registered"))
            .catch(err => console.error("SW Registration Failed", err));
    }
});

// --- Navigation ---
function showView(viewName) {
    Object.values(views).forEach(el => {
        if (el && el.id !== 'modal-review') el.classList.add('hidden');
    });
    if (views[viewName]) views[viewName].classList.remove('hidden');
    if (viewName === 'dashboard') loadDashboard();
    if (viewName === 'users') showUserProfile(); // Load profile details when showing users view
}

// --- History and Details ---
async function showMealDetails(mealId) {
    showLoader(true, "Loading details...");
    try {
        const res = await fetch(`${API_URL}/meal/${mealId}`);
        const meal = await res.json();

        document.getElementById('details-food-name').innerText = meal.food_name;
        document.getElementById('details-image').src = meal.image_url || '/static/images/logo.png';
        document.getElementById('details-calories').innerText = meal.calories;
        document.getElementById('details-weight').innerText = meal.portion_weight_g;
        document.getElementById('details-protein').innerText = meal.protein_g;
        document.getElementById('details-carbs').innerText = meal.carbs_g;
        document.getElementById('details-fat').innerText = meal.fat_g;

        showView('meal_details');
    } catch (e) {
        console.error("Failed to load meal details", e);
        alert("Error loading meal details");
    } finally {
        showLoader(false);
    }
}

document.getElementById('btn-details-back').addEventListener('click', () => {
    showView('dashboard');
});
// Onboarding logic follows...

// --- Onboarding ---
document.getElementById('setup-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    // type conversion
    data.age = parseInt(data.age);
    data.height = parseFloat(data.height);
    data.weight = parseFloat(data.weight);

    const res = await fetch(`${API_URL}/user/setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (res.ok) {
        const user = await res.json();
        allUsers.push(user);
        showView('dashboard');
    } else {
        const error = await res.json();
        alert(error.error || "Setup failed");
    }
});

// --- User Switching ---
// --- User Switching & Management ---
function renderUserManagement() {
    const list = document.getElementById('user-management-inner');
    if (!list) return;
    list.innerHTML = '';

    allUsers.forEach(u => {
        const el = document.createElement('div');
        el.className = 'glass-panel';
        el.style.display = 'flex';
        el.style.justifyContent = 'space-between';
        el.style.alignItems = 'center';
        el.style.padding = '10px';

        el.innerHTML = `
            <div>
                <strong>${u.name}</strong><br>
                <small>${u.goal}</small>
            </div>
            <div style="display: flex; gap: 5px;">
                <button class="btn-icon-small switch-btn" data-id="${u.id}">🔄</button>
                <button class="btn-icon-small delete-user-btn" data-id="${u.id}" style="color: var(--danger)">🗑️</button>
            </div>
        `;
        list.appendChild(el);
    });

    if (allUsers.length < 3) {
        const addBtn = document.createElement('button');
        addBtn.className = 'btn-primary';
        addBtn.textContent = '+ Create New User';
        addBtn.style.padding = '8px';
        addBtn.onclick = () => showView('onboarding');
        list.appendChild(addBtn);
    }

    // Bind buttons
    list.querySelectorAll('.switch-btn').forEach(btn => {
        btn.onclick = async () => {
            const id = btn.dataset.id;
            const res = await fetch(`${API_URL}/user/switch/${id}`, { method: 'POST' });
            if (res.ok) {
                currentUser = await res.json();
                showView('dashboard');
            }
        };
    });

    list.querySelectorAll('.delete-user-btn').forEach(btn => {
        btn.onclick = async () => {
            if (!confirm("Delete this user and all their data?")) return;
            const id = btn.dataset.id;
            const res = await fetch(`${API_URL}/user/${id}`, { method: 'DELETE' });
            if (res.ok) {
                allUsers = allUsers.filter(u => u.id != id);
                if (allUsers.length === 0) location.reload();
                else renderUserManagement();
            }
        };
    });
}

// Helper: Update macro progress bar
function updateMacroBar(type, consumed, target) {
    const consumedEl = document.getElementById(`${type}-consumed`);
    const targetEl = document.getElementById(`${type}-target`);
    const barEl = document.getElementById(`${type}-bar`);

    if (consumedEl) consumedEl.textContent = Math.round(consumed);
    if (targetEl) targetEl.textContent = Math.round(target);
    if (barEl) {
        const percent = target > 0 ? Math.min((consumed / target) * 100, 100) : 0;
        barEl.style.width = `${percent}%`;
    }
}

// --- Dashboard ---
async function loadDashboard() {
    try {
        const res = await fetch(`${API_URL}/daily`);
        const data = await res.json();

        if (data.error) return;

        // Current User Info
        document.getElementById('current-date').textContent = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });

        // Calorie Budget Logic
        const eaten = data.total_calories || 0;
        const target = data.target_calories || 2000;
        const remaining = data.remaining_calories || 0;
        const isOver = data.is_over_budget || (eaten > target);

        document.getElementById('cal-eaten').textContent = eaten;
        document.getElementById('cal-target').textContent = target;

        const remainingValEl = document.getElementById('cal-remaining');
        const remainingLabelEl = remainingValEl.nextElementSibling; // The <small> element

        if (isOver) {
            remainingValEl.textContent = Math.abs(remaining);
            if (remainingLabelEl) remainingLabelEl.textContent = 'Over';
            remainingValEl.style.color = 'var(--danger)';
        } else {
            remainingValEl.textContent = remaining;
            if (remainingLabelEl) remainingLabelEl.textContent = 'Left';
            remainingValEl.style.color = 'white';
        }

        // Progress Ring
        const circle = document.getElementById('ring-progress');
        if (circle) {
            const circumference = circle.r.baseVal.value * 2 * Math.PI;
            circle.style.strokeDasharray = `${circumference} ${circumference}`;
            const percent = Math.min(data.total_calories / (data.target_calories || 2000), 1);
            circle.style.strokeDashoffset = circumference - (percent * circumference);
        }

        // Macronutrient Progress
        updateMacroBar('protein', data.total_protein || 0, data.protein_target || 0);
        updateMacroBar('carbs', data.total_carbs || 0, data.carbs_target || 0);
        updateMacroBar('fat', data.total_fat || 0, data.fat_target || 0);

        // Meal List
        const mealList = document.getElementById('meal-list');
        if (data.meals.length === 0) {
            mealList.innerHTML = '<div class="empty-state">No meals logged today</div>';
        } else {
            mealList.innerHTML = data.meals.map(meal => `
                <div class="meal-item ripple" onclick="showMealDetails(${meal.id})">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 1.5rem;">${meal.health_emoji || '⚪'}</span>
                        <div class="meal-info">
                            <h4>${meal.food_name}</h4>
                            <p class="meal-meta">${meal.calories} kcal • ${meal.portion_weight_g}g</p>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span class="score-badge">${meal.health_score || 0}</span>
                        <button class="btn-icon-small btn-delete" data-id="${meal.id}" onclick="event.stopPropagation();">
                             <span class="material-symbols-rounded" style="font-size: 18px; color: var(--danger);">delete</span>
                        </button>
                    </div>
                </div>
            `).join('');
        }

        document.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation(); // Stop propagation to the parent 'meal-item'
                if (confirm("Delete meal?")) {
                    await fetch(`${API_URL}/meal/${btn.dataset.id}`, { method: 'DELETE' });
                    loadDashboard();
                }
            });
        });

        // Populate Micronutrients
        const micros = {
            sugar: data.total_sugar,
            fiber: data.total_fiber,
            sodium: data.total_sodium
        };
        console.log("[DEBUG] Dashboard Micros Received:", micros);

        const updateMicro = (id, val, unit) => {
            const el = document.getElementById(id);
            if (el) {
                // Ensure we have a valid number
                const num = parseFloat(val) || 0;
                // If value is rounded-to-zero but exists, show at least 0.1
                el.textContent = (num === 0 && val > 0) ? '0.1' : (id === 'dash-sodium' ? Math.round(num) : num.toFixed(1));
                console.log(`[UI] Updated ${id} with ${val} -> ${el.textContent}${unit}`);
            }
        };

        updateMicro('dash-sugar', micros.sugar, 'g');
        updateMicro('dash-fiber', micros.fiber, 'g');
        updateMicro('dash-sodium', micros.sodium, 'mg');

        // Weekly Stats & Graph
        loadWeeklyStats();

        // AI ML Insights
        loadMLInsights();
    } catch (e) {
        console.error("Dashboard failed", e);
    }
}

async function loadMLInsights() {
    const card = document.getElementById('ai-insight-card');
    const textEl = document.getElementById('ml-prediction-text');
    const listEl = document.getElementById('ml-suggestions-list');

    if (!card || !textEl || !listEl) return;

    try {
        const res = await fetch(`${API_URL}/ml/insight`);
        if (res.status === 202) {
            card.classList.add('hidden');
            return;
        }

        const data = await res.json();
        console.log("[ML] Received Insight Data:", data);

        if (data.predicted_score !== undefined && data.predicted_score !== null) {
            card.classList.remove('hidden');
            textEl.innerHTML = `Predicted Daily Health Score: <span style="font-size: 1.2rem; color: var(--primary);">${data.predicted_score}</span> / 100`;

            listEl.innerHTML = (data.suggestions || []).map(s => `<li>${s}</li>`).join('');
        } else {
            console.warn("[ML] No predicted score in response data");
            card.classList.add('hidden');
        }
    } catch (e) {
        console.error("ML Insight load failed", e);
        card.classList.add('hidden');
    }
}

async function loadWeeklyStats() {
    try {
        const res = await fetch(`${API_URL}/weekly`);
        const data = await res.json();

        const sectionWeekly = document.getElementById('section-weekly');
        if (sectionWeekly) {
            sectionWeekly.classList.remove('hidden');
            renderCalorieChart(data.daily_logs);
        }
    } catch (e) {
        console.error("Weekly stats failed", e);
    }
}

function renderCalorieChart(logs) {
    const ctx = document.getElementById('calorie-chart');
    if (!ctx) return;

    if (calorieChart) calorieChart.destroy();

    // Prepare labels for last 7 days
    const labels = [];
    const caloriesData = [];
    const targetsData = [];

    const today = new Date();
    for (let i = 6; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const dateStr = d.toISOString().split('T')[0];
        labels.push(d.toLocaleDateString(undefined, { weekday: 'short' }));

        const log = logs.find(l => l.date === dateStr);
        caloriesData.push(log ? log.total_calories : 0);

        // GOAL UNIFICATION: Prefer data from backend daily stats if current, otherwise fallback
        let target = (currentUser ? currentUser.target_calories : 2000);
        if (log && log.current_target_calories) {
            target = log.current_target_calories;
        }
        targetsData.push(target);
    }

    const currentTarget = targetsData[targetsData.length - 1]; // Use today's target
    const goal = (currentUser ? currentUser.goal : 'maintain').toLowerCase();

    calorieChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Consumed',
                data: caloriesData,
                backgroundColor: caloriesData.map((val, idx) => {
                    if (val === 0) return 'rgba(0,0,0,0.05)';
                    const target = targetsData[idx];
                    const margin = 200;

                    // Within passable blue zone
                    if (Math.abs(val - target) <= margin) return '#2196F3'; // Blue

                    if (goal === 'lose') {
                        return val < target - margin ? '#00C853' : '#FF5252';
                    } else if (goal === 'muscle' || goal === 'gain') {
                        return val > target + margin ? '#00C853' : '#FF5252';
                    } else {
                        // Maintain
                        return '#FF5252'; // Outside 200 margin is red for maintain
                    }
                }),
                borderRadius: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => `Consumed: ${context.raw} kcal (Goal: ${targetsData[context.dataIndex]})`
                    }
                }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    beginAtZero: true,
                    min: 0,
                    max: currentTarget + 800, // Fixed max to always show all zones
                    grid: { color: 'rgba(0,0,0,0.05)' }
                }
            }
        },
        plugins: [{
            id: 'goalLine',
            beforeDraw: (chart) => {
                const { ctx, chartArea: { left, right, top, bottom }, scales: { y } } = chart;
                const yVal = y.getPixelForValue(currentTarget);
                ctx.save();
                ctx.strokeStyle = 'rgba(0, 0, 0, 0.2)';
                ctx.setLineDash([5, 5]);
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(left, yVal);
                ctx.lineTo(right, yVal);
                ctx.stroke();
                ctx.restore();
            }
        }, {
            id: 'zones',
            beforeDraw: (chart) => {
                const { ctx, chartArea: { left, right, top, bottom }, scales: { y } } = chart;
                const target = currentTarget;
                const margin = 200;

                // Passable Zone (Blue)
                ctx.save();
                ctx.fillStyle = 'rgba(33, 150, 243, 0.1)';
                const passTop = y.getPixelForValue(target + margin);
                const passBottom = y.getPixelForValue(target - margin);
                ctx.fillRect(left, passTop, right - left, passBottom - passTop);

                // Over Zone (Light Red)
                ctx.fillStyle = 'rgba(255, 82, 82, 0.05)';
                ctx.fillRect(left, top, right - left, Math.max(0, passTop - top));

                // Goal/Under Zone (Light Green)
                ctx.fillStyle = 'rgba(0, 200, 83, 0.05)';
                ctx.fillRect(left, passBottom, right - left, Math.max(0, bottom - passBottom));

                ctx.restore();
            }
        }]
    });
}

function renderWeightGraph(history) {
    const ctx = document.getElementById('weight-chart');
    if (!ctx) return;

    if (weightChart) weightChart.destroy();

    const labels = history.map(p => new Date(p.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
    const weights = history.map(p => p.weight_kg);

    weightChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Weight (kg)',
                data: weights,
                borderColor: '#00C853',
                backgroundColor: 'rgba(0, 200, 83, 0.1)',
                fill: true,
                tension: 0.3,
                pointBackgroundColor: '#00C853',
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: {
                    beginAtZero: false,
                    grid: { color: 'rgba(0,0,0,0.05)' }
                }
            }
        }
    });
}

// --- Profile Details ---
async function showUserProfile() {
    if (!currentUser) return;

    const details = document.getElementById('user-profile-details');
    const manageTitle = document.getElementById('manage-accounts-title');

    if (details) details.classList.remove('hidden');
    if (manageTitle) manageTitle.style.marginTop = "30px";

    // Set Name and Initials
    document.getElementById('profile-name').textContent = currentUser.name;
    document.getElementById('profile-initials').textContent = currentUser.name.split(' ').map(n => n[0]).join('').toUpperCase();
    document.getElementById('profile-goal').textContent = `Goal: ${currentUser.goal.replace('-', ' ')}`;
    document.getElementById('profile-current-weight').textContent = currentUser.weight_kg;

    try {
        const res = await fetch(`${API_URL}/weekly`);
        const data = await res.json();

        document.getElementById('profile-avg-score').textContent = data.weekly_avg_score || 0;
        renderWeightGraph(data.weight_history);
    } catch (e) {
        console.error("Failed to load profile stats", e);
    }
}

document.getElementById('btn-add-meal').addEventListener('click', () => {
    showView('capture');
    selectedImageFile = null;
    document.getElementById('client-image-input').value = '';
    if (currentWeightSource === 'scale') {
        startWeightPolling();
    }
});

// --- Hardware Toggles ---
document.getElementById('toggle-camera-pi').addEventListener('click', () => {
    currentCameraSource = 'pi';
    selectedImageFile = null;
    document.getElementById('toggle-camera-pi').classList.add('active');
    document.getElementById('toggle-camera-client').classList.remove('active');
    document.getElementById('pi-camera-feed').src = '/api/video_feed';
    document.getElementById('pi-camera-feed').style.display = 'block';
    document.getElementById('cam-placeholder').style.display = 'none';
});

document.getElementById('toggle-camera-client').addEventListener('click', () => {
    document.getElementById('client-image-input').click();
});

document.getElementById('client-image-input').addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
        currentCameraSource = 'client';
        selectedImageFile = e.target.files[0];
        document.getElementById('toggle-camera-client').classList.add('active');
        document.getElementById('toggle-camera-pi').classList.remove('active');

        // Show preview in the same camera-preview area
        const reader = new FileReader();
        reader.onload = (re) => {
            const img = document.getElementById('pi-camera-feed');
            img.src = re.target.result;
            img.style.display = 'block';
            document.getElementById('cam-placeholder').style.display = 'none';
        };
        reader.readAsDataURL(selectedImageFile);
    }
});

document.getElementById('toggle-weight-scale').addEventListener('click', () => {
    currentWeightSource = 'scale';
    document.getElementById('toggle-weight-scale').classList.add('active');
    document.getElementById('toggle-weight-manual').classList.remove('active');
    document.getElementById('readout-weight').disabled = true;
    startWeightPolling();
});

document.getElementById('toggle-weight-manual').addEventListener('click', () => {
    currentWeightSource = 'manual';
    document.getElementById('toggle-weight-manual').classList.add('active');
    document.getElementById('toggle-weight-scale').classList.remove('active');
    document.getElementById('readout-weight').disabled = false;
    stopWeightPolling();
});

// --- Capture & Analysis ---
let weightInterval;

function startWeightPolling() {
    clearInterval(weightInterval);
    weightInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API_URL}/sensor/weight`);
            const data = await res.json();
            document.getElementById('readout-weight').value = data.weight_g;
        } catch (e) {
            console.log("Weight poll error", e);
        }
    }, 1000);
}

function stopWeightPolling() {
    clearInterval(weightInterval);
}

document.getElementById('btn-refresh-weight').addEventListener('click', async () => {
    try {
        const res = await fetch(`${API_URL}/sensor/weight`);
        const data = await res.json();
        document.getElementById('readout-weight').value = data.weight;
    } catch (e) {
        console.error("Weight refresh failed", e);
    }
});

document.getElementById('btn-tare-scale').addEventListener('click', async () => {
    showLoader(true, "Zeroing Scale...");
    try {
        const res = await fetch(`${API_URL}/sensor/tare`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert("Scale Zeroed");
            document.getElementById('readout-weight').value = "0.0";
        }
    } catch (e) {
        console.error("Tare failed", e);
    } finally {
        showLoader(false);
    }
});

document.getElementById('btn-back').addEventListener('click', () => {
    stopWeightPolling();
    selectedImageFile = null;
    document.getElementById('client-image-input').value = '';
    showView('dashboard');
});

// --- Loader Helper ---
function showLoader(show, text = "Loading...") {
    const el = document.getElementById('loader');
    if (el) {
        document.getElementById('loader-text').textContent = text;
        if (show) el.classList.remove('hidden');
        else el.classList.add('hidden');
    }
}

document.getElementById('btn-analyze').addEventListener('click', async () => {
    const weight = parseFloat(document.getElementById('readout-weight').value);

    console.log('[DEBUG] Analyze clicked');
    console.log('[DEBUG] currentCameraSource:', currentCameraSource);
    console.log('[DEBUG] selectedImageFile:', selectedImageFile);
    console.log('[DEBUG] weight:', weight);

    if (currentCameraSource === 'client' && !selectedImageFile) {
        alert('Please select an image first by clicking the "Phone" button.');
        return;
    }

    if (!weight || weight <= 0) {
        alert('Please enter a valid weight (greater than 0).');
        return;
    }

    showLoader(true, "NutriScale Intelligent Analysis...");

    try {
        const formData = new FormData();
        formData.append('weight_g', weight);
        formData.append('image_source', currentCameraSource);

        if (currentCameraSource === 'client' && selectedImageFile) {
            formData.append('image_file', selectedImageFile);
            console.log('[DEBUG] Appending image file to FormData');
        }

        console.log('[DEBUG] Sending request to /api/analyze-image');
        const res = await fetch(`${API_URL}/analyze-image`, {
            method: 'POST',
            body: formData
        });
        console.log('[DEBUG] Response status:', res.status);

        const data = await res.json();
        console.log('[DEBUG] Response data:', data);

        if (data.error) {
            alert(data.error);
            return;
        }

        currentMealAnalysis = data;

        // Show results
        document.getElementById('res-food-name').textContent = data.food_name;
        document.getElementById('res-cal').textContent = data.calories;
        document.getElementById('res-p').textContent = data.protein_g;
        document.getElementById('res-c').textContent = data.carbs_g;
        document.getElementById('res-f').textContent = data.fat_g;

        // Show micros
        document.getElementById('res-sugar').textContent = `${data.sugar_g || 0}g`;
        document.getElementById('res-fiber').textContent = `${data.fiber_g || 0}g`;
        document.getElementById('res-sodium').textContent = `${data.sodium_mg || 0}mg`;

        document.getElementById('res-emoji').textContent = data.health_emoji;
        document.getElementById('res-score').textContent = data.health_score;

        document.getElementById('analysis-result').classList.remove('hidden');
        document.getElementById('btn-analyze').classList.add('hidden');
    } catch (e) {
        alert("Analysis failed. Please check connection.");
        console.error(e);
    } finally {
        showLoader(false);
    }
});

document.getElementById('btn-save-meal').addEventListener('click', async () => {
    if (!currentMealAnalysis) return;

    const res = await fetch(`${API_URL}/meal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            food_name: currentMealAnalysis.food_name,
            portion_weight_g: currentMealAnalysis.weight_g,
            calories: currentMealAnalysis.calories,
            protein_g: currentMealAnalysis.protein_g,
            carbs_g: currentMealAnalysis.carbs_g,
            fat_g: currentMealAnalysis.fat_g,
            sugar_g: currentMealAnalysis.sugar_g,
            fiber_g: currentMealAnalysis.fiber_g,
            sodium_mg: currentMealAnalysis.sodium_mg,
            saturated_fat_g: currentMealAnalysis.saturated_fat_g,
            is_ultra_processed: currentMealAnalysis.is_ultra_processed,
            health_score: currentMealAnalysis.health_score,
            health_emoji: currentMealAnalysis.health_emoji,
            image_path: currentMealAnalysis.image_url
        })
    });

    if (res.ok) {
        stopWeightPolling();
        await loadDashboard(); // Force immediate refresh
        showMealReview(currentMealAnalysis);
        // Reset UI
        document.getElementById('analysis-result').classList.add('hidden');
        document.getElementById('btn-analyze').classList.remove('hidden');
        selectedImageFile = null;
    } else {
        alert("Failed to save meal");
    }
});

function showMealReview(data) {
    const content = document.getElementById('review-content');
    content.innerHTML = `
        <div style="text-align: center; margin-bottom: 25px;">
            <div style="font-size: 5rem; margin-bottom: 10px;">${data.health_emoji}</div>
            <h1 style="margin: 0; font-size: 2.2rem;">${data.food_name}</h1>
            <p style="opacity: 0.7; font-size: 1.1rem; font-weight: 600;">Intelligence Score: ${data.health_score}/100</p>
        </div>
        
        <div class="glass-panel" style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 24px;">
            <div class="nutrition-grid" style="grid-template-columns: repeat(2, 1fr); gap: 15px;">
                <div class="nutri-item" style="text-align: center; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 12px;">
                    <small style="display: block; opacity: 0.6; font-size: 0.7rem; text-transform: uppercase;">Calories</small>
                    <strong style="font-size: 1.2rem;">${data.calories}</strong>
                </div>
                <div class="nutri-item" style="text-align: center; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 12px;">
                    <small style="display: block; opacity: 0.6; font-size: 0.7rem; text-transform: uppercase;">Protein</small>
                    <strong style="font-size: 1.2rem;">${data.protein_g}g</strong>
                </div>
                <div class="nutri-item" style="text-align: center; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 12px;">
                    <small style="display: block; opacity: 0.6; font-size: 0.7rem; text-transform: uppercase;">Carbs</small>
                    <strong style="font-size: 1.2rem;">${data.carbs_g}g</strong>
                </div>
                <div class="nutri-item" style="text-align: center; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 12px;">
                    <small style="display: block; opacity: 0.6; font-size: 0.7rem; text-transform: uppercase;">Fat</small>
                    <strong style="font-size: 1.2rem;">${data.fat_g}g</strong>
                </div>
            </div>
            
            <hr style="border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 20px 0;">
            
            <div style="display: flex; justify-content: space-between; font-size: 0.9rem; opacity: 0.8;">
                <span>Sugar / Fiber</span>
                <span>${data.sugar_g}g / ${data.fiber_g}g</span>
            </div>
        </div>
        
        ${data.is_ultra_processed ? `
            <div style="margin-top: 20px; padding: 12px; background: rgba(255, 82, 82, 0.15); border-radius: 12px; border: 1px solid rgba(255, 82, 82, 0.3); color: #ffab91; font-size: 0.85rem; text-align: center;">
                ⚠️ Ultra-processed food detected.
            </div>
        ` : ''}
    `;
    views.modalReview.classList.remove('hidden');
}

document.getElementById('btn-close-review').onclick = () => {
    views.modalReview.classList.add('hidden');
    showView('dashboard');
};


// --- Settings and Profiles ---
document.getElementById('btn-show-settings').addEventListener('click', () => {
    if (currentUser) {
        document.getElementById('set-weight').value = currentUser.weight_kg;
        document.getElementById('set-height').value = currentUser.height_cm;
    }
    showView('settings');
});

document.getElementById('btn-show-users').addEventListener('click', () => {
    renderUserManagement(); // Keep this if it's intended to render the user list
    showView('users');
});

document.getElementById('btn-back-users').onclick = () => showView('dashboard');

document.getElementById('btn-back-settings').addEventListener('click', () => {
    showView('dashboard');
});

document.getElementById('update-profile-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
        weight: parseFloat(document.getElementById('set-weight').value),
        height: parseFloat(document.getElementById('set-height').value)
    };

    const res = await fetch(`${API_URL}/user/update`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    if (res.ok) {
        currentUser = await res.json();
        alert("Stats updated!");
    }
});

document.getElementById('btn-back-settings').addEventListener('click', () => {
    showView('dashboard');
});

document.getElementById('btn-reset-data').addEventListener('click', async () => {
    if (!confirm("Are you sure? This will delete ALL data including your profile.")) return;

    showLoader(true, "Resetting...");
    try {
        const res = await fetch(`${API_URL}/user/reset`, { method: 'DELETE' });
        if (res.ok) {
            alert("Data cleared. Restarting...");
            location.reload();
        } else {
            alert("Reset failed");
        }
    } catch (e) {
        alert("Error resetting data");
    } finally {
        showLoader(false);
    }
});

async function init() {
    showLoader(true, "Loading...");
    try {
        // Micro Toggle Event
        const btnToggleMicro = document.getElementById('btn-micro-toggle');
        const microContainer = document.getElementById('micro-container');
        if (btnToggleMicro && microContainer) {
            btnToggleMicro.onclick = () => {
                microContainer.classList.toggle('collapsed');
                const icon = btnToggleMicro.querySelector('.material-symbols-rounded');
                icon.textContent = microContainer.classList.contains('collapsed') ? 'expand_more' : 'expand_less';
            };
        }

        // Global Nav Listeners
        document.getElementById('btn-show-users')?.addEventListener('click', () => showView('users'));
        document.getElementById('btn-show-settings')?.addEventListener('click', () => {
            if (currentUser) {
                document.getElementById('set-weight').value = currentUser.weight_kg;
                document.getElementById('set-height').value = currentUser.height_cm;
            }
            showView('settings');
        });
        document.getElementById('btn-back-users')?.addEventListener('click', () => showView('dashboard'));

        const res = await fetch(`${API_URL}/users`);
        const data = await res.json();
        allUsers = data.users || [];

        if (allUsers.length === 0) {
            showView('onboarding');
        } else {
            // Priority: previously selected user, or first user
            const lastUserId = localStorage.getItem('nutriscale_user_id');
            currentUser = allUsers.find(u => u.id == lastUserId) || allUsers[0];
            showView('dashboard');
        }
        renderUserManagement();
    } catch (e) {
        console.error("Init failed", e);
        showView('onboarding'); // Fallback to onboarding
    } finally {
        showLoader(false);
    }
}

// Start
init();
