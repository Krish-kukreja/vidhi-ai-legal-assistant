# VIDHI Backend Deployment Script for Windows
# Usage: .\deploy.ps1 [app-runner|lambda|ec2]

param(
  [string]$DeploymentType = "app-runner",
  [string]$ImageTag = "latest"
)

$ErrorActionPreference = "Stop"

$AWS_REGION = if ($env:AWS_REGION) { $env:AWS_REGION } else { "ap-south-1" }
$ECR_REPOSITORY = "vidhi-backend"

Write-Host "🚀 Deploying VIDHI Backend to AWS ($DeploymentType)" -ForegroundColor Green
Write-Host "Region: $AWS_REGION"

# Get AWS Account ID
try {
  $AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
  Write-Host "Account: $AWS_ACCOUNT_ID"
}
catch {
  Write-Host "❌ Error: AWS CLI not configured. Run 'aws configure' first." -ForegroundColor Red
  exit 1
}

# Build Docker image
Write-Host "`n📦 Building Docker image..." -ForegroundColor Cyan
docker build -t "${ECR_REPOSITORY}:${ImageTag}" .

if ($DeploymentType -eq "app-runner" -or $DeploymentType -eq "ecs") {
  # Create ECR repository if it doesn't exist
  Write-Host "`n🏗️  Checking ECR repository..." -ForegroundColor Cyan
  try {
    aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>$null
  }
  catch {
    Write-Host "Creating ECR repository..."
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION
  }

  # Login to ECR
  Write-Host "`n🔐 Logging in to ECR..." -ForegroundColor Cyan
  $ECR_PASSWORD = aws ecr get-login-password --region $AWS_REGION
  $ECR_PASSWORD | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

  # Tag and push image
  Write-Host "`n📤 Pushing image to ECR..." -ForegroundColor Cyan
  $ECR_IMAGE = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPOSITORY}:${ImageTag}"
  docker tag "${ECR_REPOSITORY}:${ImageTag}" $ECR_IMAGE
  docker push $ECR_IMAGE

  Write-Host "`n✅ Image pushed to ECR: $ECR_IMAGE" -ForegroundColor Green

  if ($DeploymentType -eq "app-runner") {
    Write-Host "`n🏃 Next steps for App Runner:" -ForegroundColor Yellow
    Write-Host "   1. Go to AWS App Runner console"
    Write-Host "   2. Create/Update service"
    Write-Host "   3. Use image: $ECR_IMAGE"
    Write-Host "   4. Set port: 8000"
    Write-Host "   5. Add environment variables (AWS_REGION, BHASHINI_API_KEY, etc.)"
  }

}
elseif ($DeploymentType -eq "lambda") {
  Write-Host "`n📦 Creating Lambda deployment package..." -ForegroundColor Cyan
    
  # Create deployment directory
  if (Test-Path "lambda_package") {
    Remove-Item -Recurse -Force lambda_package
  }
  New-Item -ItemType Directory -Path lambda_package | Out-Null
  Set-Location lambda_package

  # Install dependencies
  Write-Host "Installing dependencies..."
  pip install -r ..\requirements.txt -t .

  # Copy application code
  Write-Host "Copying application code..."
  Copy-Item ..\*.py .
    
  $folders = @("services", "speech", "stores", "processing", "configs", "llm_setup")
  foreach ($folder in $folders) {
    if (Test-Path "..\$folder") {
      Copy-Item -Recurse "..\$folder" .
    }
  }

  # Create ZIP using PowerShell
  Write-Host "Creating ZIP file..."
  Compress-Archive -Path * -DestinationPath ..\vidhi-lambda.zip -Force
  Set-Location ..

  Write-Host "`n✅ Lambda package created: vidhi-lambda.zip" -ForegroundColor Green
  Write-Host "`n📤 Next steps:" -ForegroundColor Yellow
  Write-Host "   1. Go to AWS Lambda console"
  Write-Host "   2. Create function (Python 3.12)"
  Write-Host "   3. Upload vidhi-lambda.zip"
  Write-Host "   4. Set handler: app.handler"
  Write-Host "   5. Set timeout: 30 seconds"
  Write-Host "   6. Set memory: 1024 MB"
  Write-Host "   7. Add environment variables"

}
elseif ($DeploymentType -eq "ec2") {
  Write-Host "`n🖥️  For EC2 deployment:" -ForegroundColor Yellow
  Write-Host "   1. Launch EC2 instance (Ubuntu 22.04, t3.medium)"
  Write-Host "   2. SSH into instance"
  Write-Host "   3. Run: git clone <your-repo>"
  Write-Host "   4. Run: cd vidhi-backend && bash setup-ec2.sh"

}
else {
  Write-Host "`n❌ Unknown deployment type: $DeploymentType" -ForegroundColor Red
  Write-Host "Usage: .\deploy.ps1 [app-runner|lambda|ec2]"
  exit 1
}

Write-Host "`n✅ Deployment preparation complete!" -ForegroundColor Green
