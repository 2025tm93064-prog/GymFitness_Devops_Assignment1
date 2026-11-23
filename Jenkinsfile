pipeline {
    agent any

    options {
        disableConcurrentBuilds()
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    parameters {
        string(
            name: 'DOCKERHUB_REPO',
            defaultValue: '2025tm93064/acefitness',
            description: 'Docker Hub repository for versioned application images'
        )
        booleanParam(
            name: 'DEPLOY_TO_MINIKUBE',
            defaultValue: false,
            description: 'Manually deploy the selected strategy after publishing'
        )
        booleanParam(
            name: 'AUTO_DEPLOY_MAIN',
            defaultValue: true,
            description: 'Automatically deploy successful main builds using rolling updates'
        )
        choice(
            name: 'DEPLOYMENT_STRATEGY',
            choices: ['rolling', 'blue-green', 'canary', 'shadow', 'ab-testing'],
            description: 'Kubernetes deployment strategy to apply'
        )
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    def checkoutInfo = checkout scm
                    def branch = env.BRANCH_NAME ?: checkoutInfo.GIT_BRANCH
                    if (!branch && !env.CHANGE_ID && params.AUTO_DEPLOY_MAIN != false) {
                        error('Cannot identify the checked-out branch for automatic deployment.')
                    }
                    env.IS_MAIN_BUILD = (branch == 'main' || branch == 'origin/main').toString()
                }
            }
        }

        stage('SonarQube Analysis') {
            when {
                not {
                    changeRequest()
                }
            }
            steps {
                withCredentials([string(credentialsId: 'sonarqube-token', variable: 'SONAR_TOKEN')]) {
                    sh '''
                        docker run --rm \
                            --add-host=host.docker.internal:host-gateway \
                            -e SONAR_HOST_URL \
                            -e SONAR_TOKEN \
                            -v "$WORKSPACE:/usr/src" \
                            -w /usr/src \
                            sonarsource/sonar-scanner-cli
                    '''
                }
            }
        }

        stage('Build') {
            steps {
                script {
                    def version = readFile('VERSION').trim()
                    if (!(version ==~ 'v[0-9]+[.][0-9]+[.][0-9]+')) {
                        error('VERSION must contain a version like v1.4.0.')
                    }
                    def commit = sh(
                        returnStdout: true,
                        script: 'git rev-parse --short=12 HEAD'
                    ).trim()
                    env.IMAGE_TAG = "${version}-build-${env.BUILD_NUMBER}-${commit}"
                    echo "Building release image ${env.IMAGE_TAG}"
                }
                sh 'docker build --no-cache -t "aceest-fitness:$IMAGE_TAG" .'
            }
        }

        stage('Test') {
            steps {
                sh 'docker run --rm "aceest-fitness:$IMAGE_TAG" python -m pytest -q'
            }
        }

        stage('Publish to Docker Hub') {
            when {
                not {
                    changeRequest()
                }
            }
            steps {
                script {
                    if (!params.DOCKERHUB_REPO ||
                        params.DOCKERHUB_REPO == 'your-dockerhub-username/aceest-fitness') {
                        error('Set DOCKERHUB_REPO to your Docker Hub namespace/repository.')
                    }
                    def validRepo = (
                        params.DOCKERHUB_REPO ==~
                            '[a-z0-9]+(?:[._-][a-z0-9]+)*/[a-z0-9]+(?:[._-][a-z0-9]+)*'
                    )
                    if (!validRepo) {
                        error('DOCKERHUB_REPO must be a lowercase namespace/repository name.')
                    }
                    sh 'docker tag "aceest-fitness:$IMAGE_TAG" "$DOCKERHUB_REPO:$IMAGE_TAG"'
                }
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKERHUB_USER',
                    passwordVariable: 'DOCKERHUB_TOKEN'
                )]) {
                    sh '''
                        echo "$DOCKERHUB_TOKEN" | docker login --username "$DOCKERHUB_USER" --password-stdin
                        docker push "$DOCKERHUB_REPO:$IMAGE_TAG"
                    '''
                    script {
                        if (env.IS_MAIN_BUILD == 'true') {
                            sh 'docker tag "$DOCKERHUB_REPO:$IMAGE_TAG" "$DOCKERHUB_REPO:latest"'
                            sh 'docker push "$DOCKERHUB_REPO:latest"'
                        }
                    }
                }
            }
        }

        stage('Deploy to Minikube') {
            when {
                expression {
                    !env.CHANGE_ID && (
                        params.DEPLOY_TO_MINIKUBE ||
                        (params.AUTO_DEPLOY_MAIN != false && env.IS_MAIN_BUILD == 'true')
                    )
                }
            }
            steps {
                withCredentials([file(
                    credentialsId: 'minikube-kubeconfig',
                    variable: 'KUBECONFIG'
                )]) {
                    script {
                        def strategy = params.DEPLOY_TO_MINIKUBE ?
                            params.DEPLOYMENT_STRATEGY : 'rolling'
                        def deploymentByStrategy = [
                            'rolling': 'aceest-app',
                            'blue-green': 'aceest-green',
                            'canary': 'aceest-canary',
                            'shadow': 'aceest-shadow',
                            'ab-testing': 'aceest-variant-b'
                        ]
                        def overlay = strategy == 'rolling' ?
                            'k8s/overlays/rolling' : "k8s/strategies/${strategy}"
                        def deployment = deploymentByStrategy[strategy]

                        if (strategy == 'rolling') {
                            sh '''
                                set -eu
                                release_overlay=$(mktemp -d "$WORKSPACE/k8s/.release.XXXXXX")
                                trap 'rm -f "$release_overlay/kustomization.yaml"; rmdir "$release_overlay"' EXIT
                                cat > "$release_overlay/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../overlays/rolling
images:
  - name: 2025tm93064/acefitness
    newName: $DOCKERHUB_REPO
    newTag: $IMAGE_TAG
EOF
                                kubectl apply -k "$release_overlay"
                            '''
                        } else {
                            sh "kubectl apply -k ${overlay}"
                        }
                        try {
                            withEnv(["DEPLOYMENT_NAME=${deployment}"]) {
                                if (strategy != 'rolling') {
                                    sh '''
                                        kubectl -n aceest set image deployment/$DEPLOYMENT_NAME \
                                            app="$DOCKERHUB_REPO:$IMAGE_TAG"
                                    '''
                                }
                                sh 'kubectl -n aceest rollout status deployment/$DEPLOYMENT_NAME --timeout=180s'
                            }
                        } catch (deploymentError) {
                            if (strategy == 'canary') {
                                sh '''
                                    kubectl -n aceest patch virtualservice aceest-service \
                                        --type=json \
                                        -p='[{"op":"replace","path":"/spec/http/0/route/0/weight","value":100},{"op":"replace","path":"/spec/http/0/route/1/weight","value":0}]'
                                '''
                            }
                            if (strategy == 'ab-testing') {
                                sh '''
                                    kubectl -n aceest patch virtualservice aceest-service \
                                        --type=json \
                                        -p='[{"op":"replace","path":"/spec/http/0/route/0/destination/subset","value":"variant-a"}]'
                                '''
                            }
                            throw deploymentError
                        }

                        if (strategy == 'blue-green') {
                            try {
                                sh "kubectl -n aceest patch service aceest-service --type merge -p '{\"spec\":{\"selector\":{\"app\":\"aceest-fitness\",\"version\":\"green\"}}}'"
                            } catch (deploymentError) {
                                sh "kubectl -n aceest patch service aceest-service --type merge -p '{\"spec\":{\"selector\":{\"app\":\"aceest-fitness\",\"version\":\"blue\"}}}'"
                                throw deploymentError
                            }
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            sh 'docker rmi "aceest-fitness:$IMAGE_TAG" "$DOCKERHUB_REPO:$IMAGE_TAG" "$DOCKERHUB_REPO:latest" 2>/dev/null || true'
        }
    }
}
