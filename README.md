# ACEest Fitness & Gym

Version 1 is a Flask web app for browsing the three preset fitness programs from the original ACEest desktop prototype. It displays each program's workout and nutrition outline and provides read-only JSON endpoints. Client records and database persistence are planned for a later milestone.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000> in a browser.

## API

- `GET /api/programs` lists the available programs.
- `GET /api/programs/<program_id>` returns one program. IDs are `fat-loss`, `muscle-gain`, and `beginner`.

## Tests

```powershell
python -m pytest
```

The app is an assignment demo, not a production service.