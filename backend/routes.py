import os
import datetime
import traceback
from flask import Blueprint, request, jsonify, current_app, Response
from backend.models import db, User, Meal, DailyLog, UserProgress, WeeklyLog
from backend.services.hardware import scale_service, camera_service, display_service
from backend.services.nutrition import (
    calculate_bmr, calculate_tdee, calculate_target_calories, 
    estimate_nutrition_from_image
)

api_bp = Blueprint('api', __name__)

@api_bp.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    if not hasattr(camera_service, 'gen_frames'):
        return "Streaming not supported in Mock mode", 404
        
    return Response(camera_service.gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@api_bp.route('/sensor/tare', methods=['POST'])
def tare_scale():
    success = scale_service.tare()
    return jsonify({"success": success})

# Global state for current active user (simple in-memory for prototype)
# In production, use session or JWT tokens
current_user_id = None

def get_current_user():
    """Helper to get current active user"""
    global current_user_id
    if current_user_id is None:
        # Auto-select first user if exists
        user = User.query.first()
        if user:
            current_user_id = user.id
    return User.query.get(current_user_id) if current_user_id else None

@api_bp.route('/user/setup', methods=['POST'])
def user_setup():
    """Create a new user profile"""
    global current_user_id
    data = request.json
    try:
        # Check if we already have 3 users
        user_count = User.query.count()
        if user_count >= 3:
            return jsonify({"error": "Maximum 3 users allowed"}), 400
        
        user = User(
            name=data.get('name', f'User {user_count + 1}'),
            height_cm=data['height'],
            weight_kg=data['weight'],
            age=data['age'],
            gender=data['gender'],
            activity_level=data['activity_level'],
            goal=data['goal']
        )
        
        bmr = calculate_bmr(user.weight_kg, user.height_cm, user.age, user.gender)
        tdee = calculate_tdee(bmr, user.activity_level)
        user.bmr = bmr
        user.daily_calorie_target = calculate_target_calories(tdee, user.goal)
        
        db.session.add(user)
        db.session.flush() # Get ID
        
        # Save initial progress
        progress = UserProgress(
            user_id=user.id,
            weight_kg=user.weight_kg,
            height_cm=user.height_cm
        )
        db.session.add(progress)
        db.session.commit()
        
        # Set as current user
        current_user_id = user.id
        display_service.update_display(
            f"Welcome {user.name}!",
            f"Goal: {user.daily_calorie_target} kcal",
            ""
        )
        
        return jsonify(user.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@api_bp.route('/users', methods=['GET'])
def list_users():
    """Get all user profiles"""
    users = User.query.all()
    return jsonify({
        "users": [u.to_dict() for u in users],
        "current_user_id": current_user_id
    })

@api_bp.route('/user/switch/<int:user_id>', methods=['POST'])
def switch_user(user_id):
    """Switch to a different user profile"""
    global current_user_id
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    current_user_id = user_id
    display_service.update_display(
        f"Switched to {user.name}",
        f"Goal: {user.daily_calorie_target} kcal",
        ""
    )
    return jsonify(user.to_dict())

@api_bp.route('/user/update', methods=['PUT'])
def update_user():
    """Update current user's profile"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "No active user"}), 400
    
    data = request.json
    try:
        if 'name' in data:
            user.name = data['name']
        if 'height' in data:
            user.height_cm = data['height']
        if 'weight' in data:
            user.weight_kg = data['weight']
        if 'age' in data:
            user.age = data['age']
        if 'gender' in data:
            user.gender = data['gender']
        if 'activity_level' in data:
            user.activity_level = data['activity_level']
        if 'goal' in data:
            user.goal = data['goal']
        
        # Recalculate targets
        bmr = calculate_bmr(user.weight_kg, user.height_cm, user.age, user.gender)
        tdee = calculate_tdee(bmr, user.activity_level)
        user.bmr = bmr
        user.daily_calorie_target = calculate_target_calories(tdee, user.goal)
        
        db.session.commit()
        
        # Track weight change if provided
        if 'weight' in data or 'height' in data:
            progress = UserProgress(
                user_id=user.id,
                weight_kg=user.weight_kg,
                height_cm=user.height_cm
            )
            db.session.add(progress)
            db.session.commit()
            
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@api_bp.route('/sensor/weight', methods=['GET'])
def get_weight():
    weight = scale_service.get_weight()
    # Return both keys for compatibility with polling and refresh logic
    return jsonify({"weight": weight, "weight_g": weight})

@api_bp.route('/analyze-image', methods=['POST'])
def analyze_meal():
    """
    Captures image, reads scale, and returns estimated nutrition via AI.
    Supports both Pi Camera and client-uploaded images.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "No active user"}), 400
    
    # Check if client uploaded an image
    image_source = request.form.get('image_source', 'pi')  # 'pi' or 'client'
    print(f"[ROUTES] Image source: {image_source}", flush=True)
    print(f"[ROUTES] Files in request: {list(request.files.keys())}", flush=True)
    import sys; sys.stdout.flush()  # Force flush
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    image_filename = f"meal_{timestamp}.jpg"
    image_path = os.path.join(current_app.static_folder, 'images', image_filename)
    
    # Ensure images directory exists
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    
    if image_source == 'client' and 'image_file' in request.files:
        # Save uploaded image
        file = request.files['image_file']
        print(f"[DEBUG] Client uploaded file: {file.filename}, content_type: {file.content_type}")
        file.save(image_path)
        print(f"[DEBUG] Saved client image to: {image_path}")
    else:
        # Use Pi Camera (or mock)
        print(f"[DEBUG] Using camera service (mock or real)")
        if not camera_service.capture_image(image_path):
            return jsonify({"error": "Camera failed"}), 500
        print(f"[DEBUG] Camera saved image to: {image_path}")
    
    # Verify image exists
    if not os.path.exists(image_path):
        print(f"[ERROR] Image file does not exist: {image_path}")
        return jsonify({"error": "Image save failed"}), 500
    
    print(f"[DEBUG] Image size: {os.path.getsize(image_path)} bytes")
    
    try:
        # Get Weight
        weight = request.form.get('weight_g')
        if weight:
            weight = float(weight)
            print(f"[DEBUG] Weight from form: {weight}g", flush=True)
        else:
            weight = scale_service.get_weight()
            print(f"[DEBUG] Weight from scale: {weight}g", flush=True)

        if weight <= 0:
            return jsonify({"error": "No food detected on scale"}), 400

        # Estimate Nutrition (Adaptive)
        print(f"[DEBUG] Calling estimate_nutrition_from_image...", flush=True)
        nutrition = estimate_nutrition_from_image(image_path, weight, user.goal)
        # Use safe printing to avoid Windows console emoji errors
        try:
            print(f"[DEBUG] Nutrition result: {nutrition}", flush=True)
        except UnicodeEncodeError:
            print(f"[DEBUG] Nutrition result: {nutrition.get('food_name', 'Unknown')}, Score: {nutrition.get('health_score', 0)}", flush=True)
        
        return jsonify({
            "weight_g": weight,
            "image_url": f"/static/images/{image_filename}",
            **nutrition
        })
    except Exception as e:
        print(f"[ERROR] analyze_meal crashed: {str(e)}", flush=True)
        traceback.print_exc()
        return jsonify({"error": "Analysis Logic Failed", "details": str(e)}), 500

