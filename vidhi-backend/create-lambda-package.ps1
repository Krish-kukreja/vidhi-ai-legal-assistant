# Create Lambda Deployment Package with Dependencies
# This script ensures all dependencies are properly installed in the package

param(
    [string]$PythonVersion = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Creating Lambda Deployment Package" -ForegroundColor Green

# Step 1: Clean up old package
Write-Host "`n🧹 Cleaning up old package..." -ForegroundColor Cyan
if (Test-Path "lambda_package") {
    Remove-Item -Recurse -Force lambda_package
    Write-Host "✅ Removed old lambda_package directory"
}
if (Test-Path "vidhi-lambda.zip") {
    Remove-Item -Force vidhi-lambda.zip
    Write-Host "✅ Removed old vidhi-lambda.zip"
}

# Step 2: Create fresh package directory
Write-Host "`n📁 Creating package directory..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path lambda_package | Out-Null
Write-Host "✅ Created lambda_package directory"

# Step 3: Install dependencies INTO the package directory
Write-Host "`n📦 Installing dependencies (this may take a few minutes)..." -ForegroundColor Cyan
Write-Host "Command: pip install -r requirements.txt -t lambda_package" -ForegroundColor Yellow

# Use absolute path to avoid any issues
$requirementsPath = Join-Path $PSScriptRoot "requirements.txt"
$packagePath = Join-Path $PSScriptRoot "lambda_package"

& $PythonVersion -m pip install -r $requirementsPath -t $packagePath --upgrade

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Dependencies installed"

# Step 4: Verify FastAPI was installed
Write-Host "`n🔍 Verifying FastAPI installation..." -ForegroundColor Cyan
if (Test-Path "lambda_package\fastapi") {
    Write-Host "✅ FastAPI found in package" -ForegroundColor Green
} else {
    Write-Host "❌ FastAPI NOT found in package!" -ForegroundColor Red
    Write-Host "This will cause import errors in Lambda" -ForegroundColor Red
    exit 1
}

# Step 5: Copy application code
Write-Host "`n📋 Copying application code..." -ForegroundColor Cyan

# Copy main files
$mainFiles = @("app.py")
foreach ($file in $mainFiles) {
    if (Test-Path $file) {
        Copy-Item $file lambda_package\
        Write-Host "  ✓ Copied $file"
    }
}

# Copy directories
$folders = @("services", "speech", "stores", "processing", "configs", "llm_setup")
foreach ($folder in $folders) {
    if (Test-Path $folder) {
        Copy-Item -Recurse $folder lambda_package\
        Write-Host "  ✓ Copied $folder\"
    }
}

Write-Host "✅ Application code copied"

# Step 6: Create ZIP file
Write-Host "`n📦 Creating ZIP file..." -ForegroundColor Cyan
Write-Host "This may take a minute..." -ForegroundColor Yellow

# Change to lambda_package directory and zip its contents
Push-Location lambda_package
Compress-Archive -Path * -DestinationPath ..\vidhi-lambda.zip -Force
Pop-Location

if (Test-Path "vidhi-lambda.zip") {
    $zipSize = (Get-Item "vidhi-lambda.zip").Length / 1MB
    Write-Host "✅ ZIP created: vidhi-lambda.zip ($([math]::Round($zipSize, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to create ZIP file" -ForegroundColor Red
    exit 1
}

# Step 7: Verify ZIP contents
Write-Host "`n🔍 Verifying ZIP contents..." -ForegroundColor Cyan

# Extract a small portion to verify
if (Test-Path "temp_verify") {
    Remove-Item -Recurse -Force temp_verify
}
New-Item -ItemType Directory -Path temp_verify | Out-Null

# Use PowerShell to expand just the top level
Expand-Archive -Path vidhi-lambda.zip -DestinationPath temp_verify -Force

$hasAppPy = Test-Path "temp_verify\app.py"
$hasFastAPI = Test-Path "temp_verify\fastapi"
$hasBoto3 = Test-Path "temp_verify\boto3"
$hasPydantic = Test-Path "temp_verify\pydantic"

Write-Host "Verification Results:" -ForegroundColor Cyan
Write-Host "  app.py: $(if ($hasAppPy) { '✅ Found' } else { '❌ Missing' })"
Write-Host "  fastapi/: $(if ($hasFastAPI) { '✅ Found' } else { '❌ Missing' })"
Write-Host "  boto3/: $(if ($hasBoto3) { '✅ Found' } else { '❌ Missing' })"
Write-Host "  pydantic/: $(if ($hasPydantic) { '✅ Found' } else { '❌ Missing' })"

# Clean up verification directory
Remove-Item -Recurse -Force temp_verify

if (-not $hasAppPy -or -not $hasFastAPI) {
    Write-Host "`n❌ ZIP file is missing critical components!" -ForegroundColor Red
    exit 1
}

# Step 8: Display summary
Write-Host "`n" + ("="*70) -ForegroundColor Green
Write-Host "✅ LAMBDA PACKAGE CREATED SUCCESSFULLY!" -ForegroundColor Green
Write-Host ("="*70) -ForegroundColor Green

Write-Host "`n📦 Package Details:" -ForegroundColor Cyan
Write-Host "  File: vidhi-lambda.zip"
Write-Host "  Size: $([math]::Round($zipSize, 2)) MB"
Write-Host "  Location: $(Get-Location)\vidhi-lambda.zip"

Write-Host "`n📤 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Upload to Lambda using AWS Console, OR"
Write-Host "  2. Run: aws lambda update-function-code --function-name vidhi-backend --zip-file fileb://vidhi-lambda.zip --region ap-south-1"
Write-Host "  3. Wait 10 seconds for deployment to complete"
Write-Host "  4. Test: Invoke-RestMethod -Uri 'https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/prod/health'"

Write-Host "`n" + ("="*70) -ForegroundColor Green
