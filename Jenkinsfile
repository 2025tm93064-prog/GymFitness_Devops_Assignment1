pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('SonarQube Analysis') {
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

        stage('Clean Build') {
            steps {
                sh 'docker build --no-cache -t aceest-fitness:${BUILD_NUMBER} .'
            }
        }

        stage('Test') {
            steps {
                sh 'docker run --rm aceest-fitness:${BUILD_NUMBER} python -m pytest'
            }
        }
    }

    post {
        always {
            sh 'docker rmi aceest-fitness:${BUILD_NUMBER} || true'
        }
    }
}
