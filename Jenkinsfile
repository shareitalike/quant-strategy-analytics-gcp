pipeline {
    agent any

    environment {
        APP_NAME        = "quant-dashboard"
        IMAGE_NAME      = "quant-dashboard:latest"
        CONTAINER_NAME  = "quant-dashboard-app"

        // Container listens on 8080, host exposes 8501
        CONTAINER_PORT  = "8080"
        HOST_PORT       = "8501"

        // gcsfuse mount on VM (already mounted)
        DATA_PATH       = "/mnt/quant-dashboard-files"
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {

        stage('Checkout Code') {
            steps {
                echo "📥 Checking out source code from Git"
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                echo "🐳 Building Docker image"
                sh """
                  docker build -t ${IMAGE_NAME} .
                """
            }
        }

        stage('Stop Old Container (if any)') {
            steps {
                echo "🛑 Stopping old container if running"
                sh """
                  docker stop ${CONTAINER_NAME} || true
                  docker rm ${CONTAINER_NAME} || true
                """
            }
        }

        stage('Run Application Container') {
            steps {
                echo "🚀 Starting Streamlit container"
                sh """
                  docker run -d \
                    --name ${CONTAINER_NAME} \
                    -p ${HOST_PORT}:${CONTAINER_PORT} \
                    -e DATA_PATH=/app/data \
                    --mount type=bind,source=${DATA_PATH},target=/app/data \
                    ${IMAGE_NAME}
                """
            }
        }

        stage('Health Check') {
            steps {
                echo "🩺 Performing health check"
                sh """
                  sleep 10
                  curl -f http://localhost:${HOST_PORT} || exit 1
                """
            }
        }
    }

    post {
        always {
            echo "🧹 Cleaning unused Docker resources (safe for free tier)"
            sh """
              docker container prune -f || true
              docker image prune -f || true
            """
        }

        success {
            echo "✅ Deployment successful!"
            echo "🌍 App available at: http://<VM_EXTERNAL_IP>:${HOST_PORT}"
        }

        failure {
            echo "❌ Deployment failed. Check logs."
        }
    }
}
