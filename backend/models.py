from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, default="User")
    height_cm = db.Column(db.Float, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=True) # 'male', 'female', 'other'
    activity_level = db.Column(db.String(20), nullable=False) # 'low', 'moderate', 'high'
    goal = db.Column(db.String(20), nullable=False) # 'lose', 'maintain', 'gain', 'muscle'
    
    # Calculated fields
    bmr = db.Column(db.Integer, nullable=True)
    daily_calorie_target = db.Column(db.Integer, nullable=True)
    
    # Relationships
    meals = db.relationship('Meal', backref='user', lazy=True, cascade='all, delete-orphan')
    daily_logs = db.relationship('DailyLog', backref='user', lazy=True, cascade='all, delete-orphan')
    progress_history = db.relationship('UserProgress', backref='user', lazy=True, cascade='all, delete-orphan')
    weekly_logs = db.relationship('WeeklyLog', backref='user', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'height_cm': self.height_cm,
            'weight_kg': self.weight_kg,
            'age': self.age,
            'gender': self.gender,
            'activity_level': self.activity_level,
            'goal': self.goal,
            'daily_calorie_target': self.daily_calorie_target
        }

class UserProgress(db.Model):
    """Tracks weight and height over time for graphing."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    weight_kg = db.Column(db.Float, nullable=False)
    height_cm = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'weight_kg': self.weight_kg,
            'height_cm': self.height_cm
        }

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    food_name = db.Column(db.String(100), nullable=False)
    portion_weight_g = db.Column(db.Float, nullable=False)
    calories = db.Column(db.Integer, nullable=False)
    protein_g = db.Column(db.Float, nullable=True)
    carbs_g = db.Column(db.Float, nullable=True)
    fat_g = db.Column(db.Float, nullable=True)
    
    # New Micronutrients
    sugar_g = db.Column(db.Float, nullable=True)
    fiber_g = db.Column(db.Float, nullable=True)
    sodium_mg = db.Column(db.Float, nullable=True)
    saturated_fat_g = db.Column(db.Float, nullable=True)
    is_ultra_processed = db.Column(db.Boolean, default=False)
    
    health_score = db.Column(db.Integer, nullable=True)
    health_emoji = db.Column(db.String(10), nullable=True)
    image_path = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'food_name': self.food_name,
            'portion_weight_g': self.portion_weight_g,
            'calories': self.calories,
            'protein_g': self.protein_g,
            'carbs_g': self.carbs_g,
            'fat_g': self.fat_g,
            'sugar_g': self.sugar_g,
            'fiber_g': self.fiber_g,
            'sodium_mg': self.sodium_mg,
            'saturated_fat_g': self.saturated_fat_g,
            'health_score': self.health_score,
            'health_emoji': self.health_emoji,
            'is_ultra_processed': self.is_ultra_processed,
            'image_url': self.image_path
        }

class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=date.today)
    total_calories = db.Column(db.Integer, default=0)
    total_protein = db.Column(db.Float, default=0.0)
    total_carbs = db.Column(db.Float, default=0.0)
    total_fat = db.Column(db.Float, default=0.0)
    total_sugar = db.Column(db.Float, default=0.0)
    total_fiber = db.Column(db.Float, default=0.0)
    total_sodium = db.Column(db.Float, default=0.0)
    meal_count = db.Column(db.Integer, default=0)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='_user_date_uc'),)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date.isoformat(),
            'total_calories': self.total_calories,
            'total_protein': self.total_protein,
            'total_carbs': self.total_carbs,
            'total_fat': self.total_fat,
            'total_sugar': getattr(self, 'total_sugar', 0.0),
            'total_fiber': getattr(self, 'total_fiber', 0.0),
            'total_sodium': getattr(self, 'total_sodium', 0.0),
            'meal_count': self.meal_count,
            'current_target_calories': self.user.daily_calorie_target if self.user else None
        }

class WeeklyLog(db.Model):
    """Summarizes performance over a 7-day period."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    avg_calories = db.Column(db.Integer, default=0)
    avg_health_score = db.Column(db.Integer, default=0)
    total_meals = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'avg_calories': self.avg_calories,
            'avg_health_score': self.avg_health_score,
            'total_meals': self.total_meals
        }
