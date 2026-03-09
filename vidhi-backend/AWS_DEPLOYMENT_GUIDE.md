# AWS Deployment Guide for VIDHI Backend

## Overview

This guide covers multiple AWS deployment options for your FastAPI backend, from simplest to most scalable.

## Deployment Options Comparison

| Option | Complexity | Cost | Scalability | Best For |
|--------|-----------|------|-------------|----------|
| **EC2** | Medium | $5-50/mo | Manual | Full control, learning |
| **Elastic Beanstalk** | Low | $10-100/mo | Auto | Quick deployment |
| **Lambda + API Gateway** | Medium | Pay-per-use | Auto | Serverless, cost-effective |
| **ECS Fargate** | High | $20-200/mo | Auto | Production, containers |
| **App Runner** | Low | $5-50/mo | Auto | Easiest, modern |

## Recommended: AWS App Runner (Easiest)

AWS App Runner is the simplest way to deploy containerized applications.

### Prerequisites

1. AWS Account
2. AWS CLI installed
3. Docker installed

### Step 1: Create Dockerfile

Create `vidhi-backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 2: Create .dockerignore

Create `vidhi-backend/.dockerignore`:

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.gitignore
.mypy_cache
.pytest_cache
.hypothesis
chroma_db/
*.db
*.sqlite
.env
```

### Step 3: Test Docker Locally

```bash
cd vidhi-backend

# Build image
docker build -t vidhi-backend .

# Run container
docker run -p 8000:8000 \
  -e AWS_REGION=ap-south-1 \
  -e BHASHINI_API_KEY=your_key \
  vidhi-backend

# Test
curl http://localhost:8000/health
```

### Step 4: Deploy to AWS App Runner

```bash
# Install AWS CLI
pip install awscli

# Configure AWS credentials
aws configure

# Create ECR repository
aws ecr create-repository --repository-name vidhi-backend --region ap-south-1

# Login to ECR
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com

# Tag and push image
docker tag vidhi-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/vidhi-backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/vidhi-backend:latest
```

### Step 5: Create App Runner Service (AWS Console)

1. Go to AWS App Runner console
2. Click "Create service"
3. Choose "Container registry" → "Amazon ECR"
4. Select your image
5. Configure:
   - Port: 8000
   - Environment variables: Add your API keys
   - CPU: 1 vCPU
   - Memory: 2 GB
6. Click "Create & deploy"

**Done!** Your API will be available at: `https://xxxxx.ap-south-1.awsapprunner.com`

---

## Option 2: AWS Lambda + API Gateway (Serverless)

Best for cost optimization and auto-scaling.

### Step 1: Install Mangum (Already in requirements.txt)

Mangum is already included in your `app.py`:

```python
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None
```

### Step 2: Create Lambda Deployment Package

**Using PowerShell (Windows):**

```powershell
cd vidhi-backend

# Run the deployment script
.\deploy.ps1 lambda

# This creates vidhi-lambda.zip
```

**Or manually:**

```powershell
# Create deployment directory
New-Item -ItemType Directory -Path lambda_package -Force
Set-Location lambda_package

# Install dependencies
pip install -r ..\requirements.txt -t .

# Copy application code
Copy-Item ..\*.py .
Copy-Item -Recurse ..\services . -ErrorAction SilentlyContinue
Copy-Item -Recurse ..\speech . -ErrorAction SilentlyContinue
Copy-Item -Recurse ..\stores . -ErrorAction SilentlyContinue
Copy-Item -Recurse ..\processing . -ErrorAction SilentlyContinue
Copy-Item -Recurse ..\configs . -ErrorAction SilentlyContinue
Copy-Item -Recurse ..\llm_setup . -ErrorAction SilentlyContinue

# Create ZIP
Compress-Archive -Path * -DestinationPath ..\vidhi-lambda.zip -Force
Set-Location ..

Write-Host "✅ Lambda package created: vidhi-lambda.zip"
```

**Using Bash (Linux/Mac):**

```bash
cd vidhi-backend

# Run the deployment script
./deploy.sh lambda

# Or manually create package
mkdir lambda_package && cd lambda_package
pip install -r ../requirements.txt -t .
cp -r ../*.py ../services ../speech ../stores ../processing ../configs ../llm_setup .
zip -r ../vidhi-lambda.zip .
cd ..
```

