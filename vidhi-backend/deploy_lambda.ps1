# Windows deployment script for AWS Lambda via Container Image
# Usage: .\deploy_lambda.ps1

$ErrorActionPreference = "Stop"

$AWS_REGION = if ($env:AWS_REGION) { $env:AWS_REGION } else { "ap-south-1" }
$ECR_REPOSITORY = "vidhi-backend-lambda"
$IMAGE_TAG = "latest"
$LAMBDA_FUNCTION_NAME = "vidhi-backend"

Write-Host "`n Deploying VIDHI Backend to AWS Lambda (Container Image) in Region: $AWS_REGION" -ForegroundColor Green

# 1. Get AWS Account ID
try {
  $AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
  Write-Host "AWS Account: $AWS_ACCOUNT_ID"
}
catch {
  Write-Host " Error: AWS CLI not configured. Run 'aws configure' first." -ForegroundColor Red
  exit 1
}

# 2. Check/Create ECR repository
Write-Host "`n Checking ECR repository ($ECR_REPOSITORY)..." -ForegroundColor Cyan
try {
  aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION > $null 2>&1
}
catch {
  Write-Host "Creating ECR repository..."
  aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION > $null
}

# 3. Login to ECR
Write-Host "`n Logging in to ECR..." -ForegroundColor Cyan
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# 4. Build Docker image for Lambda
Write-Host "`n Building Docker image for Lambda..." -ForegroundColor Cyan
docker build -f Dockerfile.lambda -t "${ECR_REPOSITORY}:${IMAGE_TAG}" .

# 5. Tag and push image
Write-Host "`n Pushing image to ECR..." -ForegroundColor Cyan
$ECR_IMAGE_URI = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"
docker tag "${ECR_REPOSITORY}:${IMAGE_TAG}" $ECR_IMAGE_URI
docker push $ECR_IMAGE_URI

Write-Host "`n Image pushed to ECR: $ECR_IMAGE_URI" -ForegroundColor Green

# 6. Check/Create Lambda Function
Write-Host "`n Checking Lambda function ($LAMBDA_FUNCTION_NAME)..." -ForegroundColor Cyan
$LambdaExists = $false
try {
    aws lambda list-tags --resource "arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${LAMBDA_FUNCTION_NAME}" > $null 2>&1
    $LambdaExists = $true
} catch {
    $LambdaExists = $false
}

# Ensure wait time before updates to avoid Lambda rate limits on immediate create/update
if ($LambdaExists) {
    Write-Host "Updating existing Lambda function with new image..."
    aws lambda update-function-code --function-name $LAMBDA_FUNCTION_NAME --image-uri $ECR_IMAGE_URI --region $AWS_REGION > $null
    
    Write-Host "Waiting for update to complete..."
    aws lambda wait function-updated-v2 --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION
} else {
    Write-Host "Creating new Lambda function. NOTE: This requires appropriate execution role."
    Write-Host "We will create a basic execution role first..."
    
    $ROLE_NAME = "vidhi-lambda-execution-role"
    $TRUST_POLICY = '{"Version": "2012-10-17","Statement": [{"Effect": "Allow","Principal": {"Service": "lambda.amazonaws.com"},"Action": "sts:AssumeRole"}]}'
    
    try {
        aws iam get-role --role-name $ROLE_NAME > $null 2>&1
        Write-Host "Role $ROLE_NAME already exists."
    } catch {
        aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document $TRUST_POLICY > $null
        aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole > $null
        # Needs S3 and Bedrock access too usually. Adding broad access for ease in this phase, tighten later.
        aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess > $null
        aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess > $null
        aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess > $null
        Write-Host "Role created. Waiting 10s for IAM propagation..."
        Start-Sleep -Seconds 10
    }
    
    $ROLE_ARN = "arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
    
    Write-Host "Creating Lambda function..."
    aws lambda create-function --function-name $LAMBDA_FUNCTION_NAME `
        --package-type Image `
        --code "ImageUri=$ECR_IMAGE_URI" `
        --role $ROLE_ARN `
        --timeout 60 --memory-size 2048 `
        --region $AWS_REGION > $null

    Write-Host "Waiting for function creation to complete..."
    aws lambda wait function-active-v2 --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION
}

# 7. Add Function URL (simplest way to expose Lambda publicly)
Write-Host "`n Configuring Lambda Function URL..." -ForegroundColor Cyan
try {
    aws lambda get-function-url-config --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION > $null 2>&1
    Write-Host "Function URL already configured."
} catch {
    aws lambda create-function-url-config --function-name $LAMBDA_FUNCTION_NAME --auth-type NONE --cors '{"AllowOrigins": ["*"], "AllowMethods": ["*"], "AllowHeaders": ["*"]}' --region $AWS_REGION > $null
    
    # Add resource-based policy to allow public access to the URL
    aws lambda add-permission --function-name $LAMBDA_FUNCTION_NAME `
        --statement-id FunctionURLAllowPublicAccess `
        --action lambda:InvokeFunctionUrl `
        --principal "*" `
        --function-url-auth-type NONE `
        --region $AWS_REGION > $null
}

$URL_CONFIG = (aws lambda get-function-url-config --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION --query FunctionUrl --output text)

Write-Host "`n Deployment Complete!" -ForegroundColor Green
Write-Host "=========================================="
Write-Host "Your Backend is live at:" -ForegroundColor Yellow
Write-Host "$URL_CONFIG" -ForegroundColor Yellow
Write-Host "=========================================="
Write-Host "`n * Don't forget to update your frontend connected API URL (REACT_APP_API_URL / VITE_API_URL or client.ts) to this new URL."
