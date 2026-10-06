pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
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