### Step 3: Create IAM Role for Lambda

**PowerShell:**

```powershell
# Create trust policy file
@"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@ | Out-File -FilePath trust-policy.json -Encoding utf8

# Create IAM role
aws iam create-role `
  --role-name vidhi-lambda-execution-role `
  --assume-role-policy-document file://trust-policy.json

# Attach basic Lambda execution policy
aws iam attach-role-policy `
  --role-name vidhi-lambda-execution-role `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Attach Bedrock access policy
aws iam attach-role-policy `
  --role-name vidhi-lambda-execution-role `
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Attach S3 access policy (for audio storage)
aws iam attach-role-policy `
  --role-name vidhi-lambda-execution-role `
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Get the role ARN (save this for next step)
$ROLE_ARN = aws iam get-role --role-name vidhi-lambda-execution-role --query 'Role.Arn' --output text
Write-Host "Role ARN: $ROLE_ARN"

# Wait for role to be ready
Start-Sleep -Seconds 10
```

### Step 4: Deploy Lambda Function

**PowerShell:**

```powershell
# Get your AWS account ID
$AWS_ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$ROLE_ARN = "arn:aws:iam::${AWS_ACCOUNT_ID}:role/vidhi-lambda-execution-role"

# Create Lambda function
aws lambda create-function `
  --function-name vidhi-backend `
  --runtime python3.12 `
  --role $ROLE_ARN `
  --handler app.handler `
  --zip-file fileb://vidhi-lambda.zip `
  --timeout 30 `
  --memory-size 1024 `
  --region ap-south-1 `
  --environment "Variables={AWS_REGION=ap-south-1,BHASHINI_API_KEY=your_key_here,LOG_LEVEL=INFO}"

Write-Host "✅ Lambda function created successfully!"
```

**To update existing function:**

```powershell
# Update function code
aws lambda update-function-code `
  --function-name vidhi-backend `
  --zip-file fileb://vidhi-lambda.zip `
  --region ap-south-1

# Update environment variables
aws lambda update-function-configuration `
  --function-name vidhi-backend `
  --environment "Variables={AWS_REGION=ap-south-1,BHASHINI_API_KEY=your_key_here,LOG_LEVEL=INFO}" `
  --region ap-south-1
```

### Step 5: Create API Gateway (HTTP API)

**PowerShell:**

```powershell
# Create HTTP API
$API_RESPONSE = aws apigatewayv2 create-api `
  --name vidhi-api `
  --protocol-type HTTP `
  --region ap-south-1 | ConvertFrom-Json

$API_ID = $API_RESPONSE.ApiId
Write-Host "API ID: $API_ID"

# Get Lambda function ARN
$LAMBDA_ARN = aws lambda get-function `
  --function-name vidhi-backend `
  --region ap-south-1 `
  --query 'Configuration.FunctionArn' `
  --output text

# Create Lambda integration
$INTEGRATION_RESPONSE = aws apigatewayv2 create-integration `
  --api-id $API_ID `
  --integration-type AWS_PROXY `
  --integration-uri $LAMBDA_ARN `
  --payload-format-version 2.0 `
  --region ap-south-1 | ConvertFrom-Json

$INTEGRATION_ID = $INTEGRATION_RESPONSE.IntegrationId
Write-Host "Integration ID: $INTEGRATION_ID"

# Create route for all methods and paths
aws apigatewayv2 create-route `
  --api-id $API_ID `
  --route-key 'ANY /{proxy+}' `
  --target "integrations/$INTEGRATION_ID" `
  --region ap-south-1

# Create default route
aws apigatewayv2 create-route `
  --api-id $API_ID `
  --route-key '$default' `
  --target "integrations/$INTEGRATION_ID" `
  --region ap-south-1

# Create deployment stage
aws apigatewayv2 create-stage `
  --api-id $API_ID `
  --stage-name prod `
  --auto-deploy `
  --region ap-south-1

# Grant API Gateway permission to invoke Lambda
$AWS_ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
aws lambda add-permission `
  --function-name vidhi-backend `
  --statement-id apigateway-invoke `
  --action lambda:InvokeFunction `
  --principal apigateway.amazonaws.com `
  --source-arn "arn:aws:execute-api:ap-south-1:${AWS_ACCOUNT_ID}:${API_ID}/*/*" `
  --region ap-south-1

# Get API endpoint
$API_ENDPOINT = "https://${API_ID}.execute-api.ap-south-1.amazonaws.com/prod"
Write-Host "`n✅ Deployment complete!"
Write-Host "API Endpoint: $API_ENDPOINT"
Write-Host "`nTest your API:"
Write-Host "curl $API_ENDPOINT/health"
```

### Step 6: Test Your Deployment

**PowerShell:**

```powershell
# Get your API endpoint
$API_ID = aws apigatewayv2 get-apis --region ap-south-1 --query "Items[?Name=='vidhi-api'].ApiId" --output text
$API_ENDPOINT = "https://${API_ID}.execute-api.ap-south-1.amazonaws.com/prod"

