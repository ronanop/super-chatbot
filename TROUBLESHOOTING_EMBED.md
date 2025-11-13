# Troubleshooting Embed Iframe Issues

## Issue: "Internal Server Error (500)" or Blank Page

### Step 1: Restart Your Backend Server

The embed endpoint code has been updated. You need to restart your server:

```bash
# Stop your current server (Ctrl+C)

# Start it again
python -m app.main
# OR
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Verify Widget is Built

Make sure the widget has been built:

```bash
cd chatbot-widget
npm run build
```

This should create files in `chatbot-widget/dist/assets/`:
- `index.js`
- `index.css`

### Step 3: Check Server Logs

When you access `http://localhost:8000/embed`, check your server console for:
- Any error messages
- "Using configured API URL for embed" or "Using request-based API URL for embed"

### Step 4: Test the Embed Endpoint Directly

Open in your browser:
```
http://localhost:8000/embed
```

You should see:
- A blank page with the chatbot widget loading
- Check browser console (F12) for initialization logs

### Step 5: Check Browser Console

Open `test_embed.html` and check the browser console (F12):

**Expected logs:**
```
🚀 Chatbot Widget Embed Initialized:
  Version: [timestamp]
  API Base URL: [url]
  Request URL: [url]
✅ Using embed-provided API URL: [url]
✅ UI Settings fetched: [settings]
```

**If you see errors:**
- **500 Error**: Server issue - check server logs
- **404 Error**: Widget files not found - rebuild widget
- **CORS Error**: Check CORS settings in main.py
- **Network Error**: Backend server not running

### Step 6: Verify Database Connection

The embed endpoint queries the database for API URL settings. If the database isn't initialized:

1. The endpoint will still work (uses request URL as fallback)
2. Check server logs for "Warning: Could not query AppSettings"

### Common Fixes

#### Fix 1: Rebuild Widget
```bash
cd chatbot-widget
npm install  # If needed
npm run build
```

#### Fix 2: Check Static Files Route
Verify the static files route is working:
```
http://localhost:8000/static/widget/assets/index.js
http://localhost:8000/static/widget/assets/index.css
```

Both should return the files (not 404).

#### Fix 3: Clear Browser Cache
- Hard refresh: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
- Or open in incognito/private window

#### Fix 4: Check Port
Make sure your server is running on the port specified in the iframe URL:
- Iframe: `http://localhost:8000/embed`
- Server must be on port 8000

#### Fix 5: Database Issues
If you see database-related errors:
1. Check database connection string in `.env`
2. Verify database is running
3. The embed endpoint will still work with fallback URL

## Still Not Working?

1. **Check server terminal** for detailed error messages
2. **Check browser console** (F12) for client-side errors
3. **Verify all files exist:**
   - `chatbot-widget/dist/assets/index.js`
   - `chatbot-widget/dist/assets/index.css`
4. **Test embed URL directly:** `http://localhost:8000/embed`

## Quick Test

Run this to verify everything is set up:

```bash
# 1. Build widget
cd chatbot-widget
npm run build

# 2. Start server (in another terminal)
cd ..
python -m app.main

# 3. Open test page
# Open test_embed.html in browser
```

If the widget loads, you'll see the chatbot interface. If not, check the console logs for specific errors.

