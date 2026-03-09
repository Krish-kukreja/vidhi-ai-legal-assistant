# Simple Lambda Deployment Script
# Usage: .\deploy-lambda-simple.ps1 -BhashiniApiKey "your_key"

param(
    [string]$BhashiniApiKey = $env:BHASHINI_API_KEY,
    [string]$Region = "ap-south-1"
)

$ErrorActionPreference = "Continue"  # Don't stop on errors

Write-Host "🚀 Deploying VIDHI Backend to Lambda" -ForegroundColor Green

# 1. Create deployment package
Write-Host "`n📦 Step 1: Creating deployment package..." -ForegroundColor Cyan
.\deploy.ps1 lambda

if (-not (Test-Path "vidhi-lambda.zip")) {
    Write-Host "❌ Error: vidhi-lambda.zip not created" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Package created: vidhi-lambda.zip"

# 2. Get AWS Account ID
Write-Host "`n🔍 Step 2: Getting AWS Account..." -ForegroundColor Cyan
$AWS_ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
Write-Host "✅ Account: $AWS_ACCOUNT_ID"

# 3. Check if IAM role exists
Write-Host "`n🔐 Step 3: Checking IAM role..." -ForegroundColor Cyan
$ROLE_ARN = "arn:aws:iam::${AWS_ACCOUNT_ID}:role/vidhi-lambda-execution-role"

$roleExists = $false
try {
    aws iam get-role --role-name vidhi-lambda-execution-role 2>$null | Out-Null
    $roleExists = $true
    Write-Host "✅ IAM role exists"
} catch {
    Write-Host "❌ IAM role not found" -ForegroundColor Red
    Write-Host "Please create 'vidhi-lambda-execution-role' in AWS Console first" -ForegroundColor Yellow
    exit 1
}

# 4. Check if Lambda function exists
Write-Host "`n⚡ Step 4: Checking Lambda function..." -ForegroundColor Cyan
$functionExists = $false
try {
    aws lambda get-function --function-name vidhi-backend --region $Region 2>$null | Out-Null
    $functionExists = $true
    Write-Host "Function exists - will update"
} catch {
    Write-Host "Function doesn't exist - will create"
}

# 5. Create or update Lambda function
if ($functionExists) {
    Write-Host "`n📤 Updating Lambda function..." -ForegroundColor Cyan
    aws lambda update-function-code `
        --function-name vidhi-backend `
        --zip-file fileb://vidhi-lambda.zip `
        --region $Region
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Function updated successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Update failed" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "`n📤 Creating Lambda function..." -ForegroundColor Cyan
    aws lambda create-function `
        --function-name vidhi-backend `
        --runtime python3.12 `
        --role $ROLE_ARN `
        --handler app.handler `
        --zip-file fileb://vidhi-lambda.zip `
        --timeout 30 `
        --memory-size 1024 `
        --region $Region `
        --environment "Variables={AWS_REGION=$Region,BHASHINI_API_KEY=$BhashiniApiKey,LOG_LEVEL=INFO}"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Function created successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Creation failed" -ForegroundColor Red
        exit 1
    }
}

# 6. Wait for function to be ready and get Lambda ARN
Write-Host "`n🔗 Getting Lambda ARN..." -ForegroundColor Cyan
Start-Sleep -Seconds 3  # Wait for function to be fully created

$LAMBDA_ARN = $null
$retries = 0
while ($retries -lt 5 -and -not $LAMBDA_ARN) {
    try {
        $LAMBDA_ARN = aws lambda get-function `
            --function-name vidhi-backend `
            --region $Region `
            --query 'Configuration.FunctionArn' `
            --output text 2>$null
        
        if ($LAMBDA_ARN) {
            Write-Host "Lambda ARN: $LAMBDA_ARN"
            break
        }
    } catch {
        Write-Host "Waiting for function to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        $retries++
    }
}

if (-not $LAMBDA_ARN) {
    Write-Host "❌ Could not get Lambda ARN" -ForegroundColor Red
    Write-Host "The function may have been created. Check AWS Console." -ForegroundColor Yellow
    exit 1
}

# 7. Check if API Gateway exists
Write-Host "`n🌐 Step 5: Checking API Gateway..." -ForegroundColor Cyan
$API_ID = aws apigatewayv2 get-apis --region $Region --query "Items[?Name=='vidhi-api'].ApiId" --output text

if (-not $API_ID -or $API_ID -eq "") {
    Write-Host "Creating API Gateway..."
    
    # Create API
    $API_RESPONSE = aws apigatewayv2 create-api `
        --name vidhi-api `
        --protocol-type HTTP `
        --region $Region | ConvertFrom-Json
    
    $API_ID = $API_RESPONSE.ApiId
    Write-Host "API ID: $API_ID"
    
    # Create integration
    $INTEGRATION_RESPONSE = aws apigatewayv2 create-integration `
        --api-id $API_ID `
        --integration-type AWS_PROXY `
        --integration-uri $LAMBDA_ARN `
        --payload-format-version 2.0 `
        --region $Region | ConvertFrom-Json
    
    $INTEGRATION_ID = $INTEGRATION_RESPONSE.IntegrationId
    Write-Host "Integration ID: $INTEGRATION_ID"
    
    # Create routes
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
    
    # Create stage
    aws apigatewayv2 create-stage `
        --api-id $API_ID `
        --stage-name prod `
        --auto-deploy `
        --region $Region | Out-Null
    
    # Grant permission
    aws lambda add-permission `
        --function-name vidhi-backend `
        --statement-id apigateway-invoke-$(Get-Random) `
        --action lambda:InvokeFunction `
        --principal apigateway.amazonaws.com `
        --source-arn "arn:aws:execute-api:${Region}:${AWS_ACCOUNT_ID}:${API_ID}/*/*" `
        --region $Region 2>$null | Out-Null
    
    Write-Host "✅ API Gateway created" -ForegroundColor Green
} else {
    Write-Host "✅ API Gateway exists (ID: $API_ID)" -ForegroundColor Green
}

# 8. Display results
$API_ENDPOINT = "https://${API_ID}.execute-api.${Region}.amazonaws.com/prod"

Write-Host "`n" + ("="*70) -ForegroundColor Green
Write-Host "✅ DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host ("="*70) -ForegroundColor Green

Write-Host "`n📍 Your API Endpoint:" -ForegroundColor Cyan
Write-Host "   $API_ENDPOINT" -ForegroundColor Yellow

Write-Host "`n🧪 Test Commands:" -ForegroundColor Cyan
Write-Host "   Invoke-RestMethod -Uri '$API_ENDPOINT/health'"
Write-Host "   curl $API_ENDPOINT/health"

Write-Host "`n📊 View Logs:" -ForegroundColor Cyan
Write-Host "   aws logs tail /aws/lambda/vidhi-backend --follow --region $Region"

Write-Host "`n🔄 To Update Code:" -ForegroundColor Cyan
Write-Host "   1. Make your changes"
Write-Host "   2. Run: .\deploy-lambda-simple.ps1 -BhashiniApiKey 'your_key'"

Write-Host "`n" + ("="*70) -ForegroundColor Green
