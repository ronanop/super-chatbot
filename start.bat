@echo off
REM Production startup script for Cache Digitech Chatbot (Windows)

echo 🚀 Starting Cache Digitech Chatbot...

REM Load environment variables from .env if it exists
if exist .env (
    echo 📋 Loading environment variables from .env
    for /f "tokens=1,* delims==" %%a in (.env) do (
        set "%%a=%%b"
    )
) else (
    echo ⚠️  Warning: .env file not found. Using environment variables.
)

REM Set defaults
if "%HOST%"=="" set HOST=0.0.0.0
if "%PORT%"=="" set PORT=8000
if "%WORKERS%"=="" set WORKERS=4
if "%LOG_LEVEL%"=="" set LOG_LEVEL=INFO

REM Check required variables
if "%DATABASE_URL%"=="" (
    echo ❌ Error: DATABASE_URL environment variable is not set.
    exit /b 1
)
if "%GEMINI_API_KEY%"=="" (
    echo ❌ Error: GEMINI_API_KEY environment variable is not set.
    exit /b 1
)
if "%PINECONE_API_KEY%"=="" (
    echo ❌ Error: PINECONE_API_KEY environment variable is not set.
    exit /b 1
)
if "%PINECONE_INDEX%"=="" (
    echo ❌ Error: PINECONE_INDEX environment variable is not set.
    exit /b 1
)
if "%SESSION_SECRET_KEY%"=="" (
    echo ❌ Error: SESSION_SECRET_KEY environment variable is not set.
    exit /b 1
)

REM Build frontend widget if dist doesn't exist
if not exist "chatbot-widget\dist" (
    echo 📦 Building frontend widget...
    cd chatbot-widget
    call npm install
    call npm run build
    cd ..
)

REM Start the application
echo 🌟 Starting application on %HOST%:%PORT% with %WORKERS% workers...
echo.

if "%ENVIRONMENT%"=="development" (
    echo 🔧 Development mode: Using uvicorn with auto-reload
    uvicorn app.main:app --host %HOST% --port %PORT% --reload --log-level %LOG_LEVEL%
) else (
    echo 🏭 Production mode: Using uvicorn with %WORKERS% workers
    uvicorn app.main:app --host %HOST% --port %PORT% --workers %WORKERS% --log-level %LOG_LEVEL% --access-log --no-use-colors
)

