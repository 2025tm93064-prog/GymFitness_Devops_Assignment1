from app import PROGRAMS, app


def test_homepage_shows_default_program():
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"Fat Loss (FL)" in response.data
    assert b"5x5 Back Squat" in response.data


def test_homepage_can_select_another_program():
    response = app.test_client().get("/?program=beginner")

    assert response.status_code == 200
    assert b"Beginner (BG)" in response.data
    assert b"Technique Mastery" in response.data


def test_program_list_api_returns_all_programs():
    response = app.test_client().get("/api/programs")

    assert response.status_code == 200
    assert set(response.get_json()) == set(PROGRAMS)


def test_program_api_returns_selected_program():
    response = app.test_client().get("/api/programs/muscle-gain")

    assert response.status_code == 200
    assert response.get_json()["name"] == "Muscle Gain (MG)"


def test_program_api_returns_404_for_unknown_program():
    response = app.test_client().get("/api/programs/unknown")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Program not found"}