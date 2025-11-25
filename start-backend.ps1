# PowerShell script to start the backend server
# This script ensures the backend is running before starting the frontend

Write-Host "🚀 Starting AskCache.ai Backend Server..." -ForegroundColor Cyan

# Change to project directory
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

# Check if backend is already running
$backendRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Backend is already running on port 8000" -ForegroundColor Green
        $backendRunning = $true
    }
} catch {
    # Backend is not running, continue
}

if (-not $backendRunning) {
    Write-Host "📦 Starting backend server..." -ForegroundColor Yellow
    
    # Set environment variables
    $env:ENVIRONMENT = "development"
    
    # Check if virtual environment exists and use its Python executable
    $pythonExe = "python"
    if (Test-Path ".venv\Scripts\python.exe") {
        $pythonExe = Join-Path $projectDir ".venv\Scripts\python.exe"
        Write-Host "🔧 Using virtual environment Python: .venv" -ForegroundColor Cyan
    } elseif (Test-Path "venv\Scripts\python.exe") {
        $pythonExe = Join-Path $projectDir "venv\Scripts\python.exe"
        Write-Host "🔧 Using virtual environment Python: venv" -ForegroundColor Cyan
    } else {
        Write-Host "⚠️  No virtual environment found. Using system Python." -ForegroundColor Yellow
    }
    
    # Get network IP for display
    $networkIP = "localhost"
    try {
        $ipAddresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {
            $_.IPAddress -like '192.168.*' -or $_.IPAddress -like '10.*'
        }
        if ($ipAddresses) {
            $networkIP = $ipAddresses[0].IPAddress
        }
    } catch {
        # Ignore errors getting IP
    }
    
    Write-Host "🌐 Starting uvicorn server on 0.0.0.0:8000..." -ForegroundColor Cyan
    Write-Host "📍 Server will be available at:" -ForegroundColor Cyan
    Write-Host "   - http://localhost:8000" -ForegroundColor Cyan
    Write-Host "   - http://$networkIP`:8000" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
    Write-Host ""
    
    # Start backend server (this is a blocking command)
    & $pythonExe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
} else {
    Write-Host ""
    Write-Host "✅ Backend is already running. No need to start again." -ForegroundColor Green
    Write-Host ""
    Write-Host "Press Ctrl+C to exit" -ForegroundColor Yellow
}