# Test health endpoint
Invoke-RestMethod -Uri "$API_ENDPOINT/health" -Method Get

# Test with curl (if installed)
curl "$API_ENDPOINT/health"
```

### Step 7: Monitor and Debug

**View Lambda logs:**

```powershell
# View recent logs
aws logs tail /aws/lambda/vidhi-backend --follow --region ap-south-1

# View specific log stream
aws logs describe-log-streams `
  --log-group-name /aws/lambda/vidhi-backend `
  --order-by LastEventTime `
  --descending `
  --max-items 1 `
  --region ap-south-1
```

### Complete PowerShell Deployment Script

Save this as `deploy-lambda-complete.ps1`:

```powershell
# Complete Lambda + API Gateway Deployment Script
param(
    [string]$BhashiniApiKey = $env:BHASHINI_API_KEY,
    [string]$Region = "ap-south-1"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying VIDHI Backend to Lambda + API Gateway" -ForegroundColor Green

# 1. Create deployment package
Write-Host "`n📦 Creating deployment package..." -ForegroundColor Cyan
.\deploy.ps1 lambda

# 2. Get AWS Account ID
$AWS_ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
Write-Host "AWS Account: $AWS_ACCOUNT_ID"

# 3. Create IAM role (if doesn't exist)
Write-Host "`n🔐 Setting up IAM role..." -ForegroundColor Cyan
try {
    aws iam get-role --role-name vidhi-lambda-execution-role 2>$null | Out-Null
    Write-Host "IAM role already exists"
} catch {
    Write-Host "Creating IAM role..."
    
    @"
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
"@ | Out-File -FilePath trust-policy.json -Encoding utf8

    aws iam create-role --role-name vidhi-lambda-execution-role --assume-role-policy-document file://trust-policy.json
    aws iam attach-role-policy --role-name vidhi-lambda-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    aws iam attach-role-policy --role-name vidhi-lambda-execution-role --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
    aws iam attach-role-policy --role-name vidhi-lambda-execution-role --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
    
    Start-Sleep -Seconds 10
}

$ROLE_ARN = "arn:aws:iam::${AWS_ACCOUNT_ID}:role/vidhi-lambda-execution-role"

# 4. Create or update Lambda function
Write-Host "`n⚡ Deploying Lambda function..." -ForegroundColor Cyan
try {
    aws lambda get-function --function-name vidhi-backend --region $Region 2>$null | Out-Null
    Write-Host "Updating existing function..."
    aws lambda update-function-code --function-name vidhi-backend --zip-file fileb://vidhi-lambda.zip --region $Region
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
        --environment "Variables={AWS_REGION=$Region,BHASHINI_API_KEY=$BhashiniApiKey,LOG_LEVEL=INFO}"
}

# 5. Create API Gateway
Write-Host "`n🌐 Setting up API Gateway..." -ForegroundColor Cyan
$API_ID = aws apigatewayv2 get-apis --region $Region --query "Items[?Name=='vidhi-api'].ApiId" --output text

