pipeline {
    agent any
    
    environment {
        AWS_REGION     = 'us-east-1'
        AWS_ACCOUNT_ID = credentials('aws-account-id')
        ECR_REGISTRY   = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        IMAGE_NAME     = 'product-service'
    }
    
    stages {
        
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.IMAGE_TAG = "${env.BUILD_NUMBER}-${gitCommit().take(7)}"
                    echo "🏷️ Image tag: ${env.IMAGE_TAG}"
                }
            }
        }
        
        stage('Docker Build') {
            steps {
                sh """
                    echo "🔨 Building..."
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                """
            }
        }
        
        stage('Trivy Scan') {
            steps {
                sh """
                    echo "🔍 Scanning..."
                    trivy image --exit-code 1 \
                      --severity HIGH,CRITICAL \
                      --ignore-unfixed \
                      ${IMAGE_NAME}:${IMAGE_TAG}
                    echo "✅ Clean"
                """
            }
        }
        
        stage('Push to ECR') {
            steps {
                sh """
                    echo "⬆️ Pushing..."
                    aws ecr get-login-password --region ${AWS_REGION} | \
                      docker login --username AWS --password-stdin ${ECR_REGISTRY}
                    docker push ${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                """
            }
        }
        
        stage('Deploy') {
            steps {
                sh """
                    echo "🚀 Deploying..."
                    kubectl delete deployment ${IMAGE_NAME} --ignore-not-found
                    kubectl create deployment ${IMAGE_NAME} \
                      --image=${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} \
                      --port=8000
                    kubectl rollout status deployment/${IMAGE_NAME} --timeout=120s
                """
            }
        }
    }
    
    post {
        success { echo "🎉 Done! ${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}" }
        failure { echo "❌ Failed" }
        always { sh "docker rmi ${IMAGE_NAME}:${IMAGE_TAG} || true" }
    }
}