@api_bp.route('/meal', methods=['POST'])
def log_meal():
    user = get_current_user()
    if not user:
        return jsonify({"error": "No active user"}), 400

    data = request.json
    meal = Meal(
        user_id=user.id,
        food_name=data['food_name'],
        portion_weight_g=data['portion_weight_g'],
        calories=data['calories'],
        protein_g=data.get('protein_g', 0),
        carbs_g=data.get('carbs_g', 0),
        fat_g=data.get('fat_g', 0),
        sugar_g=data.get('sugar_g', 0),
        fiber_g=data.get('fiber_g', 0),
        sodium_mg=data.get('sodium_mg', 0),
        saturated_fat_g=data.get('saturated_fat_g', 0),
        is_ultra_processed=data.get('is_ultra_processed', False),
        health_score=data.get('health_score', 0),
        health_emoji=data.get('health_emoji', ''),
        image_path=data.get('image_path', '')
    )
    
    db.session.add(meal)
    
    # Update Daily Log for this user
    today = datetime.date.today()
    log = DailyLog.query.filter_by(user_id=user.id, date=today).first()
    if not log:
        log = DailyLog(
            user_id=user.id,
            date=today,
            total_calories=0,
            total_protein=0,
            total_carbs=0,
            total_fat=0,
            total_sugar=0,
            total_fiber=0,
            total_sodium=0,
            meal_count=0
        )
        db.session.add(log)
    
    log.total_calories += meal.calories
    log.total_protein += meal.protein_g
    log.total_carbs += meal.carbs_g
    log.total_fat += meal.fat_g
    log.total_sugar += meal.sugar_g
    log.total_fiber += meal.fiber_g
    log.total_sodium += meal.sodium_mg
    log.meal_count += 1
    
    db.session.commit()
    
    # Update Physical Display with enhanced feedback
    remaining = user.daily_calorie_target - log.total_calories
    display_service.update_display(
        f"{meal.health_emoji} Score: {meal.health_score}",
        f"Cal: {log.total_calories}/{user.daily_calorie_target}",
        f"Remaining: {remaining}"
    )

    return jsonify(meal.to_dict())

@api_bp.route('/meal/<int:meal_id>', methods=['GET'])
def get_meal(meal_id):
    """Get single meal details"""
    meal = Meal.query.get(meal_id)
    if not meal:
        return jsonify({"error": "Meal not found"}), 404
    return jsonify(meal.to_dict())