if (-not $API_ID) {
    Write-Host "Creating new API..."
    $API_RESPONSE = aws apigatewayv2 create-api --name vidhi-api --protocol-type HTTP --region $Region | ConvertFrom-Json
    $API_ID = $API_RESPONSE.ApiId
    
    $LAMBDA_ARN = aws lambda get-function --function-name vidhi-backend --region $Region --query 'Configuration.FunctionArn' --output text
    
    $INTEGRATION_RESPONSE = aws apigatewayv2 create-integration `
        --api-id $API_ID `
        --integration-type AWS_PROXY `
        --integration-uri $LAMBDA_ARN `
        --payload-format-version 2.0 `
        --region $Region | ConvertFrom-Json
    
    $INTEGRATION_ID = $INTEGRATION_RESPONSE.IntegrationId
    
    aws apigatewayv2 create-route --api-id $API_ID --route-key 'ANY /{proxy+}' --target "integrations/$INTEGRATION_ID" --region $Region
    aws apigatewayv2 create-route --api-id $API_ID --route-key '$default' --target "integrations/$INTEGRATION_ID" --region $Region
    aws apigatewayv2 create-stage --api-id $API_ID --stage-name prod --auto-deploy --region $Region
    
    aws lambda add-permission `
        --function-name vidhi-backend `
        --statement-id apigateway-invoke `
        --action lambda:InvokeFunction `
        --principal apigateway.amazonaws.com `
        --source-arn "arn:aws:execute-api:${Region}:${AWS_ACCOUNT_ID}:${API_ID}/*/*" `
        --region $Region
} else {
    Write-Host "API Gateway already exists"
}

$API_ENDPOINT = "https://${API_ID}.execute-api.${Region}.amazonaws.com/prod"

Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
Write-Host "`n📍 API Endpoint: $API_ENDPOINT" -ForegroundColor Yellow
Write-Host "`n🧪 Test your API:" -ForegroundColor Cyan
Write-Host "   curl $API_ENDPOINT/health"
Write-Host "   Invoke-RestMethod -Uri '$API_ENDPOINT/health'"
```

**Run the complete deployment:**

```powershell
.\deploy-lambda-complete.ps1 -BhashiniApiKey "your_api_key_here"
```

---

## Option 3: AWS EC2 (Traditional)

Full control over the server.

### Step 1: Launch EC2 Instance

1. Go to EC2 console
2. Launch instance:
   - AMI: Ubuntu 22.04 LTS
   - Instance type: t3.medium (2 vCPU, 4 GB RAM)
   - Security group: Allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
   - Key pair: Create or select existing

### Step 2: Connect and Setup

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install -y python3.12 python3.12-venv python3-pip

# Install FFmpeg
sudo apt install -y ffmpeg

# Install Nginx
sudo apt install -y nginx

# Install Git
sudo apt install -y git
```

### Step 3: Deploy Application

```bash
# Clone repository (or upload files)
git clone https://github.com/your-repo/vidhi.git
cd vidhi/vidhi-backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
nano .env
# Add your environment variables

# Test application
python app.py
```

### Step 4: Setup Systemd Service

Create `/etc/systemd/system/vidhi.service`:

```ini
[Unit]
Description=VIDHI FastAPI Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/vidhi/vidhi-backend
Environment="PATH=/home/ubuntu/vidhi/vidhi-backend/venv/bin"
EnvironmentFile=/home/ubuntu/vidhi/vidhi-backend/.env
ExecStart=/home/ubuntu/vidhi/vidhi-backend/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable vidhi
sudo systemctl start vidhi
sudo systemctl status vidhi
```

### Step 5: Configure Nginx

Create `/etc/nginx/sites-available/vidhi`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts for long requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/vidhi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 6: Setup SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

---

## Option 4: AWS Elastic Beanstalk

Managed platform with auto-scaling.

### Step 1: Install EB CLI

```bash
pip install awsebcli
```

### Step 2: Initialize Elastic Beanstalk

```bash
cd vidhi-backend

# Initialize
eb init -p python-3.12 vidhi-backend --region ap-south-1

# Create environment
eb create vidhi-prod --instance-type t3.medium
```

### Step 3: Configure Environment

Create `.ebextensions/01_packages.config`:

```yaml
packages:
  yum:
    ffmpeg: []
```

Create `.ebextensions/02_python.config`:

```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: app:app
  aws:elasticbeanstalk:application:environment:
    AWS_REGION: ap-south-1
    BHASHINI_API_KEY: your_key_here
```

### Step 4: Deploy

```bash
# Deploy
eb deploy

# Open in browser
eb open

# View logs
eb logs

# SSH into instance
eb ssh
```

---

## Environment Variables Setup

### For All Deployment Methods

Create a `.env` file (never commit this):

```bash
# AWS Configuration
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Bhashini API
BHASHINI_API_KEY=your_bhashini_key
BHASHINI_USER_ID=your_user_id

# Application Settings
LOG_LEVEL=INFO
ENABLE_VOICE_INPUT=true
ENABLE_DOCUMENT_ANALYSIS=true
ENABLE_SCHEME_MATCHING=true

# S3 Buckets
S3_BUCKET_AUDIO=vidhi-audio-prod
S3_BUCKET_DOCUMENTS=vidhi-documents-prod

# Database (if using)
DATABASE_URL=postgresql://user:pass@host:5432/vidhi

# CORS Origins (comma-separated)
CORS_ORIGINS=https://your-frontend.com,https://www.your-frontend.com
```

---

## Cost Estimates (Monthly)

### App Runner
- **Light usage**: $5-10
- **Medium usage**: $20-50
- **Heavy usage**: $50-100

### Lambda + API Gateway
- **1M requests**: $5-10
- **10M requests**: $50-100
- **Pay only for what you use**

### EC2 (t3.medium)
- **Instance**: $30
- **Storage (50GB)**: $5
- **Data transfer**: $5-20
- **Total**: $40-55

### Elastic Beanstalk
- **Same as EC2** + $0 (no additional charge)
- **Load balancer**: +$18/month (optional)

---

## Monitoring and Logging

### CloudWatch Logs

```bash
# View logs (Lambda)
aws logs tail /aws/lambda/vidhi-backend --follow

# View logs (App Runner)
aws logs tail /aws/apprunner/vidhi-backend/application --follow
```

### CloudWatch Metrics

Set up alarms for:
- CPU utilization > 80%
- Memory utilization > 80%
- Error rate > 5%
- Response time > 5s

---

## CI/CD Pipeline (GitHub Actions)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ap-south-1
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build and push Docker image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: vidhi-backend
        IMAGE_TAG: ${{ github.sha }}
      run: |
        cd vidhi-backend
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
    
    - name: Deploy to App Runner
      run: |
        aws apprunner start-deployment --service-arn ${{ secrets.APP_RUNNER_SERVICE_ARN }}
```

---

## Security Best Practices

1. **Use IAM roles** instead of access keys when possible
2. **Enable AWS WAF** for API protection
3. **Use AWS Secrets Manager** for sensitive data
4. **Enable CloudTrail** for audit logging
5. **Use VPC** for network isolation
6. **Enable encryption** at rest and in transit
7. **Regular security updates** for dependencies
8. **Rate limiting** on API endpoints

---

## Troubleshooting

### Common Issues

**Issue: Lambda timeout**
- Solution: Increase timeout to 30s or use async processing

**Issue: Cold start latency**
- Solution: Use provisioned concurrency or App Runner

**Issue: Memory errors**
- Solution: Increase memory allocation

**Issue: FFmpeg not found**
- Solution: Include FFmpeg in Docker image or Lambda layer

---

## Recommended Setup for VIDHI

For your project, I recommend:

1. **Start with**: AWS App Runner (easiest, cost-effective)
2. **Scale to**: ECS Fargate (when you need more control)
3. **Use**: S3 for audio storage
4. **Use**: CloudFront for CDN
5. **Use**: RDS for database (if needed)

**Estimated monthly cost**: $20-50 for moderate usage

---

## Quick Start Commands

```bash
# 1. Build Docker image
cd vidhi-backend
docker build -t vidhi-backend .

# 2. Test locally
docker run -p 8000:8000 vidhi-backend

# 3. Push to ECR
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com
docker tag vidhi-backend:latest YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/vidhi-backend:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com/vidhi-backend:latest

# 4. Deploy to App Runner (via console or CLI)
```

---

## Support

For issues or questions:
- AWS Documentation: https://docs.aws.amazon.com
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/
- Docker Documentation: https://docs.docker.com
