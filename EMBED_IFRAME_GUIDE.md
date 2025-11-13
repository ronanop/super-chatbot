# How to Use the Updated Embed Iframe

This guide explains how to use the chatbot widget embed iframe after the recent updates.

## Prerequisites

1. **Backend server must be running** on port 8000 (or your configured port)
2. **Widget must be built** - The frontend widget needs to be compiled

## Step 1: Rebuild the Widget

After making changes to the widget code, you need to rebuild it:

```bash
# Navigate to the widget directory
cd chatbot-widget

# Install dependencies (if not already done)
npm install

# Build the widget for production
npm run build
```

This creates the `dist` folder with the compiled widget files that the embed endpoint serves.

## Step 2: Get the Embed Code

### Option A: From Admin Panel (Recommended)

1. **Start your backend server:**
   ```bash
   # From the project root
   python -m app.main
   # Or
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Open the admin panel:**
   - Go to `http://localhost:8000/admin` (or your server URL)
   - Login with your admin credentials

3. **Navigate to App Settings:**
   - Click on **"App Settings"** in the sidebar
   - Scroll down to the **"Embed Code"** section

4. **Copy the embed code:**
   - Click the **"Copy Code"** button
   - The embed code will be copied to your clipboard

### Option B: Manual Embed Code

Use this template and replace `YOUR_SERVER_URL` with your actual server address:

```html
<!-- Chatbot Widget Container -->
<div style="width: 100%; height: 600px; max-width: 100%;">
  <iframe 
    style="width: 100%; height: 100%; border: none; border-radius: 12px;" 
    src="http://YOUR_SERVER_URL:8000/embed"
    allow="microphone"
  ></iframe>
</div>
```

**Examples:**
- **Local development:** `http://localhost:8000/embed`
- **Local network:** `http://192.168.1.100:8000/embed` (replace with your IP)
- **Production:** `https://yourdomain.com/embed`

## Step 3: Add to Your HTML Page

### Basic Example

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Website with Chatbot</title>
</head>
<body>
    <h1>Welcome to My Website</h1>
    <p>Your content here...</p>
    
    <!-- Chatbot Widget -->
    <div style="width: 100%; height: 600px; max-width: 100%;">
      <iframe 
        style="width: 100%; height: 100%; border: none; border-radius: 12px;" 
        src="http://localhost:8000/embed"
        allow="microphone"
      ></iframe>
    </div>
</body>
</html>
```

### Responsive Example (Full Height)

```html
<!-- Full viewport height -->
<div style="width: 100%; height: 100vh;">
  <iframe 
    style="width: 100%; height: 100%; border: none;" 
    src="http://localhost:8000/embed"
    allow="microphone"
  ></iframe>
</div>
```

### Compact Example (Fixed Height)

```html
<!-- Compact size -->
<div style="width: 100%; height: 500px;">
  <iframe 
    style="width: 100%; height: 100%; border: none;" 
    src="http://localhost:8000/embed"
    allow="microphone"
  ></iframe>
</div>
```

## Step 4: Configure API URL (Important!)

The embed iframe automatically uses the correct API URL, but you can configure it:

1. **Go to Admin Panel → App Settings**
2. **API URL Configuration:**
   - **Auto-detect (Recommended):** Automatically detects your IP address
   - **Manual:** Enter a specific API URL like `http://192.168.1.100:8000`

3. **Save the settings**

The embed will automatically use the configured API URL, ensuring it connects to the correct backend.

## Step 5: Customize UI Settings

1. **Go to Admin Panel → BOT UI**
2. **Customize:**
   - Bot name
   - Bot icon / Header image
   - Colors (primary, secondary, background, etc.)
   - Welcome message
   - Widget position and size
   - Custom CSS

3. **Save settings**

**✨ The embed iframe automatically updates within 5 seconds** when you change settings - no reload needed!

## Step 6: Verify It's Working

### Check Browser Console

1. **Open your HTML page** with the embedded iframe
2. **Open Developer Tools** (F12 or Right-click → Inspect)
3. **Go to Console tab**
4. **Look for these logs:**
   ```
   🚀 Chatbot Widget Embed Initialized:
     Version: [timestamp]
     API Base URL: [your-api-url]
     Request URL: [your-server-url]
   ✅ Using embed-provided API URL: [url]
   ✅ UI Settings fetched: [settings]
   ```

### Test the Chatbot

1. Type a message in the chatbot
2. Verify it responds correctly
3. Check that UI matches your admin panel settings

## Troubleshooting

### Issue: "Cannot connect to backend"

**Solution:**
1. Make sure your backend server is running
2. Check the API URL in Admin Panel → App Settings
3. Verify the embed URL matches your server address
4. Check browser console for the actual API URL being used

### Issue: UI doesn't match admin settings

**Solution:**
1. Wait 5 seconds - settings auto-update via polling
2. Hard refresh the page (Ctrl+F5 or Cmd+Shift+R)
3. Check browser console for settings fetch errors
4. Verify settings are saved in Admin Panel → BOT UI

### Issue: Widget not loading

**Solution:**
1. Make sure you ran `npm run build` in the `chatbot-widget` folder
2. Check that `chatbot-widget/dist` folder exists
3. Verify backend server is running
4. Check browser console for errors

### Issue: Using old IP address

**Solution:**
1. The embed now automatically uses the correct URL from the request
2. If still seeing old IP, clear browser cache
3. Update API URL in Admin Panel → App Settings
4. Rebuild widget: `cd chatbot-widget && npm run build`

## Features

✅ **Automatic API URL Detection** - Uses correct server URL automatically  
✅ **Real-time Settings Sync** - UI updates within 5 seconds of changes  
✅ **Responsive Design** - Works on desktop, tablet, and mobile  
✅ **Voice Input Support** - Includes microphone permission  
✅ **Customizable** - All UI settings from admin panel apply automatically  
✅ **No Reload Needed** - Settings update without refreshing  

## Advanced Usage

### Custom Container Styling

```html
<div id="chatbot-container" style="width: 100%; height: 600px; max-width: 100%; border: 2px solid #4338ca; border-radius: 12px; overflow: hidden;">
  <iframe 
    style="width: 100%; height: 100%; border: none;" 
    src="http://localhost:8000/embed"
    allow="microphone"
    title="Chatbot Widget"
  ></iframe>
</div>
```

### Multiple Chatbots on Same Page

You can embed multiple chatbots by using different container divs:

```html
<div style="width: 48%; height: 500px; display: inline-block;">
  <iframe style="width: 100%; height: 100%; border: none;" 
          src="http://localhost:8000/embed"></iframe>
</div>
<div style="width: 48%; height: 500px; display: inline-block;">
  <iframe style="width: 100%; height: 100%; border: none;" 
          src="http://localhost:8000/embed"></iframe>
</div>
```

## Support

If you encounter issues:
1. Check browser console for error messages
2. Verify backend server is running and accessible
3. Ensure widget is built (`npm run build`)
4. Check Admin Panel settings are saved correctly

