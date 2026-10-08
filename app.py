from flask import Flask, jsonify, render_template, request


PROGRAMS = {
    "fat-loss": {
        "name": "Fat Loss (FL)",
        "calorie_factor": 22,
        "workout": [
            "Mon: 5x5 Back Squat + AMRAP",
            "Tue: EMOM 20min Assault Bike",
            "Wed: Bench Press + 21-15-9",
            "Thu: 10RFT Deadlifts/Box Jumps",
            "Fri: 30min Active Recovery",
        ],
        "diet": [
            "Breakfast: 3 Egg Whites + Oats Idli",
            "Lunch: Grilled Chicken + Brown Rice",
            "Dinner: Fish Curry + Millet Roti",
            "Target: 2,000 kcal",
        ],
    },
    "muscle-gain": {
        "name": "Muscle Gain (MG)",
        "calorie_factor": 35,
        "workout": [
            "Mon: Squat 5x5",
            "Tue: Bench 5x5",
            "Wed: Deadlift 4x6",
            "Thu: Front Squat 4x8",
            "Fri: Incline Press 4x10",
            "Sat: Barbell Rows 4x10",
        ],
        "diet": [
            "Breakfast: 4 Eggs + PB Oats",
            "Lunch: Chicken Biryani (250g Chicken)",
            "Dinner: Mutton Curry + Jeera Rice",
            "Target: 3,200 kcal",
        ],
    },
    "beginner": {
        "name": "Beginner (BG)",
        "calorie_factor": 26,
        "workout": [
            "Circuit Training: Air Squats, Ring Rows, Push-ups.",
            "Focus: Technique Mastery & Form (90% Threshold)",
        ],
        "diet": [
            "Balanced Tamil Meals: Idli-Sambar, Rice-Dal, Chapati.",
            "Protein: 120g/day",
        ],
    },
}

app = Flask(__name__)
CLIENTS = []


@app.get("/")
def index():
    selected_id = request.args.get("program", "fat-loss")
    if selected_id not in PROGRAMS:
        selected_id = "fat-loss"
    return render_template(
        "index.html",
        programs=PROGRAMS,
        selected_id=selected_id,
        clients=CLIENTS,
        form_data={},
    )


@app.post("/clients")
def create_client():
    form_data = request.form
    name = form_data.get("name", "").strip()
    program_id = form_data.get("program_id", "")

    try:
        age = int(form_data.get("age", ""))
        weight = float(form_data.get("weight", ""))
        adherence = int(form_data.get("adherence", ""))
    except ValueError:
        age, weight, adherence = 0, 0, -1

    error = None
    if not name or len(name) > 100:
        error = "Enter a client name up to 100 characters."
    elif not 1 <= age <= 120:
        error = "Enter an age between 1 and 120."
    elif not 1 <= weight <= 500:
        error = "Enter a weight between 1 and 500 kg."
    elif not 0 <= adherence <= 100:
        error = "Enter adherence between 0 and 100 percent."
    elif program_id not in PROGRAMS:
        error = "Select a valid fitness program."

    selected_id = program_id if program_id in PROGRAMS else "fat-loss"
    if error:
        return render_template(
            "index.html",
            programs=PROGRAMS,
            selected_id=selected_id,
            clients=CLIENTS,
            form_data=form_data,
            error=error,
        ), 400

    program = PROGRAMS[program_id]
    client = {
        "name": name,
        "age": age,
        "weight": weight,
        "program_id": program_id,
        "program_name": program["name"],
        "adherence": adherence,
        "calories": int(weight * program["calorie_factor"]),
    }
    CLIENTS.append(client)

    return render_template(
        "index.html",
        programs=PROGRAMS,
        selected_id=selected_id,
        clients=CLIENTS,
        form_data={},
        saved_client=client,
    ), 201


@app.get("/api/programs")
def list_programs():
    return jsonify(PROGRAMS)


@app.get("/api/programs/<program_id>")
def get_program(program_id):
    program = PROGRAMS.get(program_id)
    if program is None:
        return jsonify({"error": "Program not found"}), 404
    return jsonify({"id": program_id, **program})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
