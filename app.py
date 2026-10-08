from contextlib import contextmanager
from datetime import date
from pathlib import Path
import sqlite3

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
app.config["DATABASE"] = Path(app.instance_path) / "aceest_fitness.db"


@contextmanager
def database_connection():
    database_path = Path(app.config["DATABASE"])
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with database_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                age INTEGER NOT NULL,
                weight REAL NOT NULL,
                program_id TEXT NOT NULL,
                adherence INTEGER NOT NULL,
                calories INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                week TEXT NOT NULL,
                adherence INTEGER NOT NULL,
                FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
            );
            """
        )


def load_clients():
    with database_connection() as connection:
        client_rows = connection.execute(
            "SELECT * FROM clients ORDER BY id DESC"
        ).fetchall()
        clients = []
        for row in client_rows:
            client = dict(row)
            client["program_name"] = PROGRAMS[client["program_id"]]["name"]
            client["progress"] = [
                dict(progress_row)
                for progress_row in connection.execute(
                    "SELECT week, adherence FROM progress "
                    "WHERE client_id = ? ORDER BY id DESC",
                    (client["id"],),
                ).fetchall()
            ]
            clients.append(client)
        return clients


def render_home(selected_id="fat-loss", status=200, **context):
    if selected_id not in PROGRAMS:
        selected_id = "fat-loss"
    template_context = {
        "programs": PROGRAMS,
        "selected_id": selected_id,
        "clients": load_clients(),
        "form_data": {},
        "today": date.today().isoformat(),
    }
    template_context.update(context)
    return render_template("index.html", **template_context), status


initialize_database()


@app.get("/")
def index():
    selected_id = request.args.get("program", "fat-loss")
    return render_home(selected_id)


@app.post("/clients")
def create_client():
    form_data = request.form
    name = form_data.get("name", "").strip()
    program_id = form_data.get("program_id", "")

    try:
        age = int(form_data.get("age", ""))
        weight = float(form_data.get("weight", ""))
        adherence = int(form_data.get("adherence", ""))
    except (TypeError, ValueError):
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
        return render_home(selected_id, 400, error=error, form_data=form_data)

    program = PROGRAMS[program_id]
    calories = int(weight * program["calorie_factor"])
    try:
        with database_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO clients "
                "(name, age, weight, program_id, adherence, calories) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (name, age, weight, program_id, adherence, calories),
            )
            client_id = cursor.lastrowid
            connection.execute(
                "INSERT INTO progress (client_id, week, adherence) VALUES (?, ?, ?)",
                (client_id, date.today().isoformat(), adherence),
            )
    except sqlite3.IntegrityError:
        return render_home(
            selected_id,
            409,
            error="A client with that name already exists.",
            form_data=form_data,
        )

    client = next(client for client in load_clients() if client["id"] == client_id)
    return render_home(selected_id, 201, saved_client=client)


@app.post("/clients/<int:client_id>/progress")
def add_progress(client_id):
    try:
        adherence = int(request.form.get("adherence", ""))
        week = date.fromisoformat(request.form.get("week", "")).isoformat()
    except (TypeError, ValueError):
        return render_home(
            status=400, error="Enter a valid week and adherence percentage."
        )

    if not 0 <= adherence <= 100:
        return render_home(
            status=400, error="Enter adherence between 0 and 100 percent."
        )

    with database_connection() as connection:
        client = connection.execute(
            "SELECT program_id FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
        if client is None:
            return jsonify({"error": "Client not found"}), 404
        connection.execute(
            "INSERT INTO progress (client_id, week, adherence) VALUES (?, ?, ?)",
            (client_id, week, adherence),
        )
        connection.execute(
            "UPDATE clients SET adherence = ? WHERE id = ?", (adherence, client_id)
        )

    return render_home(
        client["program_id"],
        201,
        progress_saved={"week": week, "adherence": adherence},
    )


@app.get("/api/clients")
def list_clients():
    return jsonify(load_clients())


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
