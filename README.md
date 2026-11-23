# ACEest Fitness & Gym

Version 1.3 is a Flask web app for browsing the three preset fitness programs, creating client profiles, estimating calories, recording weekly adherence, logging workouts, and tracking body measurements with BMI. Local runs default to SQLite under Flask's `instance` directory. Kubernetes runs use PostgreSQL so deployment strategies can run multiple app replicas against the same data.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000> in a browser.

To connect a local run to PostgreSQL instead, set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`. `DATABASE_URL` may be used in place of those settings.

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

SQLite data is written to `instance/aceest_fitness.db`. When running the app in a disposable Docker container, mount a volume at `/app/instance` if the local database should survive container removal.

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

**Jenkins** ([Jenkinsfile](Jenkinsfile)) checks out the repository, runs SonarQube analysis, builds a clean Docker image, runs Pytest inside it, and publishes versioned images to Docker Hub only after tests pass. Pull-request builds do not receive SonarQube or Docker Hub credentials.

Configure the Jenkins environment variable `SONAR_HOST_URL` with the reachable SonarQube server URL, and add a **Secret text** credential with ID `sonarqube-token` containing a project analysis token. The scanner reads [sonar-project.properties](sonar-project.properties) and waits for the quality gate; a failed gate fails the pipeline. Add a **Username with password** credential with ID `dockerhub-credentials` using a Docker Hub access token as the password. Jenkins uses the `DOCKERHUB_REPO` build parameter for the repository name, tags images with the Git tag or build number, and pushes `latest` from `main`. The Jenkins agent must be able to reach SonarQube and Docker Hub and run Docker.

### Trigger Jenkins builds for pull requests

Use a Multibranch Pipeline so Jenkins discovers `Jenkinsfile` on `main`, feature branches, and pull-request revisions. The pipeline polls SCM every five minutes; configure the GitHub webhook below for faster push and pull-request triggers. The Jenkins server needs Git, Docker, the **Pipeline** plugin, and the **GitHub Branch Source** plugin. The Jenkins service account must be able to access Docker.

1. In Jenkins, select **New Item**, enter a job name, choose **Multibranch Pipeline**, and select **OK**.
2. Under **Branch Sources**, add **GitHub**. Select the repository owner and repository; add a GitHub credential if required.
3. In the branch source discovery behaviours, enable **Discover branches** and **Discover pull requests from origin**. Choose whether PR builds test the PR head or merge it with the target branch; merge-with-target checks the combined change.
4. Set the **Script Path** to `Jenkinsfile`, save the job, then select **Scan Multibranch Pipeline Now**. Jenkins should discover `main`, feature branches, and open PRs.
5. In the GitHub repository, open **Settings > Webhooks > Add webhook**. Set the payload URL to `http://<jenkins-host>:8080/github-webhook/`, choose `application/json`, and enable **Pushes** and **Pull requests** events. Use `https://` if Jenkins is configured with TLS.
6. Confirm the Jenkins host and webhook endpoint are reachable from GitHub. For an EC2 VM, configure its security group and host firewall to allow the webhook connection on the Jenkins port.
7. Push a commit to a branch with an open PR, or open/update a PR. Jenkins should start the corresponding branch/PR job; check its **Console Output** for checkout, Docker build, Pytest, and image cleanup.

The `Jenkinsfile` uses `checkout scm`, so Jenkins checks out the branch or PR revision selected by the Multibranch job. GitHub Actions also runs the repository's lint, Docker build, and tests for every push and pull request.

## Kubernetes on Minikube

The manifests are in [k8s/](k8s/). They deploy the Flask app with PostgreSQL, a persistent PostgreSQL volume, database readiness checks, and health probes. Set the Docker Hub image name in the `images` section of the selected `kustomization.yaml` files before applying them. The Docker Hub repository must be public, or Kubernetes must be configured with an image pull secret.

Create the namespace and database credential secret without storing the password in Git:

```powershell
kubectl create namespace aceest
kubectl -n aceest create secret generic aceest-db `
  --from-literal=DB_USER=aceest `
  --from-literal=DB_PASSWORD='REPLACE_WITH_A_STRONG_PASSWORD'
```

Apply the rolling-update configuration:

```powershell
kubectl apply -k k8s/overlays/rolling
kubectl -n aceest rollout status deployment/aceest-app
minikube service aceest-service -n aceest --url
```

The app is exposed on NodePort `30080`. Kubernetes creates the PostgreSQL data claim; its storage class must support persistent volumes.

### Deployment strategies

- **Rolling update:** [k8s/overlays/rolling/](k8s/overlays/rolling/) keeps two replicas available while replacing pods. Roll back with `kubectl -n aceest rollout undo deployment/aceest-app`.
- **Blue-green:** [k8s/strategies/blue-green/](k8s/strategies/blue-green/) runs separate blue and green deployments. After green is healthy, switch the Service selector to `version: green`; switch it back to `version: blue` to roll back. The Jenkins pipeline can perform this switch after a successful rollout.
- **Canary:** [k8s/strategies/canary/](k8s/strategies/canary/) routes 90% to stable and 10% to canary through Istio. For rollback, set the VirtualService weights to 100% stable and 0% canary; Kubernetes rollout history can also restore the candidate Deployment.
- **Shadow:** [k8s/strategies/shadow/](k8s/strategies/shadow/) mirrors GET traffic to a shadow version while returning the primary version's response. Writes are intentionally not mirrored to avoid duplicate database changes. Roll back by removing the `mirror` rule or scaling the shadow Deployment to zero.
- **A/B testing:** [k8s/strategies/ab-testing/](k8s/strategies/ab-testing/) routes requests with `x-aceest-cohort: B` to variant B and all other requests to variant A. Roll back the B cohort to variant A in the VirtualService or restore the variant-B Deployment's prior image.

Install Istio in Minikube before applying the canary, shadow, or A/B manifests. For example, with `istioctl` installed, run `istioctl install --set profile=demo -y`. The gateway host in these manifests is `aceest.local`; configure local DNS or use port-forwarding to reach the Istio ingress gateway.

Update the blue/stable image tags in the strategy manifests to a previously published Docker Hub image, and the green/candidate tags to the release under test. Keep database changes backward-compatible while old and new versions run concurrently.

### Optional Jenkins deployment

For automated deployment, add a Jenkins **Secret file** credential with ID `minikube-kubeconfig`, containing a kubeconfig usable by the Jenkins agent. The agent also needs `kubectl` and network access to the cluster. Run the Multibranch build with `DEPLOY_TO_MINIKUBE=true` and choose a `DEPLOYMENT_STRATEGY`. The parameter defaults to deployment disabled so builds do not change a cluster until it is configured.

## Assignment 2 report

Create the required 2–3 page report from the actual Jenkins, SonarQube, Docker Hub, and Minikube runs. Include the architecture, deployment strategy demonstrations, challenges and mitigations, and verified outcomes. Do not claim a deployment or quality gate passed until you have captured its run results.

If Docker commands fail with permission denied for `/var/run/docker.sock`, grant the Jenkins service account Docker access and restart Jenkins. On a Linux assignment VM, for example:

```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
sudo -u jenkins docker version
```

Docker group membership grants effectively root-level control of the VM; use this only on a trusted assignment machine.

The app is an assignment demo, not a production service.