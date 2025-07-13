
def calculate_calories(data):
    age = int(data['age'])
    weight = float(data['weight'])
    height = float(data['height'])
    gender = data['gender']
    activity = data['activity']
    goal = data['goal']


    # BMR using Mifflin-St Jeor formula
    if gender == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161


    activity_factors = {
        'low': 1.2,
        'moderate': 1.55,
        'high': 1.9
    }


    calories = bmr * activity_factors.get(activity, 1.2)


    if goal == 'loss':
        calories -= 500
    elif goal == 'gain':
        calories += 500


    return int(calories)


