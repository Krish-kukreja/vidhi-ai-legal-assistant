# Complete Lambda + API Gateway Deployment Script
# Usage: .\deploy-lambda-complete.ps1 -BhashiniApiKey "your_key"

param(
    [string]$BhashiniApiKey = $env:BHASHINI_API_KEY,
    [string]$Region = "ap-south-1"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying VIDHI Backend to Lambda + API Gateway" -ForegroundColor Green
Write-Host "Region: $Region`n"

if (-not $BhashiniApiKey) {
    Write-Host "⚠️  Warning: BHASHINI_API_KEY not provided" -ForegroundColor Yellow
    $BhashiniApiKey = Read-Host "Enter Bhashini API Key (or press Enter to skip)"
}

# 1. Create deployment package
Write-Host "`n📦 Step 1: Creating deployment package..." -ForegroundColor Cyan
.\deploy.ps1 lambda

if (-not (Test-Path "vidhi-lambda.zip")) {
    Write-Host "❌ Error: vidhi-lambda.zip not created" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Deployment package created: vidhi-lambda.zip"

# 2. Get AWS Account ID
Write-Host "`n🔍 Step 2: Getting AWS Account ID..." -ForegroundColor Cyan
try {
    $AWS_ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
    Write-Host "✅ AWS Account: $AWS_ACCOUNT_ID"
} catch {
    Write-Host "❌ Error: AWS CLI not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# 3. Create IAM role (if doesn't exist)
Write-Host "`n🔐 Step 3: Setting up IAM role..." -ForegroundColor Cyan
try {
    $existingRole = aws iam get-role --role-name vidhi-lambda-execution-role 2>$null
    Write-Host "✅ IAM role already exists"
} catch {
    Write-Host "Creating IAM role..."
    
    $trustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
"@
    $trustPolicy | Out-File -FilePath trust-policy.json -Encoding utf8

    aws iam create-role --role-name vidhi-lambda-execution-role --assume-role-policy-document file://trust-policy.json | Out-Null
    
    Write-Host "Attaching policies..."
    aws iam attach-role-policy --role-name vidhi-lambda-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    aws iam attach-role-policy --role-name vidhi-lambda-execution-role --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
    aws iam attach-role-policy --role-name vidhi-lambda-execution-role --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
    
    Write-Host "Waiting for role to propagate..."
    Start-Sleep -Seconds 10
    Write-Host "✅ IAM role created"
}

$ROLE_ARN = "arn:aws:iam::${AWS_ACCOUNT_ID}:role/vidhi-lambda-execution-role"

# 4. Create or update Lambda function
Write-Host "`n⚡ Step 4: Deploying Lambda function..." -ForegroundColor Cyan
try {
    $existingFunction = aws lambda get-function --function-name vidhi-backend --region $Region 2>$null
    Write-Host "Updating existing function..."
    aws lambda update-function-code `
        --function-name vidhi-backend `
        --zip-file fileb://vidhi-lambda.zip `
        --region $Region | Out-Null
    
    Write-Host "Updating configuration..."
    aws lambda update-function-configuration `
        --function-name vidhi-backend `
        --environment "Variables={AWS_REGION=$Region,BHASHINI_API_KEY=$BhashiniApiKey,LOG_LEVEL=INFO}" `
        --region $Region | Out-Null
    
    Write-Host "✅ Lambda function updated"
} catch {
    Write-Host "Creating new function..."
    aws lambda create-function `
        --function-name vidhi-backend `
        --runtime python3.12 `
        --role $ROLE_ARN `
        --handler app.handler `
        --zip-file fileb://vidhi-lambda.zip `
        --timeout 30 `
        --memory-size 1024 `
        --region $Region `
        --environment "Variables={AWS_REGION=$Region,BHASHINI_API_KEY=$BhashiniApiKey,LOG_LEVEL=INFO}" | Out-Null
    
    Write-Host "✅ Lambda function created"
}

# 5. Create API Gateway
Write-Host "`n🌐 Step 5: Setting up API Gateway..." -ForegroundColor Cyan
$API_ID = aws apigatewayv2 get-apis --region $Region --query "Items[?Name=='vidhi-api'].ApiId" --output text

if (-not $API_ID -or $API_ID -eq "") {
    Write-Host "Creating new API Gateway..."
    
    $API_RESPONSE = aws apigatewayv2 create-api `
        --name vidhi-api `
        --protocol-type HTTP `
        --region $Region | ConvertFrom-Json
    
    $API_ID = $API_RESPONSE.ApiId
    Write-Host "API ID: $API_ID"
    
    $LAMBDA_ARN = aws lambda get-function `
        --function-name vidhi-backend `
        --region $Region `
        --query 'Configuration.FunctionArn' `
        --output text
    
    Write-Host "Creating integration..."
    $INTEGRATION_RESPONSE = aws apigatewayv2 create-integration `
        --api-id $API_ID `
        --integration-type AWS_PROXY `
        --integration-uri $LAMBDA_ARN `
        --payload-format-version 2.0 `
        --region $Region | ConvertFrom-Json
    
    $INTEGRATION_ID = $INTEGRATION_RESPONSE.IntegrationId
    
    Write-Host "Creating routes..."
    aws apigatewayv2 create-route `
        --api-id $API_ID `
        --route-key 'ANY /{proxy+}' `
        --target "integrations/$INTEGRATION_ID" `
        --region $Region | Out-Null
    
    aws apigatewayv2 create-route `
        --api-id $API_ID `
        --route-key '$default' `
        --target "integrations/$INTEGRATION_ID" `
        --region $Region | Out-Null
    
    Write-Host "Creating stage..."
    aws apigatewayv2 create-stage `
        --api-id $API_ID `
        --stage-name prod `
        --auto-deploy `
        --region $Region | Out-Null
    
    Write-Host "Granting API Gateway permission to invoke Lambda..."
    aws lambda add-permission `
        --function-name vidhi-backend `
        --statement-id apigateway-invoke `
        --action lambda:InvokeFunction `
        --principal apigateway.amazonaws.com `
        --source-arn "arn:aws:execute-api:${Region}:${AWS_ACCOUNT_ID}:${API_ID}/*/*" `
        --region $Region 2>$null | Out-Null
    
    Write-Host "✅ API Gateway created"
} else {
    Write-Host "✅ API Gateway already exists (ID: $API_ID)"
}

$API_ENDPOINT = "https://${API_ID}.execute-api.${Region}.amazonaws.com/prod"

# 6. Test deployment
Write-Host "`n🧪 Step 6: Testing deployment..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

try {
    $response = Invoke-RestMethod -Uri "$API_ENDPOINT/health" -Method Get -TimeoutSec 10
    Write-Host "✅ Health check passed!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json)
} catch {
    Write-Host "⚠️  Health check failed (this is normal for first deployment)" -ForegroundColor Yellow
    Write-Host "   The API may need a few minutes to become fully available"
}

# Summary
Write-Host "`n" + ("="*60) -ForegroundColor Green
Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host ("="*60) -ForegroundColor Green

Write-Host "`n📍 API Endpoint:" -ForegroundColor Cyan
Write-Host "   $API_ENDPOINT" -ForegroundColor Yellow

Write-Host "`n🧪 Test Commands:" -ForegroundColor Cyan
Write-Host "   # PowerShell:"
Write-Host "   Invoke-RestMethod -Uri '$API_ENDPOINT/health'"
Write-Host ""
Write-Host "   # Curl:"
Write-Host "   curl $API_ENDPOINT/health"

Write-Host "`n📊 View Logs:" -ForegroundColor Cyan
Write-Host "   aws logs tail /aws/lambda/vidhi-backend --follow --region $Region"

Write-Host "`n🔄 Update Function:" -ForegroundColor Cyan
Write-Host "   .\deploy.ps1 lambda"
Write-Host "   aws lambda update-function-code --function-name vidhi-backend --zip-file fileb://vidhi-lambda.zip --region $Region"

Write-Host "`n💰 Estimated Cost:" -ForegroundColor Cyan
Write-Host "   ~`$5-10/month for 1M requests"
Write-Host "   Pay only for what you use!"

Write-Host "`n" + ("="*60) -ForegroundColor Green
