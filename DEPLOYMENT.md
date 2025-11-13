# Deployment Guide

Complete guide for deploying the Cache Digitech Chatbot application to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Manual Deployment](#manual-deployment)
5. [Production Configuration](#production-configuration)
6. [Monitoring & Health Checks](#monitoring--health-checks)
7. [Scaling](#scaling)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

- Python 3.11+
- Node.js 18+ (for building frontend)
- PostgreSQL 15+
- Docker & Docker Compose (for containerized deployment)
- Google Gemini API Key
- Pinecone API Key and Index

## Environment Setup

### 1. Copy Environment Template

```bash
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with your production values:

```bash
# Database
DATABASE_URL=postgresql+psycopg2://user:password@db_host:5432/chatbot_db

# API Keys
GEMINI_API_KEY=your_actual_gemini_api_key
PINECONE_API_KEY=your_actual_pinecone_api_key
PINECONE_INDEX=your_pinecone_index_name

# Security (IMPORTANT: Generate a strong secret!)
SESSION_SECRET_KEY=$(openssl rand -hex 32)

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# CORS
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 3. Generate Secure Session Secret

```bash
# Linux/Mac
openssl rand -hex 32

# Windows PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
```

## Docker Deployment (Recommended)

### Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your values

# 2. Start services
docker-compose up -d

# 3. Check logs
docker-compose logs -f backend

# 4. Verify health
curl http://localhost:8000/health
```

### Building Custom Image

```bash
# Build image
docker build -t chatbot-backend:latest .

# Run container
docker run -d \
  --name chatbot-backend \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/knowledge_base:/app/knowledge_base \
  chatbot-backend:latest
```

### Docker Compose Production

```bash
# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Manual Deployment

### 1. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd chatbot-widget
npm install
npm run build
cd ..
```

### 2. Database Setup

```bash
# Create database
createdb chatbot_db

# Run migrations (if using Alembic)
# alembic upgrade head
```

### 3. Start Application

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```cmd
start.bat
```

**Or manually:**
```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level INFO
```

## Production Configuration

### Using Systemd (Linux)

Create `/etc/systemd/system/chatbot.service`:

```ini
[Unit]
Description=Cache Digitech Chatbot API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/chatbot
Environment="PATH=/var/www/chatbot/.venv/bin"
ExecStart=/var/www/chatbot/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable chatbot
sudo systemctl start chatbot
sudo systemctl status chatbot
```

### Using Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # Static files
    location /static/ {
        alias /var/www/chatbot/chatbot-widget/dist/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Environment-Specific Settings

**Development:**
```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
WORKERS=1
```

**Production:**
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
WORKERS=4
ALLOWED_ORIGINS=https://yourdomain.com
```

## Monitoring & Health Checks

### Health Check Endpoint

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "database": "healthy",
  "service": "Cache Digitech Chatbot API",
  "version": "1.0.0"
}
```

### Monitoring Setup

**Prometheus Metrics** (if implemented):
```yaml
scrape_configs:
  - job_name: 'chatbot'
    static_configs:
      - targets: ['localhost:8000']
```

**Logging:**
- Application logs: Check stdout/stderr
- Access logs: Enabled with `--access-log` flag
- Error logs: Check application logs for exceptions

## Scaling

### Horizontal Scaling

1. **Load Balancer**: Use Nginx or cloud load balancer
2. **Multiple Workers**: Increase `WORKERS` environment variable
3. **Multiple Instances**: Run multiple containers/instances behind load balancer

### Database Scaling

- Use connection pooling (already configured)
- Consider read replicas for high read traffic
- Monitor connection pool usage

### Vector Database Scaling

- Pinecone automatically scales
- Monitor index size and query performance
- Consider multiple indexes for different knowledge bases

## Security Checklist

- [ ] Strong `SESSION_SECRET_KEY` (32+ characters)
- [ ] HTTPS enabled (SSL/TLS certificates)
- [ ] CORS configured with specific origins (not `*`)
- [ ] Database credentials secured
- [ ] API keys stored in environment variables (not code)
- [ ] Firewall rules configured
- [ ] Regular security updates
- [ ] Backup strategy implemented
- [ ] Logs don't contain sensitive information

## Troubleshooting

### Application Won't Start

1. Check environment variables:
   ```bash
   python -c "from app.db.session import DATABASE_URL; print('DB OK')"
   ```

2. Check database connection:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

3. Check logs:
   ```bash
   docker-compose logs backend
   # or
   journalctl -u chatbot -f
   ```

### Database Connection Issues

- Verify `DATABASE_URL` format
- Check database is running and accessible
- Verify network/firewall rules
- Check connection pool settings

### Frontend Widget Not Loading

1. Verify widget is built:
   ```bash
   ls chatbot-widget/dist/assets/
   ```

2. Check static file serving:
   ```bash
   curl http://localhost:8000/static/widget/assets/index.js
   ```

3. Rebuild if needed:
   ```bash
   cd chatbot-widget && npm run build
   ```

### Performance Issues

1. Increase workers:
   ```bash
   WORKERS=8 uvicorn app.main:app ...
   ```

2. Monitor resource usage:
   ```bash
   docker stats
   # or
   htop
   ```

3. Check database query performance
4. Monitor Pinecone query latency

## Backup & Recovery

### Database Backup

```bash
# Backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore
psql $DATABASE_URL < backup_20240101.sql
```

### File Backups

- `uploads/` - User uploaded files
- `knowledge_base/` - Knowledge base documents
- `.env` - Environment configuration (store securely!)

## Updates & Maintenance

### Updating Application

```bash
# Pull latest code
git pull

# Rebuild frontend
cd chatbot-widget && npm run build && cd ..

# Restart application
docker-compose restart backend
# or
systemctl restart chatbot
```

### Zero-Downtime Deployment

1. Use load balancer with health checks
2. Deploy new version to one instance
3. Verify health check passes
4. Gradually shift traffic
5. Update remaining instances

## Support

For issues or questions:
1. Check logs first
2. Verify environment configuration
3. Test health endpoint
4. Review this deployment guide

