@echo off
REM VIDHI Backend Quick Start Script for Windows

echo.
echo ========================================
echo   VIDHI Backend Quick Start
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9 or higher.
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

REM Create virtual environment
echo [STEP 1] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment created
echo.

REM Activate virtual environment
echo [STEP 2] Activating virtual environment...
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated
echo.

REM Upgrade pip
echo [STEP 3] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [OK] Pip upgraded
echo.

REM Install dependencies
echo [STEP 4] Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM Check if .env exists
if not exist .env (
    echo [STEP 5] Creating .env file from template...
    copy .env.example .env >nul
    echo [OK] .env file created
    echo.
    echo [WARNING] Please edit .env file with your AWS credentials!
    echo.
) else (
    echo [STEP 5] .env file already exists
    echo.
)

REM Check AWS CLI
aws --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] AWS CLI not found
    echo Install from: https://aws.amazon.com/cli/
    echo.
) else (
    echo [OK] AWS CLI found
    aws --version
    echo.
    
    REM Check AWS credentials
    aws sts get-caller-identity >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] AWS credentials not configured
        echo Run: aws configure
        echo.
    ) else (
        echo [OK] AWS credentials configured
        echo.
    )
)

echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env file with your AWS credentials
echo 2. Create AWS resources (see README.md)
echo 3. Enable AWS Bedrock model access
echo 4. Run: python app.py
echo.
echo For detailed instructions, see README.md
echo.
pause