@api_bp.route('/meal/<int:meal_id>', methods=['DELETE'])
def delete_meal(meal_id):
    """Delete a meal and update daily totals"""
    meal = Meal.query.get(meal_id)
    if not meal:
        return jsonify({"error": "Meal not found"}), 404
    
    try:
        # Update Daily Log
        meal_date = meal.timestamp.date()
        log = DailyLog.query.filter_by(user_id=meal.user_id, date=meal_date).first()
        if log:
            log.total_calories = max(0, log.total_calories - meal.calories)
            log.total_protein = max(0, log.total_protein - meal.protein_g)
            log.total_carbs = max(0, log.total_carbs - meal.carbs_g)
            log.total_fat = max(0, log.total_fat - meal.fat_g)
            log.meal_count = max(0, log.meal_count - 1)
            
        db.session.delete(meal)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_bp.route('/daily', methods=['GET'])
def get_daily_stats():
    user = get_current_user()
    if not user:
        return jsonify({"error": "No active user"}), 400
    
    today = datetime.date.today()
    log = DailyLog.query.filter_by(user_id=user.id, date=today).first()
    
    # Base statistics
    stats = {
        'date': today.isoformat(),
        'total_calories': 0,
        'total_protein': 0,
        'total_carbs': 0,
        'total_fat': 0,
        'total_sugar': 0.0,
        'total_fiber': 0.0,
        'total_sodium': 0.0,
        'meal_count': 0,
        'user_name': user.name,
        'diagnostics_key': 'refactored_v1'
    }

    if log:
        stats['total_calories'] = log.total_calories
        stats['total_protein'] = log.total_protein
        stats['total_carbs'] = log.total_carbs
        stats['total_fat'] = log.total_fat
        stats['total_sugar'] = float(getattr(log, 'total_sugar', 0.0) or 0.0)
        stats['total_fiber'] = float(getattr(log, 'total_fiber', 0.0) or 0.0)
        stats['total_sodium'] = float(getattr(log, 'total_sodium', 0.0) or 0.0)
        stats['meal_count'] = log.meal_count

    # GOAL AUTHORITY: Use user.daily_calorie_target as the source of truth
    target_cals = user.daily_calorie_target
    stats['target_calories'] = target_cals
    
    # Calculate Remaining vs Over
    diff = target_cals - stats['total_calories']
    stats['remaining_calories'] = diff # Can be negative
    stats['is_over_budget'] = diff < 0

    # Macro targets (calculated from authority goal)
    if user.goal == 'muscle' or user.goal == 'gain':
        stats['protein_target'] = int((target_cals * 0.30) / 4)
        stats['carbs_target'] = int((target_cals * 0.40) / 4)
        stats['fat_target'] = int((target_cals * 0.30) / 9)
    elif user.goal == 'lose':
        stats['protein_target'] = int((target_cals * 0.35) / 4)
        stats['carbs_target'] = int((target_cals * 0.35) / 4)
        stats['fat_target'] = int((target_cals * 0.30) / 9)
    else:
        stats['protein_target'] = int((target_cals * 0.25) / 4)
        stats['carbs_target'] = int((target_cals * 0.45) / 4)
        stats['fat_target'] = int((target_cals * 0.30) / 9)

    # Today's meals
    start_of_day = datetime.datetime.combine(today, datetime.time.min)
    meals = Meal.query.filter(
        Meal.user_id == user.id,
        Meal.timestamp >= start_of_day
    ).order_by(Meal.timestamp.desc()).all()
    stats['meals'] = [m.to_dict() for m in meals]
    
    return jsonify(stats)

@api_bp.route('/user/reset', methods=['DELETE'])
def reset_user():
    try:
        # Delete all data
        db.session.query(Meal).delete()
        db.session.query(DailyLog).delete()
        db.session.query(User).delete()
        db.session.commit()
        return jsonify({"success": True, "message": "All data cleared"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_bp.route('/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user profile and all associated data"""
    global current_user_id
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    try:
        db.session.delete(user)
        db.session.commit()
        
        # If deleted user was active, clear current
        if current_user_id == user_id:
            current_user_id = None
            
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_bp.route('/weekly', methods=['GET'])
def get_weekly_stats():
    """Aggregated stats for the last 7 days"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "No active user"}), 400
        
    seven_days_ago = datetime.date.today() - datetime.timedelta(days=7)
    
    # Get daily logs
    logs = DailyLog.query.filter(
        DailyLog.user_id == user.id,
        DailyLog.date >= seven_days_ago
    ).order_by(DailyLog.date.asc()).all()
    
    # Get weight history
    history = UserProgress.query.filter(
        UserProgress.user_id == user.id
    ).order_by(UserProgress.timestamp.asc()).all()
    
    # Calculate weekly performance
    meals = Meal.query.filter(
        Meal.user_id == user.id,
        Meal.timestamp >= datetime.datetime.combine(seven_days_ago, datetime.time.min)
    ).all()
    
    avg_score = 0
    if meals:
        avg_score = int(sum(m.health_score or 0 for m in meals) / len(meals))
        
    return jsonify({
        "daily_logs": [log.to_dict() for log in logs],
        "weight_history": [p.to_dict() for p in history],
        "weekly_avg_score": avg_score
    })
