#!/bin/bash
# AWS CloudShell Deployment Script for VIDHI Backend (Lambda Container Image)

set -e

# Configuration
AWS_REGION=${AWS_REGION:-ap-south-1}
ECR_REPOSITORY="vidhi-backend-lambda"
IMAGE_TAG="latest"
LAMBDA_FUNCTION_NAME="vidhi-backend"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🚀 Deploying VIDHI Backend to AWS Lambda from CloudShell"
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"

# 1. Clone or pull the latest code
if [ ! -d "vidhi" ]; then
    echo "📦 Cloning repository..."
    git clone https://github.com/Krish-kukreja/vidhi.git
    cd vidhi/vidhi-backend
else
    echo "📦 Repository already exists, pulling latest..."
    cd vidhi/vidhi-backend
    git pull
fi

# 2. Check/Create ECR repository
echo -e "\n🏗️  Checking ECR repository ($ECR_REPOSITORY)..."
if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION >/dev/null 2>&1; then
    echo "Creating ECR repository..."
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION >/dev/null
fi

# 3. Login to ECR
echo -e "\n🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# 4. Build Docker image
echo -e "\n📦 Building Docker image..."
docker build -f Dockerfile.lambda -t "${ECR_REPOSITORY}:${IMAGE_TAG}" .

# 5. Tag and push image
echo -e "\n📤 Pushing image to ECR..."
ECR_IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"
docker tag "${ECR_REPOSITORY}:${IMAGE_TAG}" $ECR_IMAGE_URI
docker push $ECR_IMAGE_URI

echo -e "\n✅ Image pushed to ECR: $ECR_IMAGE_URI"

# 6. Check/Create Lambda Function
echo -e "\n⚡ Checking Lambda function ($LAMBDA_FUNCTION_NAME)..."

if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION >/dev/null 2>&1; then
    echo "Updating existing Lambda function with new image..."
    aws lambda update-function-code --function-name $LAMBDA_FUNCTION_NAME --image-uri $ECR_IMAGE_URI --region $AWS_REGION >/dev/null
    
    echo "Waiting for update to complete..."
    aws lambda wait function-updated-v2 --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION
else
    echo "Creating new Lambda function..."
    
    ROLE_NAME="vidhi-lambda-execution-role"
    
    if ! aws iam get-role --role-name $ROLE_NAME >/dev/null 2>&1; then
        echo "Creating execution role ($ROLE_NAME)..."
        aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document '{"Version": "2012-10-17","Statement": [{"Effect": "Allow","Principal": {"Service": "lambda.amazonaws.com"},"Action": "sts:AssumeRole"}]}' >/dev/null
        aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole >/dev/null
        aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess >/dev/null
        aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess >/dev/null
        aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess >/dev/null
        echo "Waiting 10s for IAM propagation..."
        sleep 10
    fi
    
    ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
    
    echo "Creating Lambda function..."
    aws lambda create-function \
        --function-name $LAMBDA_FUNCTION_NAME \
        --package-type Image \
        --code "ImageUri=$ECR_IMAGE_URI" \
        --role $ROLE_ARN \
        --timeout 60 \
        --memory-size 2048 \
        --region $AWS_REGION >/dev/null

    echo "Waiting for function creation to complete..."
    aws lambda wait function-active-v2 --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION
fi

# 7. Add Function URL
echo -e "\n🌐 Configuring Lambda Function URL..."
if ! aws lambda get-function-url-config --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION >/dev/null 2>&1; then
    aws lambda create-function-url-config --function-name $LAMBDA_FUNCTION_NAME --auth-type NONE --cors '{"AllowOrigins": ["*"], "AllowMethods": ["*"], "AllowHeaders": ["*"]}' --region $AWS_REGION >/dev/null
    
    aws lambda add-permission --function-name $LAMBDA_FUNCTION_NAME \
        --statement-id FunctionURLAllowPublicAccess \
        --action lambda:InvokeFunctionUrl \
        --principal "*" \
        --function-url-auth-type NONE \
        --region $AWS_REGION >/dev/null
fi

URL_CONFIG=$(aws lambda get-function-url-config --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION --query FunctionUrl --output text)

echo -e "\n🎉 Deployment Complete!"
echo "=========================================="
echo -e "Your Backend is live at:\n\e[33m$URL_CONFIG\e[0m"
echo "=========================================="
echo "Use this URL in your frontend client.ts configuration."
