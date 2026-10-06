from flask import Flask, jsonify, render_template, request


PROGRAMS = {
    "fat-loss": {
        "name": "Fat Loss (FL)",
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


@app.get("/")
def index():
    selected_id = request.args.get("program", "fat-loss")
    if selected_id not in PROGRAMS:
        selected_id = "fat-loss"
    return render_template(
        "index.html", programs=PROGRAMS, selected_id=selected_id
    )


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
