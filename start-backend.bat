@echo off
REM Batch script to start the backend server on Windows
echo 🚀 Starting AskCache.ai Backend Server...

REM Change to script directory
cd /d "%~dp0"

REM Check if backend is already running
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ Backend is already running on port 8000
    goto :end
)

echo 📦 Starting backend server...

REM Set environment variable
set ENVIRONMENT=development

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo 🔧 Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Start backend server
echo 🌐 Starting uvicorn server on 0.0.0.0:8000...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

:end
echo.
echo ✅ Backend server started!
echo 📍 Server URL: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
pause




