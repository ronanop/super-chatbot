# Quick Fix: Chatbot Not Visible in test_embed.html

## ✅ Widget Built Successfully!

The widget has been built. Now follow these steps:

### Step 1: Make Sure Backend Server is Running

Open a terminal and run:
```bash
python -m app.main
```

Or:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Test the Embed Endpoint Directly

Open in your browser:
```
http://localhost:8000/embed
```

**Expected:** You should see the chatbot widget loading.

**If you see an error:**
- Check server terminal for error messages
- Make sure port 8000 is not being used by another application

### Step 3: Open test_embed.html

1. **Double-click** `test_embed.html` to open in your browser
2. **OR** Right-click → Open with → Your browser
3. The chatbot should now be visible in both sections

### Step 4: Check Browser Console

Press **F12** to open Developer Tools, then check:

**Console Tab:**
- Look for: `🚀 Chatbot Widget Embed Initialized`
- Look for: `✅ Using embed-provided API URL`
- Look for: `✅ UI Settings fetched`

**Network Tab:**
- Check if `/static/widget/assets/index.js` loads (status 200)
- Check if `/static/widget/assets/index.css` loads (status 200)
- Check if `/admin/bot-ui/api/settings` loads (status 200)

### Common Issues & Fixes

#### Issue: Still seeing blank/error
**Fix:** 
1. Hard refresh: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
2. Clear browser cache
3. Try incognito/private window

#### Issue: "Cannot connect to backend"
**Fix:**
- Make sure backend server is running
- Check if server is on correct port (8000)
- Verify `http://localhost:8000/admin` works

#### Issue: "404 Not Found" for static files
**Fix:**
- Verify `chatbot-widget/dist/assets/` folder exists
- Restart backend server after building widget
- Check server logs for file path errors

#### Issue: Widget loads but shows old UI
**Fix:**
- Wait 5 seconds (auto-sync)
- Hard refresh: `Ctrl+F5`
- Check browser console for settings fetch errors

### Verification Checklist

- [ ] Widget built (`chatbot-widget/dist/assets/` exists)
- [ ] Backend server running (check terminal)
- [ ] Can access `http://localhost:8000/admin`
- [ ] Can access `http://localhost:8000/embed` directly
- [ ] Browser console shows initialization logs
- [ ] No errors in browser console
- [ ] Static files load (check Network tab)

### Still Not Working?

1. **Check server terminal** - Look for error messages
2. **Check browser console** (F12) - Look for JavaScript errors
3. **Test embed URL directly** - `http://localhost:8000/embed`
4. **Verify files exist:**
   ```bash
   ls chatbot-widget/dist/assets/
   ```
   Should show: `index.js` and `index.css`

