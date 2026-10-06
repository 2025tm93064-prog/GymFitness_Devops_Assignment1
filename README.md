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

## Docker

```powershell
docker build -t aceest-fitness .
docker run --rm -p 5000:5000 aceest-fitness
docker run --rm aceest-fitness python -m pytest
```

The image uses `python:3.12-slim`, installs dependencies in a cached layer, runs as a non-root user, and serves the app with gunicorn.

## CI/CD

**GitHub Actions** ([.github/workflows/main.yml](.github/workflows/main.yml)) runs on every push and pull request:

1. `build-and-lint`: installs dependencies, checks syntax with `compileall`, and lints with flake8.
2. `docker-test`: builds the Docker image and runs Pytest inside the container.

**Jenkins** ([Jenkinsfile](Jenkinsfile)) acts as a second, independent build check:

1. Pulls the latest code from GitHub.
2. Builds the image from scratch (`--no-cache`).
3. Runs Pytest inside the new image, then removes the image.

To set it up, create a Pipeline job on a Jenkins server that has Docker available, choose "Pipeline script from SCM", and point it at this repository's URL and the `main` branch. Enable "GitHub hook trigger for GITScm polling" (with a webhook) or "Poll SCM" so new commits start a build.

The app is an assignment demo, not a production service.