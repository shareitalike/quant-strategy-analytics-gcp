pipeline {
    agent any

    environment {
        APP_NAME        = "quant-dashboard"
        IMAGE_NAME      = "quant-dashboard:latest"
        CONTAINER_NAME  = "quant-dashboard-app"

        // Streamlit runs INSIDE container on 8080
        CONTAINER_PORT  = "8080"

        // Jenkins already uses 8080 → expose app on 8501
        HOST_PORT       = "8501"

        // Mounted GCS / local data directory
        DATA_PATH       = "/home/alvigeorge3/quant-dashboard-files"
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {

        stage('Checkout Code') {
            steps {
                echo "📥 Checking out source code"
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
                echo "🛑 Stopping existing container if running"
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
                  -v ${DATA_PATH}:/app/data \
                  ${IMAGE_NAME}
                """
            }
        }

        stage('Health Check') {
            steps {
                echo "🩺 Verifying application health"
                sh """
                sleep 20
                curl -f http://127.0.0.1:${HOST_PORT} || exit 1
                """
            }
        }
    }

    post {
        always {
            echo "🧹 Cleaning up unused Docker containers (safe cleanup)"
            sh """
            docker container prune -f || true
            docker builder prune -f || true
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
