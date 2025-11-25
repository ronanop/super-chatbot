# PowerShell script to start the frontend server
# This script checks if backend is running and starts the frontend

Write-Host "Starting AskCache.ai Frontend..." -ForegroundColor Cyan

# Change to project directory
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$projectDir\chatbot-widget"

# Check if backend is running
$backendRunning = $false
$backendUrls = @("http://localhost:8000/health", "http://10.81.226.34:8000/health", "http://192.168.0.120:8000/health")

foreach ($url in $backendUrls) {
    try {
        $response = Invoke-WebRequest -Uri $url -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "Backend is running at $url" -ForegroundColor Green
            $backendRunning = $true
            break
        }
    } catch {
        # Continue checking other URLs
    }
}

if (-not $backendRunning) {
    Write-Host "WARNING: Backend server is not running!" -ForegroundColor Yellow
    Write-Host "   Please start the backend first using: .\start-backend.ps1" -ForegroundColor Yellow
    Write-Host "   Or run: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit
    }
}

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
}

# Start frontend server
Write-Host "Starting frontend development server..." -ForegroundColor Cyan
npm run dev
