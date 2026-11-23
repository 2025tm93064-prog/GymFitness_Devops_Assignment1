# ACEest Fitness & Gym

ACEest Fitness is a Flask web app for browsing the three preset fitness programs, creating client profiles, estimating calories, recording weekly adherence, logging workouts, and tracking body measurements with BMI. The version in [VERSION](VERSION) is displayed on the homepage. Local runs default to SQLite under Flask's `instance` directory. Kubernetes runs use PostgreSQL so deployment strategies can run multiple app replicas against the same data.

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

### Push a version to Docker Hub

Jenkins publishes tested images automatically. To publish manually from the Rocky Linux VM, first check out the intended application revision and run the following from the repository directory. The image contains the currently checked-out code. Use a unique tag so an existing release is not overwritten.

```bash
git rev-parse HEAD
docker login --username 2025tm93064
IMAGE_TAG="$(cat VERSION)-manual-$(date -u +%Y%m%d%H%M%S)-$(git rev-parse --short=12 HEAD)"
docker build -t "2025tm93064/acefitness:$IMAGE_TAG" . && \
  docker run --rm "2025tm93064/acefitness:$IMAGE_TAG" python -m pytest -q && \
  docker push "2025tm93064/acefitness:$IMAGE_TAG"
```

Enter a Docker Hub access token when prompted; do not put it in the command line or Git. Docker may store login credentials in its configuration, so use a [credential store](https://docs.docker.com/reference/cli/docker/login/#credential-stores) on shared machines. This manual login is separate from Jenkins' `dockerhub-credentials`.

### Run the current container on a Linux VM

Run these commands in the VM from the cloned repository directory. Port `8081` is used because Jenkins commonly uses `8080` on the same VM.

```bash
cd ~/GymFitness_Devops_Assignment1
git switch main
git pull origin main
docker version
docker build --no-cache -t aceest-fitness:local .
docker run --rm aceest-fitness:local python -m pytest -q
```

The Docker version output should include both **Client** and **Server** sections, and the test command should pass. Create a named volume once to retain the SQLite database across container restarts:

```bash
docker volume create aceest-data
```

Start the app container, check the page and program API from the VM, then stop and remove the container when finished:

```bash
docker rm -f aceest-local 2>/dev/null || true
docker run -d --name aceest-local -p 8081:5000 -v aceest-data:/app/instance aceest-fitness:local
docker ps --filter name=aceest-local
curl -i http://localhost:8081/
curl -f http://localhost:8081/api/programs
docker logs aceest-local
docker stop aceest-local
docker rm aceest-local
```

The HTTP checks should return status `200`; the API should list all three programs. To open the app from outside the VM, visit `http://<EC2-public-IP>:8081` and allow inbound TCP port `8081` in the EC2 security group, restricted to your IP where possible. If Docker reports permission denied for `/var/run/docker.sock`, run the Docker commands with `sudo` or grant the VM user Docker access; Docker group membership is effectively root-level access.

## CI/CD

**GitHub Actions** ([.github/workflows/main.yml](.github/workflows/main.yml)) runs on every push and pull request:

1. `build-and-lint`: installs dependencies, checks syntax with `compileall`, and lints with flake8.
2. `docker-test`: builds the Docker image and runs Pytest inside the container.

**Jenkins** ([Jenkinsfile](Jenkinsfile)) checks out the repository, runs SonarQube analysis, builds a clean Docker image, runs Pytest inside it, and publishes versioned images to Docker Hub only after tests pass. Pull-request builds do not receive SonarQube or Docker Hub credentials.

Configure the Jenkins environment variable `SONAR_HOST_URL` with the reachable SonarQube server URL, and add a **Secret text** credential with ID `sonarqube-token` containing a project analysis token. The scanner reads [sonar-project.properties](sonar-project.properties) and waits for the quality gate; a failed gate fails the pipeline. Add a **Username with password** credential with ID `dockerhub-credentials` using a Docker Hub access token as the password. The `DOCKERHUB_REPO` build parameter defaults to `2025tm93064/acefitness` for automatic builds and can be overridden for a manual build. Jenkins reads `VERSION` and publishes an image tagged `v1.4.0-build-<build-number>-<12-character-commit>`, as well as `latest` for `main`. Builds do not run concurrently. The Jenkins agent must be able to reach SonarQube and Docker Hub and run Docker.

### SonarQube on a Rocky Linux VM

These steps document the setup used with SonarQube 9.9 on the same VM as Jenkins and Docker. Use a Java version supported by your SonarQube version; the existing 9.9 installation previously ran with Java 17.

1. Check the service and its logs:

   ```bash
   sudo systemctl status sonarqube --no-pager -l
   sudo tail -n 60 /opt/sonarqube/logs/sonar.log
   sudo tail -n 100 /opt/sonarqube/logs/nohup.log
   ```

   If SonarQube stops because Elasticsearch reports `UnsupportedOperationException` about the Security Manager, check the Java runtime. For this 9.9 installation, Java 17 resolved the issue:

   ```bash
   /usr/lib/jvm/java-17-openjdk/bin/java -version
   ```

   If Java 17 is installed at that path, set it for the SonarQube service without changing the system-wide Java version:

   ```bash
   sudo systemctl edit sonarqube
   ```

   Add and save the following service override (adjust the paths if Java 17 is installed elsewhere):

   ```ini
   [Service]
   Environment="JAVA_HOME=/usr/lib/jvm/java-17-openjdk"
   Environment="SONAR_JAVA_PATH=/usr/lib/jvm/java-17-openjdk/bin/java"
   ```

2. Restart and verify SonarQube. Startup can take a minute:

   ```bash
   sudo systemctl restart sonarqube
   sudo systemctl status sonarqube --no-pager -l
   curl -s http://localhost:9000/api/system/status
   ```

   The API should return a status of `UP`. If it does not, review the logs above.

3. Generate a SonarQube token with permission to analyze the project. In Jenkins, open **Manage Jenkins > Credentials > System > Global credentials > Add Credentials**, choose **Secret text**, and set the ID to `sonarqube-token`. Do not commit or share the token.

4. In **Manage Jenkins > System > Global properties > Environment variables**, set `SONAR_HOST_URL` to `http://host.docker.internal:9000` for this same-VM Docker setup. The Jenkinsfile maps `host.docker.internal` to the Docker host. Do not use `localhost` here: inside the scanner container it refers to the container, not the VM. If the URL is missing, the scanner may attempt to contact SonarQube Cloud instead.

   If the scanner cannot connect, check the listening address and VM firewall:

   ```bash
   sudo ss -ltnp | grep ':9000'
   ```

   SonarQube must listen on an interface reachable from the Docker network. Limit access to trusted networks.

5. Rerun the Jenkins build and verify that the scanner reports the intended SonarQube server and `QUALITY GATE STATUS: PASSED`. SonarQube 9.9's Python analyzer may warn that Python 3.12 is analyzed as 3.10; address this through a compatible analyzer or server upgrade rather than treating it as full Python 3.12 analysis.

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
The checked-in rolling overlay uses a baseline image. Applying it directly after a Jenkins deployment can revert the app image; Jenkins renders the current build's image into a temporary overlay before applying it.

### Deployment strategies

- **Rolling update:** [k8s/overlays/rolling/](k8s/overlays/rolling/) keeps two replicas available while replacing pods. Roll back with `kubectl -n aceest rollout undo deployment/aceest-app`.
- **Blue-green:** [k8s/strategies/blue-green/](k8s/strategies/blue-green/) runs separate blue and green deployments. After green is healthy, switch the Service selector to `version: green`; switch it back to `version: blue` to roll back. The Jenkins pipeline can perform this switch after a successful rollout.
- **Canary:** [k8s/strategies/canary/](k8s/strategies/canary/) routes 90% to stable and 10% to canary through Istio. For rollback, set the VirtualService weights to 100% stable and 0% canary; Kubernetes rollout history can also restore the candidate Deployment.
- **Shadow:** [k8s/strategies/shadow/](k8s/strategies/shadow/) mirrors GET traffic to a shadow version while returning the primary version's response. Writes are intentionally not mirrored to avoid duplicate database changes. Roll back by removing the `mirror` rule or scaling the shadow Deployment to zero.
- **A/B testing:** [k8s/strategies/ab-testing/](k8s/strategies/ab-testing/) routes requests with `x-aceest-cohort: B` to variant B and all other requests to variant A. Roll back the B cohort to variant A in the VirtualService or restore the variant-B Deployment's prior image.

Install Istio in Minikube before applying the canary, shadow, or A/B manifests. For example, with `istioctl` installed, run `istioctl install --set profile=demo -y`. The gateway host in these manifests is `aceest.local`; configure local DNS or use port-forwarding to reach the Istio ingress gateway.

Update the blue/stable image tags in the strategy manifests to a previously published Docker Hub image, and the green/candidate tags to the release under test. Keep database changes backward-compatible while old and new versions run concurrently.

### Jenkins deployment

Add a Jenkins **Secret file** credential with ID `minikube-kubeconfig`, containing a kubeconfig usable by the Jenkins agent. The agent also needs `kubectl` on its PATH and network access to the cluster. Create the `aceest-db` secret above before deploying.

The job polls its configured SCM every five minutes. After a feature branch is merged into `main`, a successful main build publishes its version/build/commit image and deploys that exact image with the rolling strategy. `AUTO_DEPLOY_MAIN` defaults to true; set it to false for a manual build to opt out. Set `DEPLOY_TO_MINIKUBE=true` and select `DEPLOYMENT_STRATEGY` to manually deploy another strategy. PR builds do not publish or deploy. For a regular Pipeline job, configure SCM to track `main`; PR detection requires a Multibranch Pipeline.

After the merge, check Jenkins **Console Output** for the selected image, passing tests, push, and successful rollout. With a kubeconfig that can reach the same cluster, verify on the VM:

```bash
kubectl -n aceest get secret aceest-db
kubectl -n aceest rollout status deployment/aceest-app --timeout=180s
kubectl -n aceest get deployment aceest-app -o jsonpath='{.spec.template.spec.containers[?(@.name=="app")].image}{"\n"}'
kubectl -n aceest get pods,services
minikube service aceest-service -n aceest --url
```

Compare the deployment image with the image tag in that Jenkins build and Docker Hub, then open the service URL and check the displayed version. A failed rolling rollout can be reverted with `kubectl -n aceest rollout undo deployment/aceest-app`; the pipeline does not automatically undo it.

`VERSION` and the image tag do not create a Git tag. If a Git release tag is needed, create and push it on the merged `main` commit after verifying the build, rather than tagging the feature branch.

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