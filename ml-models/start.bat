@echo off
REM Mind Bridge AI ML Service Startup Script for Windows

echo 🚀 Starting Mind Bridge AI ML Service
echo =====================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM Check if service is already running
curl -s http://localhost:8001/health >nul 2>&1
if not errorlevel 1 (
    echo ⚠️  Service is already running on port 8001
    echo    Stopping existing service...
    taskkill /f /im python.exe >nul 2>&1
    timeout /t 2 >nul
)

REM Start the service
echo 🎯 Starting ML service on port 8001...
echo    Health check: http://localhost:8001/health
echo    API docs: http://localhost:8001/docs
echo    Press Ctrl+C to stop
echo.

uvicorn main:app --reload --port 8001 --host 0.0.0.0
