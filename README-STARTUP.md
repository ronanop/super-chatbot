# AskCache.ai - Startup Guide

## Quick Start

### Option 1: Use Startup Scripts (Recommended)

**Windows PowerShell:**
```powershell
# Terminal 1: Start Backend
.\start-backend.ps1

# Terminal 2: Start Frontend
.\start-frontend.ps1
```

**Windows Command Prompt:**
```cmd
# Terminal 1: Start Backend
start-backend.bat

# Terminal 2: Start Frontend
cd chatbot-widget
npm run dev
```

### Option 2: Manual Start

**Terminal 1 - Backend:**
```powershell
cd C:\Users\risha\Downloads\askcache
$env:ENVIRONMENT="development"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```powershell
cd C:\Users\risha\Downloads\askcache\chatbot-widget
npm run dev
```

## Troubleshooting

### Backend Not Starting
1. Check if Python is installed: `python --version`
2. Check if dependencies are installed: `pip install -r requirements.txt`
3. Check if port 8000 is available: `netstat -ano | findstr :8000`

### Frontend Connection Issues
1. Ensure backend is running on port 8000
2. Check backend URL in browser console
3. Verify CORS is enabled (should be automatic in development mode)

### IP Address Changes
If your IP address changes, the backend will automatically bind to `0.0.0.0`, making it accessible from any network interface. The frontend will try to detect the correct backend URL automatically.

## Important Notes

- **Always start the backend first** before starting the frontend
- The backend must be running for the frontend to work
- Backend runs on port 8000
- Frontend runs on port 5173
- CORS is automatically configured in development mode




