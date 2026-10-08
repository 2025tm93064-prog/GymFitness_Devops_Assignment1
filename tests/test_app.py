import pytest

from app import CLIENTS, PROGRAMS, app


@pytest.fixture(autouse=True)
def clear_clients():
    CLIENTS.clear()
    yield
    CLIENTS.clear()


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


def test_homepage_shows_client_form_and_reset_button():
    response = app.test_client().get("/")

    assert b"Save client" in response.data
    assert b'type="reset"' in response.data
    assert b"Estimated daily calories" in response.data


def test_client_submission_saves_details_and_calorie_estimate():
    response = app.test_client().post(
        "/clients",
        data={
            "name": "Asha",
            "age": "28",
            "weight": "70",
            "program_id": "fat-loss",
            "adherence": "80",
        },
    )

    assert response.status_code == 201
    assert CLIENTS == [
        {
            "name": "Asha",
            "age": 28,
            "weight": 70.0,
            "program_id": "fat-loss",
            "program_name": "Fat Loss (FL)",
            "adherence": 80,
            "calories": 1540,
        }
    ]
    assert b"Asha" in response.data
    assert b"1540 kcal/day" in response.data


@pytest.mark.parametrize(
    "form_data",
    [
        {"name": "", "age": "28", "weight": "70", "program_id": "fat-loss", "adherence": "80"},
        {"name": "Asha", "age": "0", "weight": "70", "program_id": "fat-loss", "adherence": "80"},
        {"name": "Asha", "age": "28", "weight": "0", "program_id": "fat-loss", "adherence": "80"},
        {"name": "Asha", "age": "28", "weight": "70", "program_id": "unknown", "adherence": "80"},
    ],
)
def test_invalid_client_submission_is_rejected(form_data):
    response = app.test_client().post("/clients", data=form_data)

    assert response.status_code == 400
    assert CLIENTS == []
