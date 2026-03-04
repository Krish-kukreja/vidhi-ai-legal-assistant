@echo off
echo ========================================
echo VIDHI Backend - Windows Installation
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo ERROR: Virtual environment not found!
    echo Please create it first: python -m venv venv
    exit /b 1
)

echo Step 1: Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    exit /b 1
)

echo.
echo Step 2: Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip
    exit /b 1
)

echo.
echo Step 3: Installing minimal requirements...
echo This will install only packages with pre-built Windows wheels.
echo.
pip install -r requirements-windows-minimal.txt
if errorlevel 1 (
    echo.
    echo ERROR: Installation failed!
    echo.
    echo Trying to install packages one by one...
    echo.
    pip install fastapi==0.100.0
    pip install uvicorn==0.23.0
    pip install python-multipart==0.0.6
    pip install python-dotenv==1.0.0
    pip install boto3==1.34.34
    pip install requests==2.31.0
    pip install httpx==0.24.1
    pip install beautifulsoup4==4.12.3
    pip install pydantic==1.10.12
    pip install python-dateutil==2.8.2
    pip install pytz==2024.1
    pip install python-json-logger==2.0.7
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Configure AWS: aws configure
echo 2. Copy .env.example to .env and fill in values
echo 3. Start backend: python app.py
echo.
echo See WINDOWS_SETUP.md for detailed instructions.
echo.
pause
