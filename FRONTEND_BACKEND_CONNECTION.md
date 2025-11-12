# Frontend-Backend Connection Guide

## Current Issue: "Failed to fetch" Error

This error means the frontend cannot connect to the backend API.

## Quick Fix Steps

### 1. Check Browser Console
Open your browser's developer console (F12) and check:
- What API URL is being used (should show: "ChatWidget API Base URL: ...")
- Any CORS or network errors

### 2. Set the Correct API URL

The frontend uses `VITE_API_BASE_URL` environment variable. Create a `.env` file in the `chatbot-widget` folder:

**For local development (same machine):**
```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

**For network access (other devices):**
```
VITE_API_BASE_URL=http://YOUR_COMPUTER_IP:8000
```

To find your computer's IP:
- Windows: Run `ipconfig` in CMD, look for "IPv4 Address"
- Example: `VITE_API_BASE_URL=http://192.168.1.100:8000`

### 3. Restart Frontend Dev Server

After creating/updating `.env`:
1. Stop the frontend server (Ctrl+C)
2. Restart it: `npm run dev`

### 4. Verify Backend is Running

Check backend is accessible:
- Open: http://127.0.0.1:8000/health
- Should show: `{"status":"ok"}`

### 5. Check CORS Configuration

Backend should allow all origins. Verify in `.env`:
```
ALLOWED_ORIGINS=*
```

## Common Issues

**Issue: Frontend on different port**
- Frontend might be on port 5173, 5174, or 5175
- Backend CORS includes these ports automatically

**Issue: Network access**
- If accessing from another device, use your computer's LAN IP
- Make sure backend is running with `--host 0.0.0.0`

**Issue: Backend not running**
- Check: `http://127.0.0.1:8000/health`
- Restart backend if needed

## Testing Connection

1. Open browser console (F12)
2. Look for: "ChatWidget API Base URL: http://..."
3. Try the API directly: Open `http://127.0.0.1:8000/health` in browser
4. Check Network tab in DevTools to see failed requests

## Current Configuration

- **Backend**: Running on `http://0.0.0.0:8000` (accessible from all interfaces)
- **Frontend**: Defaults to `http://127.0.0.1:8000` if no `.env` file
- **CORS**: Allows all origins (`*`)

