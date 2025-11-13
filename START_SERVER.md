# How to Start the Backend Server

## Quick Start

### Option 1: Using Python Module (Recommended)
```bash
# From project root directory
python -m app.main
```

### Option 2: Using Uvicorn Directly
```bash
# From project root directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Using Uvicorn with Python Path
```bash
# From project root directory
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Verify Server is Running

After starting, you should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Test Server is Working

Open in your browser:
- Admin Panel: `http://localhost:8000/admin`
- Embed Endpoint: `http://localhost:8000/embed`
- API Config: `http://localhost:8000/admin/api/config`

## Common Issues

### Issue: "Port 8000 already in use"
**Solution:** 
- Find and stop the process using port 8000
- Or change the port: `--port 8001` (and update iframe URL)

### Issue: "Module not found"
**Solution:**
```bash
# Install dependencies
pip install -r requirements.txt
```

### Issue: "Database connection error"
**Solution:**
- Check your `.env` file for database connection string
- Make sure PostgreSQL is running
- Verify database credentials

## After Starting Server

1. **Open test_embed.html** in your browser
2. The chatbot should now load instead of showing "refused to connect"
3. Check browser console (F12) for initialization logs

