#!/bin/bash

# VIDHI Backend Deployment Script
# Usage: ./deploy.sh [app-runner|lambda|ec2]

set -e

DEPLOYMENT_TYPE=${1:-app-runner}
AWS_REGION=${AWS_REGION:-ap-south-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY=vidhi-backend
IMAGE_TAG=${2:-latest}

echo "🚀 Deploying VIDHI Backend to AWS ($DEPLOYMENT_TYPE)"
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"

# Build Docker image
echo "📦 Building Docker image..."
docker build -t $ECR_REPOSITORY:$IMAGE_TAG .

if [ "$DEPLOYMENT_TYPE" == "app-runner" ] || [ "$DEPLOYMENT_TYPE" == "ecs" ]; then
    # Create ECR repository if it doesn't exist
    echo "🏗️  Creating ECR repository..."
    aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null || \
        aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION

    # Login to ECR
    echo "🔐 Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

    # Tag and push image
    echo "📤 Pushing image to ECR..."
    docker tag $ECR_REPOSITORY:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

    echo "✅ Image pushed to ECR: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"

    if [ "$DEPLOYMENT_TYPE" == "app-runner" ]; then
        echo "🏃 Deploy to App Runner via AWS Console:"
        echo "   1. Go to AWS App Runner console"
        echo "   2. Create/Update service"
        echo "   3. Use image: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"
    fi

elif [ "$DEPLOYMENT_TYPE" == "lambda" ]; then
    echo "📦 Creating Lambda deployment package..."
    
    # Create deployment directory
    rm -rf lambda_package
    mkdir lambda_package
    cd lambda_package

    # Install dependencies
    pip install -r ../requirements.txt -t .

    # Copy application code
    cp -r ../*.py .
    cp -r ../services . 2>/dev/null || true
    cp -r ../speech . 2>/dev/null || true
    cp -r ../stores . 2>/dev/null || true
    cp -r ../processing . 2>/dev/null || true
    cp -r ../configs . 2>/dev/null || true
    cp -r ../llm_setup . 2>/dev/null || true

    # Create ZIP
    zip -r ../vidhi-lambda.zip . -x "*.pyc" -x "__pycache__/*"
    cd ..

    echo "✅ Lambda package created: vidhi-lambda.zip"
    echo "📤 Upload to Lambda via AWS Console or CLI"

elif [ "$DEPLOYMENT_TYPE" == "ec2" ]; then
    echo "🖥️  For EC2 deployment:"
    echo "   1. Launch EC2 instance (Ubuntu 22.04, t3.medium)"
    echo "   2. SSH into instance"
    echo "   3. Run: git clone <your-repo>"
    echo "   4. Run: cd vidhi-backend && ./setup-ec2.sh"

else
    echo "❌ Unknown deployment type: $DEPLOYMENT_TYPE"
    echo "Usage: ./deploy.sh [app-runner|lambda|ec2]"
    exit 1
fi

echo "✅ Deployment preparation complete!"
