# ACEest Fitness & Gym

Version 1.2 is a Flask web app for browsing the three preset fitness programs, creating client profiles, estimating calories, and recording weekly adherence. Client and adherence data are stored in SQLite under Flask's `instance` directory and survive application restarts. The database file is local runtime data and is excluded from Git.

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
- `GET /api/clients` lists saved clients and their adherence history.

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

SQLite data is written to `instance/aceest_fitness.db`. When running the app in a disposable Docker container, mount a volume at `/app/instance` if the database should survive container removal.

## CI/CD

**GitHub Actions** ([.github/workflows/main.yml](.github/workflows/main.yml)) runs on every push and pull request:

1. `build-and-lint`: installs dependencies, checks syntax with `compileall`, and lints with flake8.
2. `docker-test`: builds the Docker image and runs Pytest inside the container.

**Jenkins** ([Jenkinsfile](Jenkinsfile)) acts as a second, independent build check. It checks out the repository, builds a clean Docker image, runs Pytest inside that image, and removes the image afterward.

### Create the Jenkins Pipeline job

The Jenkins server needs Git and Docker installed. The Jenkinsfile uses Linux `sh` steps, so configure a Linux Jenkins agent with Docker available. The Jenkins service account must be allowed to access the Docker daemon.

1. Sign in to Jenkins and select **New Item**.
2. Enter a job name, select **Pipeline**, then select **OK**.
3. In the job configuration, find **Pipeline** and set **Definition** to **Pipeline script from SCM**.
4. Set **SCM** to **Git**, enter this repository's URL, and add credentials if the repository is private.
5. Set **Branch Specifier** to `*/main` and **Script Path** to `Jenkinsfile`.
6. Select **Save**, then select **Build Now**.
7. Open the build and check **Console Output**. A successful run should show checkout, Docker image build, Pytest, and image cleanup stages.

To trigger builds automatically, configure either **GitHub hook trigger for GITScm polling** and a GitHub webhook pointed at `https://<jenkins-host>/github-webhook/`, or configure **Poll SCM** in the job. The Jenkins host must be reachable by GitHub for webhooks to work.

If Docker commands fail with permission denied for `/var/run/docker.sock`, grant the Jenkins service account Docker access and restart Jenkins. On a Linux assignment VM, for example:

```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
sudo -u jenkins docker version
```

Docker group membership grants effectively root-level control of the VM; use this only on a trusted assignment machine.

The app is an assignment demo, not a production service.