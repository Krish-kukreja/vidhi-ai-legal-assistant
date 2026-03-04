@echo off
echo ========================================
echo VIDHI - GitHub Repository Setup
echo ========================================
echo.

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git is not installed or not in PATH
    echo Please install Git from: https://git-scm.com/download/win
    pause
    exit /b 1
)

echo Step 1: Initialize Git repository...
git init
if errorlevel 1 (
    echo ERROR: Failed to initialize Git repository
    pause
    exit /b 1
)

echo.
echo Step 2: Add all files to Git...
git add .
if errorlevel 1 (
    echo ERROR: Failed to add files to Git
    pause
    exit /b 1
)

echo.
echo Step 3: Create initial commit...
git commit -m "Initial commit: VIDHI - Voice-Integrated Defense for Holistic Inclusion

Features:
- Complete React frontend with 22+ languages
- FastAPI backend with AWS integration
- Document education system
- Language-preserved voice playback
- Emergency legal assistance
- Government scheme search
- Comprehensive documentation

Tech Stack:
- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Python
- Cloud: AWS (Bedrock, Polly, Transcribe, S3, DynamoDB)
- Languages: 22+ Indian languages supported"

if errorlevel 1 (
    echo ERROR: Failed to create initial commit
    pause
    exit /b 1
)

echo.
echo ========================================
echo Git repository initialized successfully!
echo ========================================
echo.
echo Next steps:
echo.
echo 1. Create a new repository on GitHub:
echo    - Go to: https://github.com/new
echo    - Repository name: vidhi
echo    - Description: AI-Powered Legal Assistant for Indian Citizens
echo    - Make it Public (recommended) or Private
echo    - DO NOT initialize with README (we already have one)
echo    - Click "Create repository"
echo.
echo 2. Copy the repository URL (it will look like):
echo    https://github.com/yourusername/vidhi.git
echo.
echo 3. Run these commands to push to GitHub:
echo    git remote add origin https://github.com/yourusername/vidhi.git
echo    git branch -M main
echo    git push -u origin main
echo.
echo 4. Your repository will be live at:
echo    https://github.com/yourusername/vidhi
echo.
echo Repository structure:
echo ├── vidhi-assistant/     (React Frontend)
echo ├── vidhi-backend/      (FastAPI Backend)  
echo ├── docs/               (Documentation)
echo ├── README.md           (Project overview)
echo ├── .gitignore          (Git ignore rules)
echo └── LICENSE             (MIT License)
echo.
pause