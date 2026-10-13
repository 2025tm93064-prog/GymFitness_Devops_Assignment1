# ACEest Fitness & Gym

Version 1.3 is a Flask web app for browsing the three preset fitness programs, creating client profiles, estimating calories, recording weekly adherence, logging workouts, and tracking body measurements with BMI. Client, adherence, workout, and measurement data are stored in SQLite under Flask's `instance` directory and survive application restarts. The database file is local runtime data and is excluded from Git.

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
- `POST /clients/<client_id>/workouts` logs a dated workout (Strength, Hypertrophy, Cardio, or Mobility).
- `POST /clients/<client_id>/metrics` logs weight, height, waist, and body-fat measurements; BMI is calculated from the recorded weight and height.

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

### Run the v1.3.0 container on a Linux VM

Run these commands in the VM from the cloned repository directory. Port `8081` is used because Jenkins commonly uses `8080` on the same VM.

```bash
cd ~/GymFitness_Devops_Assignment1
git switch main
git pull origin main
docker version
docker build --no-cache -t aceest-fitness:v1.3.0 .
docker run --rm aceest-fitness:v1.3.0 python -m pytest -q
```

The Docker version output should include both **Client** and **Server** sections, and the test command should pass. Create a named volume once to retain the SQLite database across container restarts:

```bash
docker volume create aceest-data
```

Start the app container, check the page and program API from the VM, then stop and remove the container when finished:

```bash
docker rm -f aceest-v130 2>/dev/null || true
docker run -d --name aceest-v130 -p 8081:5000 -v aceest-data:/app/instance aceest-fitness:v1.3.0
docker ps --filter name=aceest-v130
curl -i http://localhost:8081/
curl -f http://localhost:8081/api/programs
docker logs aceest-v130
docker stop aceest-v130
docker rm aceest-v130
```

The HTTP checks should return status `200`; the API should list all three programs. To open the app from outside the VM, visit `http://<EC2-public-IP>:8081` and allow inbound TCP port `8081` in the EC2 security group, restricted to your IP where possible. If Docker reports permission denied for `/var/run/docker.sock`, run the Docker commands with `sudo` or grant the VM user Docker access; Docker group membership is effectively root-level access.

## CI/CD

**GitHub Actions** ([.github/workflows/main.yml](.github/workflows/main.yml)) runs on every push and pull request:

1. `build-and-lint`: installs dependencies, checks syntax with `compileall`, and lints with flake8.
2. `docker-test`: builds the Docker image and runs Pytest inside the container.

**Jenkins** ([Jenkinsfile](Jenkinsfile)) acts as a second, independent build check. It checks out the repository, builds a clean Docker image, runs Pytest inside that image, and removes the image afterward.

Jenkins also runs SonarQube analysis with the `sonarsource/sonar-scanner-cli` Docker image before building the app image. Configure the Jenkins environment variable `SONAR_HOST_URL` with the reachable SonarQube server URL, and add a **Secret text** credential with ID `sonarqube-token` containing a project analysis token. The scanner reads [sonar-project.properties](sonar-project.properties) and waits for the quality gate; a failed gate fails the pipeline. The Jenkins agent must be able to reach the SonarQube server and run Docker.

### Trigger Jenkins builds for pull requests

Use a Multibranch Pipeline so Jenkins discovers `Jenkinsfile` on `main`, feature branches, and pull-request revisions. The Jenkins server needs Git, Docker, the **Pipeline** plugin, and the **GitHub Branch Source** plugin. The Jenkins service account must be able to access Docker.

1. In Jenkins, select **New Item**, enter a job name, choose **Multibranch Pipeline**, and select **OK**.
2. Under **Branch Sources**, add **GitHub**. Select the repository owner and repository; add a GitHub credential if required.
3. In the branch source discovery behaviours, enable **Discover branches** and **Discover pull requests from origin**. Choose whether PR builds test the PR head or merge it with the target branch; merge-with-target checks the combined change.
4. Set the **Script Path** to `Jenkinsfile`, save the job, then select **Scan Multibranch Pipeline Now**. Jenkins should discover `main`, feature branches, and open PRs.
5. In the GitHub repository, open **Settings > Webhooks > Add webhook**. Set the payload URL to `http://<jenkins-host>:8080/github-webhook/`, choose `application/json`, and enable **Pushes** and **Pull requests** events. Use `https://` if Jenkins is configured with TLS.
6. Confirm the Jenkins host and webhook endpoint are reachable from GitHub. For an EC2 VM, configure its security group and host firewall to allow the webhook connection on the Jenkins port.
7. Push a commit to a branch with an open PR, or open/update a PR. Jenkins should start the corresponding branch/PR job; check its **Console Output** for checkout, Docker build, Pytest, and image cleanup.

The existing `Jenkinsfile` uses `checkout scm`, so Jenkins checks out the branch or PR revision selected by the Multibranch job. GitHub Actions also runs the repository's lint, Docker build, and tests for every push and pull request; Jenkins provides the separate VM-based build check.

If Docker commands fail with permission denied for `/var/run/docker.sock`, grant the Jenkins service account Docker access and restart Jenkins. On a Linux assignment VM, for example:

```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
sudo -u jenkins docker version
```

Docker group membership grants effectively root-level control of the VM; use this only on a trusted assignment machine.

The app is an assignment demo, not a production service.