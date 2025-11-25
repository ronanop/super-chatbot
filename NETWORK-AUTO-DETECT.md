# Network Auto-Detection Feature

## Overview
The application now automatically detects and adapts to network changes. When you switch WiFi networks, both the frontend and backend will automatically adjust to the new network configuration without manual intervention.

## How It Works

### Backend
- The backend always binds to `0.0.0.0:8000`, making it accessible from all network interfaces
- This allows the backend to be reachable via:
  - `localhost:8000` (local access)
  - `127.0.0.1:8000` (local access)
  - Any network IP address on port 8000 (e.g., `192.168.1.100:8000`)

### Frontend Auto-Detection
The frontend uses multiple strategies to find the backend:

1. **WebRTC IP Discovery**: Uses WebRTC to detect your current local network IP address
2. **Current Origin Detection**: If accessing via a specific IP/hostname, tries that first
3. **Parallel URL Testing**: Tests multiple possible URLs simultaneously for faster discovery
4. **Automatic Retry**: On connection failure, automatically rediscovers the backend URL and retries

### Detection Priority
The frontend tries backend URLs in this order:
1. Current origin (if accessing via IP/hostname)
2. `localhost:8000`
3. `127.0.0.1:8000`
4. Dynamically discovered network IPs (via WebRTC)
5. Fallback to default

### Automatic Retry Logic
When a connection fails:
1. The frontend automatically attempts to rediscover the backend URL
2. Tests all possible URLs in parallel
3. Updates the API URL if a new one is found
4. Retries the request with the new URL
5. Only shows an error if all attempts fail

## Usage

### Starting the Application

**Terminal 1 - Backend:**
```powershell
.\start-backend.ps1
```

**Terminal 2 - Frontend:**
```powershell
.\start-frontend.ps1
```

### Network Changes
When you switch WiFi networks:
1. The backend continues running (it's bound to all interfaces)
2. The frontend automatically detects the new network IP
3. All API calls automatically use the new backend URL
4. No manual configuration needed!

## Technical Details

### Backend Configuration
- Host: `0.0.0.0` (all interfaces)
- Port: `8000`
- CORS: Configured to allow all origins in development mode

### Frontend Configuration
- File: `chatbot-widget/src/config.js`
- Function: `fetchApiConfig(forceRediscover)`
- Caching: Last successful URL is cached for faster subsequent requests

### Error Handling
- Network errors trigger automatic URL rediscovery
- User-friendly error messages if backend cannot be found
- Automatic retry with exponential backoff

## Troubleshooting

### Backend Not Found
If the frontend cannot find the backend:
1. Ensure backend is running: `.\start-backend.ps1`
2. Check backend is accessible: Open `http://localhost:8000/health` in browser
3. Check firewall settings (port 8000 must be open)
4. Verify network connectivity

### Still Having Issues?
1. Open browser console (F12) to see detection logs
2. Check which URLs are being tested
3. Verify backend is bound to `0.0.0.0:8000` (check startup logs)
4. Try accessing backend directly via IP in browser

## Benefits
- ✅ No manual IP configuration needed
- ✅ Works across network changes
- ✅ Faster connection (parallel testing)
- ✅ Automatic recovery from network issues
- ✅ Better user experience



