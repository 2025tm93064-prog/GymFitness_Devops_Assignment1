# ACEest Fitness & Gym - Assignment 2 Report

> Draft for completion after deployment. Replace every bracketed item with evidence from your own Jenkins, SonarQube, Docker Hub, and Minikube runs. Do not report unverified results.

## 1. CI/CD architecture

The application is maintained in GitHub and validated by GitHub Actions and Jenkins. GitHub Actions checks Python syntax, lint, Docker build, and Pytest. Jenkins checks out the selected branch, runs SonarQube analysis and its quality gate, builds the Docker image, runs Pytest inside the image, and publishes successful images to Docker Hub with a Git release tag or Jenkins build tag. Jenkins can optionally deploy the published image to Minikube.

The Flask application uses SQLAlchemy with SQLite for local development and PostgreSQL for Kubernetes. PostgreSQL uses a persistent volume claim. Kubernetes readiness and liveness probes use the application health endpoints. The rolling-update configuration is provided separately from blue-green, canary, shadow, and A/B routing configurations.

**Architecture evidence:** [Add a pipeline diagram or describe the actual configured services, Jenkins agent, registry, cluster, and network path.]

## 2. Implementation and deployment strategies

- **Rolling update:** [Record deployment name, replica count, rollout command, and result.]
- **Blue-green:** [Record the active color, Service selector switch, validation, and rollback check.]
- **Canary:** [Record Istio traffic weights, test duration, observations, and promotion or rollback.]
- **Shadow:** [Record the mirrored read-only request test and comparison approach.]
- **A/B testing:** [Record the cohort header used and how the two variants were compared.]

Images used: **[Docker Hub repository and version tags]**  
Running endpoint: **[Minikube or cluster endpoint]**  
Test result: **[Jenkins build URL and Pytest result]**  
SonarQube result: **[Project link and quality-gate status]**

## 3. Challenges and mitigations

The original application stored data in a local SQLite database. That is unsuitable for independent replicas that need consistent shared state, so the app was adapted to use PostgreSQL in Kubernetes while retaining SQLite for local development and tests. Database credentials are created as a Kubernetes Secret and are not stored in the repository. Shadow routing mirrors only GET requests so write requests do not create duplicate database changes.

**Additional challenges and mitigations observed during the actual deployment:** [Describe issues you encountered and what resolved them.]

## 4. Outcomes

**Complete after running the pipeline and deployment:** [Summarize verified automated checks, published images, strategy demonstrations, endpoint availability, and any rollback test. Include screenshots or links as evidence.]
