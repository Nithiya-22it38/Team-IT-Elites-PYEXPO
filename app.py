from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this in production!

# --- Database helpers ---
def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   email TEXT UNIQUE NOT NULL,
                   password TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS foods (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT,
                   calories INTEGER,
                   carbs TEXT,
                   protein TEXT,
                   fats TEXT
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS meals (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_email TEXT,
                   meal_type TEXT,
                   food_id INTEGER,
                   date TEXT,
                   FOREIGN KEY(user_email) REFERENCES users(email),
                   FOREIGN KEY(food_id) REFERENCES foods(id)
                )''')
    c.execute('SELECT COUNT(*) FROM foods')
    if c.fetchone()[0] == 0:
        foods = [
            ('Apple', 52, '14g', '0.3g', '0.2g'),
            ('Boiled Egg', 68, '1g', '6g', '5g'),
            ('Brown Rice', 111, '23g', '2.6g', '0.9g'),
            ('Oatmeal', 150, '27g', '5g', '2.5g'),
            ('Banana', 90, '23g', '1g', '0.3g'),
            ('Grilled Chicken', 220, '0g', '40g', '5g'),
            ('Salad', 80, '16g', '2g', '0.5g'),
            ('Steamed Veggies', 70, '14g', '3g', '0.2g'),
        ]
        c.executemany('INSERT INTO foods (name, calories, carbs, protein, fats) VALUES (?, ?, ?, ?, ?)', foods)
    conn.commit()
    conn.close()

def get_foods():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM foods')
    foods = c.fetchall()
    conn.close()
    return foods

def get_meals(user, for_date=None):
    if not user:
        return []
    if not for_date:
        for_date = date.today().isoformat()
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT meals.meal_type, foods.name, foods.calories, foods.carbs, foods.protein, foods.fats
                 FROM meals JOIN foods ON meals.food_id = foods.id
                 WHERE meals.user_email = ? AND meals.date = ?''', (user, for_date))
    meals = c.fetchall()
    conn.close()
    return meals

def get_daily_totals(meals):
    totals = {'calories': 0, 'carbs': 0, 'protein': 0, 'fats': 0}
    for meal in meals:
        try:
            totals['calories'] += int(meal['calories'])
            totals['carbs'] += float(str(meal['carbs']).replace('g',''))
            totals['protein'] += float(str(meal['protein']).replace('g',''))
            totals['fats'] += float(str(meal['fats']).replace('g',''))
        except Exception:
            pass
    return totals

# --- Routes ---
@app.route('/')
def index():
    user = session.get('user')
    foods = get_foods()
    meals = get_meals(user)
    daily_totals = get_daily_totals(meals) if user else None
    return render_template('index.html', user=user, foods=foods, meals=meals, daily_totals=daily_totals)

@app.route('/add_meal', methods=['POST'])
def add_meal():
    if 'user' not in session:
        flash('Please log in to add meals.')
        return redirect(url_for('index'))
    meal_type = request.form['meal_type']
    food_id = request.form['food_id']
    user = session['user']
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO meals (user_email, meal_type, food_id, date) VALUES (?, ?, ?, ?)',
              (user, meal_type, food_id, date.today().isoformat()))
    conn.commit()
    conn.close()
    flash('Food added to meal!')
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    if user and check_password_hash(user['password'], password):
        session['user'] = email
        flash('Logged in successfully!')
    else:
        flash('Invalid email or password')
    return redirect(url_for('index'))

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    password = request.form['password']
    hashed = generate_password_hash(password)
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed))
        conn.commit()
        flash('Signup successful. You can now log in.')
    except sqlite3.IntegrityError:
        flash('Account already exists')
    conn.close()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully')
    return redirect(url_for('index'))

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        age = int(request.form['age'])
        gender = request.form['gender']
        height = float(request.form['height'])
        weight = float(request.form['weight'])
        activity = request.form['activity']
        goal = request.form['goal']

        bmr = 10 * weight + 6.25 * height - 5 * age
        if gender == 'Male':
            bmr += 5
        elif gender == 'Female':
            bmr -= 161

        activity_factors = {
            'Sedentary': 1.2,
            'Lightly Active': 1.375,
            'Moderately Active': 1.55,
            'Very Active': 1.725
        }
        calories = bmr * activity_factors.get(activity, 1.2)

        if goal == 'Lose Weight':
            calories -= 500
        elif goal == 'Gain Weight':
            calories += 500

        user = session.get('user')
        foods = get_foods()
        meals = get_meals(user)
        daily_totals = get_daily_totals(meals) if user else None
        return render_template('index.html', calorie_result=int(calories), user=user, foods=foods, meals=meals, daily_totals=daily_totals)
    except Exception as e:
        flash("Something went wrong. Please check your input.")
        return redirect(url_for('index'))

@app.route('/history', methods=['GET', 'POST'])
def history():
    user = session.get('user')
    selected_date = request.form.get('history_date') if request.method == 'POST' else date.today().isoformat()
    foods = get_foods()
    meals = get_meals(user, for_date=selected_date)
    daily_totals = get_daily_totals(meals) if user else None
    return render_template('index.html', user=user, foods=foods, meals=meals, daily_totals=daily_totals, history_date=selected_date, history_mode=True)

if __name__ == '__main__':
    if not os.path.exists('users.db'):
        init_db()
    app.run(debug=True)
