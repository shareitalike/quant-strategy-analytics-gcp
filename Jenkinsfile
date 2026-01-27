pipeline {
    agent any

    environment {
        // -----------------------------
        // App & Image
        // -----------------------------
        APP_NAME   = "quant-dashboard"
        PROJECT_ID = "<YOUR_GCP_PROJECT_ID>"
        REGION     = "us-central1"

        IMAGE_URI  = "gcr.io/${PROJECT_ID}/${APP_NAME}"

        // -----------------------------
        // Runtime Configuration
        // -----------------------------
        DATA_MODE  = "GCS"
        GCS_BUCKET = "quant-dashboard-data"
        GCS_PREFIX = "strategies/"
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

        stage('Build & Push Image') {
            steps {
                echo "🐳 Building and pushing image to GCR"
                sh """
                  gcloud builds submit \
                    --tag ${IMAGE_URI}
                """
            }
        }

        stage('Deploy to Cloud Run') {
            steps {
                echo "🚀 Deploying to Cloud Run"
                sh """
                  gcloud run deploy ${APP_NAME} \
                    --image ${IMAGE_URI} \
                    --region ${REGION} \
                    --platform managed \
                    --allow-unauthenticated \
                    --set-env-vars \
                      DATA_MODE=${DATA_MODE},\
                      GCS_BUCKET=${GCS_BUCKET},\
                      GCS_PREFIX=${GCS_PREFIX}
                """
            }
        }

        stage('Post-Deploy Smoke Test') {
            steps {
                echo "🩺 Running Cloud Run smoke test"
                sh """
                  SERVICE_URL=$(gcloud run services describe ${APP_NAME} \
                    --region ${REGION} \
                    --format='value(status.url)')

                  echo "Service URL: $SERVICE_URL"
                  curl -f $SERVICE_URL || exit 1
                """
            }
        }
    }

    post {
        success {
            echo "✅ Deployment successful!"
            echo "🌍 Cloud Run service deployed:"
            sh """
              gcloud run services describe ${APP_NAME} \
                --region ${REGION} \
                --format='value(status.url)'
            """
        }

        failure {
            echo "❌ Deployment failed. Check Jenkins logs."
        }
    }
}
