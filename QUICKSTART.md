# Quick Start Guide

Get your chatbot up and running in 5 minutes!

## Prerequisites Checklist

- [ ] Python 3.9+ installed
- [ ] Node.js 18+ installed
- [ ] PostgreSQL installed and running
- [ ] Google Gemini API key
- [ ] Pinecone API key

## Step-by-Step Setup

### 1. Clone and Setup Backend (2 minutes)

```bash
# Clone repository
git clone <repository-url>
cd finalbot

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Setup Database (1 minute)

```bash
# Create database (in PostgreSQL)
createdb chatbot_db

# Or using psql:
psql -U postgres
CREATE DATABASE chatbot_db;
\q

# Initialize tables
python -m app.db.init_db
```

### 3. Configure Environment (1 minute)

Create `.env` file in project root:

```env
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/chatbot_db
GEMINI_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
PINECONE_ENVIRONMENT=us-east1-gcp
PINECONE_INDEX_NAME=chatbot-index
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_password
SESSION_SECRET_KEY=random_secret_key_32_chars_min
ALLOWED_ORIGINS=*
```

### 4. Setup Frontend (1 minute)

```bash
cd chatbot-widget
npm install

# Create .env file
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
```

### 5. Start Services

**Terminal 1 - Backend:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd chatbot-widget
npm run dev
```

### 6. Access Your Application

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:8000/admin
- **Chatbot Widget**: http://localhost:5173

### 7. First Steps

1. **Login to Admin Panel**
   - Go to http://localhost:8000/admin
   - Login with your admin credentials

2. **Add Knowledge Base**
   - Go to "Knowledge Base" tab
   - Upload a PDF or crawl a website
   - Wait for ingestion to complete

3. **Test Chatbot**
   - Open http://localhost:5173
   - Start chatting!

4. **Customize Chatbot**
   - Go to "BOT UI" tab in admin panel
   - Customize colors, name, icon
   - Save and refresh widget

## Common First-Time Issues

### Issue: "Module not found"
**Solution**: Make sure virtual environment is activated and dependencies are installed

### Issue: "Database connection failed"
**Solution**: Check PostgreSQL is running and DATABASE_URL is correct

### Issue: "Gemini API error"
**Solution**: Verify GEMINI_API_KEY is correct and API is enabled

### Issue: "Frontend can't connect"
**Solution**: Check backend is running and VITE_API_BASE_URL matches backend URL

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [SCALING_GUIDE.md](SCALING_GUIDE.md) for production deployment
- Explore admin panel features
- Add your knowledge base content

## Getting API Keys

### Google Gemini API Key
1. Go to https://ai.google.dev/
2. Sign in with Google account
3. Create API key
4. Copy key to `.env` file

### Pinecone API Key
1. Go to https://www.pinecone.io/
2. Sign up for free account
3. Create an index
4. Copy API key and environment to `.env` file

## Production Deployment

For production deployment, see:
- [README.md - Deployment Section](README.md#-deployment)
- [SCALING_GUIDE.md](SCALING_GUIDE.md)

---

**Need Help?** Check the [Troubleshooting](README.md#-troubleshooting) section in README.md

