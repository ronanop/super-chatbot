# Quick Deployment Guide

Fastest way to get your chatbot deployed to production.

## Option 1: Docker Compose (Easiest)

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env with your values

# 2. Start everything
docker-compose up -d

# 3. Check status
docker-compose ps
docker-compose logs -f backend

# 4. Access application
# Admin: http://localhost:8000/admin
# Embed: http://localhost:8000/embed
# Health: http://localhost:8000/health
```

## Option 2: Manual Deployment

```bash
# 1. Install dependencies
pip install -r requirements.txt
cd chatbot-widget && npm install && npm run build && cd ..

# 2. Configure environment
cp .env.example .env
# Edit .env

# 3. Start server
# Linux/Mac:
chmod +x start.sh && ./start.sh

# Windows:
start.bat

# Or manually:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Required Environment Variables

Minimum required in `.env`:

```bash
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname
GEMINI_API_KEY=your_key
PINECONE_API_KEY=your_key
PINECONE_INDEX=your_index
SESSION_SECRET_KEY=$(openssl rand -hex 32)
```

## Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","database":"healthy",...}
```

## Next Steps

1. Configure admin panel: `http://localhost:8000/admin`
2. Customize chatbot UI: Admin → BOT UI
3. Add knowledge base: Admin → Ingestion
4. Get embed code: Admin → App Settings → Embed Code

## Troubleshooting

- **Can't connect**: Check `DATABASE_URL` and database is running
- **Widget not loading**: Run `cd chatbot-widget && npm run build`
- **500 errors**: Check logs with `docker-compose logs` or server logs
- **CORS errors**: Set `ALLOWED_ORIGINS` in `.env`

For detailed deployment, see `DEPLOYMENT.md`

