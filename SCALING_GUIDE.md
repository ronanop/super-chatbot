# Chatbot Traffic Capacity & Scaling Guide

## Current Architecture Capacity

### Estimated Traffic Capacity

**With Free Gemini API Tier:**
- **~10-15 requests/minute** (Gemini free tier limit)
- **~50-100 concurrent users** (if rate limits allow)
- **Bottleneck:** Gemini API rate limits

**With Paid Gemini API Tier:**
- **~300-360 requests/minute** (Gemini paid tier)
- **~200-500 concurrent users** (depending on response times)
- **Bottleneck:** Server resources and database connections

### Component Limits

1. **FastAPI/Uvicorn (Single Worker)**
   - Handles ~100-200 concurrent async requests
   - CPU-bound operations can reduce this

2. **Google Gemini API**
   - Free Tier: ~15 requests/minute
   - Paid Tier: ~360 requests/minute (varies by plan)
   - Check your quota: https://ai.google.dev/pricing

3. **Pinecone Vector Database**
   - Free Tier: ~100 queries/minute
   - Paid Tier: ~200+ queries/second
   - Check your plan limits

4. **PostgreSQL Database**
   - Default: ~100 concurrent connections
   - Can be increased with configuration

## Scaling Strategies

### 1. Immediate Improvements (No Code Changes)

#### Increase Gemini API Tier
```bash
# Upgrade your Google Cloud account
# Visit: https://ai.google.dev/pricing
# Paid tier allows 360+ RPM vs 15 RPM free
```

#### Run Multiple Workers
```bash
# Instead of single worker:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Use multiple workers:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
# Or use gunicorn with uvicorn workers:
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 2. Code-Level Improvements

#### Add Connection Pooling
Update `app/db/session.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,          # Number of connections to maintain
    max_overflow=40,      # Additional connections allowed
    pool_pre_ping=True,   # Verify connections before using
)
```

#### Add Rate Limiting
Install: `pip install slowapi`

Add to `app/main.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/chat")
@limiter.limit("10/minute")  # Per IP address
async def chat_endpoint(...):
    ...
```

#### Add Response Caching
Install: `pip install cachetools`

Cache common queries:
```python
from cachetools import TTLCache
import hashlib

# Cache Pinecone queries for 5 minutes
query_cache = TTLCache(maxsize=1000, ttl=300)

def _build_context_cached(query: str):
    cache_key = hashlib.md5(query.encode()).hexdigest()
    if cache_key in query_cache:
        return query_cache[cache_key]
    result = _build_context(query)
    query_cache[cache_key] = result
    return result
```

### 3. Infrastructure Scaling

#### Horizontal Scaling with Load Balancer

**Option A: Cloud Run / App Engine (Google Cloud)**
```yaml
# app.yaml for App Engine
runtime: python39
instance_class: F2
automatic_scaling:
  min_instances: 1
  max_instances: 10
  target_cpu_utilization: 0.6
```

**Option B: Docker + Kubernetes**
```dockerfile
# Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

**Option C: AWS App Runner / ECS**
- Auto-scales based on traffic
- Handles load balancing automatically

#### Database Scaling

**Managed PostgreSQL (Recommended)**
- **Google Cloud SQL**: Auto-scales connections
- **AWS RDS**: Can handle 1000+ connections
- **Supabase/Neon**: Serverless PostgreSQL

**Connection Pooling Service**
- Use **PgBouncer** or **PgPool** for connection pooling
- Reduces database load

### 4. Monitoring & Optimization

#### Add Performance Monitoring
```python
# Install: pip install prometheus-fastapi-instrumentator
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

#### Monitor Key Metrics
- Request latency (p50, p95, p99)
- Gemini API response times
- Database query times
- Error rates
- Concurrent user count

## Expected Capacity After Scaling

### Small Scale (Single Server, Paid Gemini)
- **~300-500 requests/minute**
- **~200-300 concurrent users**
- **Cost:** ~$50-100/month

### Medium Scale (Load Balanced, 3-5 Instances)
- **~1,000-2,000 requests/minute**
- **~500-1,000 concurrent users**
- **Cost:** ~$200-500/month

### Large Scale (Auto-scaling, 10+ Instances)
- **~5,000+ requests/minute**
- **~2,000+ concurrent users**
- **Cost:** ~$1,000+/month

## Quick Wins Checklist

- [ ] Upgrade Gemini API to paid tier
- [ ] Run multiple Uvicorn workers (`--workers 4`)
- [ ] Add connection pooling to PostgreSQL
- [ ] Implement rate limiting (prevent abuse)
- [ ] Add response caching for common queries
- [ ] Monitor API response times
- [ ] Set up error alerting
- [ ] Use managed database (Cloud SQL/RDS)
- [ ] Deploy to auto-scaling platform (Cloud Run/App Runner)
- [ ] Add CDN for static assets

## Cost Estimates

### Current Setup (Free Tier)
- **Server:** $0 (local) or $5-20/month (VPS)
- **Gemini API:** Free (limited)
- **Pinecone:** Free tier available
- **PostgreSQL:** $0 (local) or $10-50/month (managed)
- **Total:** ~$15-70/month

### Scaled Setup (Production)
- **Server:** $50-200/month (auto-scaling)
- **Gemini API:** $50-500/month (based on usage)
- **Pinecone:** $70-300/month (based on queries)
- **PostgreSQL:** $50-200/month (managed)
- **CDN:** $10-50/month
- **Total:** ~$230-1,250/month

## Next Steps

1. **Immediate:** Upgrade Gemini API tier and add workers
2. **Short-term:** Add rate limiting and connection pooling
3. **Medium-term:** Deploy to auto-scaling platform
4. **Long-term:** Implement caching and monitoring

## Monitoring Commands

```bash
# Check current server load
htop

# Monitor API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# Check database connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Monitor Gemini API usage
# Check Google Cloud Console > APIs & Services > Gemini API
```

