import pytest

from app import PROGRAMS, app, initialize_database


@pytest.fixture(autouse=True)
def use_test_database(tmp_path):
    app.config["DATABASE"] = tmp_path / "test.sqlite"
    initialize_database()
    yield


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
    clients = app.test_client().get("/api/clients").get_json()
    assert len(clients) == 1
    assert clients[0]["name"] == "Asha"
    assert clients[0]["age"] == 28
    assert clients[0]["weight"] == 70.0
    assert clients[0]["program_id"] == "fat-loss"
    assert clients[0]["adherence"] == 80
    assert clients[0]["calories"] == 1540
    assert clients[0]["progress"] == [{"week": clients[0]["progress"][0]["week"], "adherence": 80}]
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
    assert app.test_client().get("/api/clients").get_json() == []


def test_client_is_persisted_between_requests():
    client = app.test_client()
    client.post(
        "/clients",
        data={
            "name": "Asha",
            "age": "28",
            "weight": "70",
            "program_id": "fat-loss",
            "adherence": "80",
        },
    )

    response = client.get("/")

    assert b"Asha" in response.data
    assert b"Saved clients" in response.data


def test_duplicate_client_name_is_rejected():
    client = app.test_client()
    data = {
        "name": "Asha",
        "age": "28",
        "weight": "70",
        "program_id": "fat-loss",
        "adherence": "80",
    }
    client.post("/clients", data=data)

    response = client.post("/clients", data=data)

    assert response.status_code == 409
    assert b"already exists" in response.data
    assert len(client.get("/api/clients").get_json()) == 1


def test_weekly_adherence_is_saved_to_client_history():
    client = app.test_client()
    client.post(
        "/clients",
        data={
            "name": "Asha",
            "age": "28",
            "weight": "70",
            "program_id": "fat-loss",
            "adherence": "80",
        },
    )
    client_id = client.get("/api/clients").get_json()[0]["id"]

    response = client.post(
        f"/clients/{client_id}/progress",
        data={"week": "2026-10-05", "adherence": "65"},
    )

    saved_client = client.get("/api/clients").get_json()[0]
    assert response.status_code == 201
    assert saved_client["adherence"] == 65
    assert saved_client["progress"][0] == {"week": "2026-10-05", "adherence": 65}
    assert len(saved_client["progress"]) == 2


def test_invalid_weekly_adherence_is_rejected():
    client = app.test_client()
    client.post(
        "/clients",
        data={
            "name": "Asha",
            "age": "28",
            "weight": "70",
            "program_id": "fat-loss",
            "adherence": "80",
        },
    )
    client_id = client.get("/api/clients").get_json()[0]["id"]

    response = client.post(
        f"/clients/{client_id}/progress",
        data={"week": "2026-10-05", "adherence": "101"},
    )

    assert response.status_code == 400
    assert len(client.get("/api/clients").get_json()[0]["progress"]) == 1
