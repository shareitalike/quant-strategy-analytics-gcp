pipeline {
    agent any

    environment {
        IMAGE_NAME = "quant-dashboard"
        CONTAINER_NAME = "quant-dashboard-container"
        // HOST_DATA_PATH must be created/mounted on the VM before running this pipeline
        HOST_DATA_PATH = "/home/quant_user/quant-dashboard-files" 
    }

    stages {
        stage('Build') {
            steps {
                script {
                    echo 'Building Docker Image...'
                    // Build the image tagged with the build number
                    sh "docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} ."
                    // Also tag as latest
                    sh "docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest"
                }
            }
        }

        stage('Deploy') {
            steps {
                script {
                    echo 'Deploying Container...'
                    
                    // Stop running container if it exists
                    sh "docker stop ${CONTAINER_NAME} || true"
                    sh "docker rm ${CONTAINER_NAME} || true"

                    // specific run command for low-memory environments (optional flags can be added)
                    sh """
                        docker run -d \
                        --name ${CONTAINER_NAME} \
                        -p 8501:8501 \
                        -e DATA_PATH="/app/data" \
                        -v ${HOST_DATA_PATH}:/app/data \
                        --restart unless-stopped \
                        ${IMAGE_NAME}:latest
                    """
                }
            }
        }

        stage('Clean Up') {
            steps {
                script {
                    echo 'Pruning old images to save disk space...'
                    // -f forces cleanup without prompt
                    sh "docker image prune -f"
                }
            }
        }
    }
}
