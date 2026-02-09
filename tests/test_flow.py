import unittest
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app, db

class TestMealTrackerFlow(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def test_full_flow(self):
        # 1. User Setup
        user_data = {
            "age": 30,
            "height": 180,
            "weight": 80,
            "gender": "male",
            "activity_level": "moderate",
            "goal": "maintain"
        }
        res = self.client.post('/api/user/setup', json=user_data)
        self.assertEqual(res.status_code, 200)
        data = res.json
        print(f"\n[1] Setup User: Needs {data['daily_calorie_target']} kcal")
        self.assertIn('daily_calorie_target', data)

        # 2. Get Weight (Mock)
        res = self.client.get('/api/sensor/weight')
        self.assertEqual(res.status_code, 200)
        weight = res.json['weight_g']
        print(f"[2] Scale Reading: {weight}g")
        
        # 3. Analyze Meal
        # We simulate frontend passing the weight
        res = self.client.post('/api/analyze-image', json={"weight_g": 250})
        self.assertEqual(res.status_code, 200)
        analysis = res.json
        print(f"[3] Analysis: {analysis['food_name']} ({analysis['calories']} kcal)")
        self.assertEqual(analysis['weight_g'], 250)

        # 4. Log Meal
        meal_data = {
            "food_name": analysis['food_name'],
            "portion_weight_g": analysis['weight_g'],
            "calories": analysis['calories'],
            "protein_g": analysis['protein_g'],
            "carbs_g": analysis['carbs_g'],
            "fat_g": analysis['fat_g'],
            "health_score": analysis['health_score'],
            "health_emoji": analysis['health_emoji'],
            "image_path": analysis['image_url']
        }
        res = self.client.post('/api/meal', json=meal_data)
        self.assertEqual(res.status_code, 200)
        print(f"[4] Meal Logged!")

        # 5. Check Daily Stats
        res = self.client.get('/api/daily')
        self.assertEqual(res.status_code, 200)
        stats = res.json
        print(f"[5] Daily Stats: {stats['total_calories']} / {stats['target_calories']} kcal")
        self.assertEqual(stats['meal_count'], 1)
        self.assertEqual(stats['total_calories'], analysis['calories'])
        
        # 6. Delete Meal
        meal_id = stats['meals'][0]['id']
        res = self.client.delete(f'/api/meal/{meal_id}')
        self.assertEqual(res.status_code, 200)
        print(f"[6] Meal Deleted!")
        
        # 7. Verify Deletion
        res = self.client.get('/api/daily')
        stats = res.json
        self.assertEqual(stats['meal_count'], 0)
        self.assertEqual(stats['total_calories'], 0)
        print(f"[7] Stats Reset: {stats['total_calories']} kcal")

if __name__ == '__main__':
    unittest.main()
