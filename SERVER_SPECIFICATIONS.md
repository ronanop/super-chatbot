# Server Specifications Guide

## Recommended Server Specifications

### 🚀 **Initial Deployment (Low-Medium Traffic)**

#### **Option 1: Budget-Friendly Start**
```
CPU: 2 vCPU cores
RAM: 4 GB
Storage: 40 GB SSD
Network: 1 Gbps
OS: Ubuntu 22.04 LTS

Estimated Cost: $10-20/month (DigitalOcean, Linode, Vultr)
```

**Suitable for:**
- 10-50 concurrent users
- ~100-500 requests/day
- Testing and initial launch
- Small to medium businesses

**Limitations:**
- May struggle with heavy PDF processing
- Limited concurrent connections
- May need upgrade if traffic grows

---

#### **Option 2: Recommended Production Start** ⭐
```
CPU: 4 vCPU cores
RAM: 8 GB
Storage: 80 GB SSD
Network: 1 Gbps
OS: Ubuntu 22.04 LTS

Estimated Cost: $40-60/month (DigitalOcean, Linode, AWS EC2 t3.medium)
```

**Suitable for:**
- 50-200 concurrent users
- ~1,000-5,000 requests/day
- Production deployment
- Medium businesses

**Why this is recommended:**
- Handles 4 workers comfortably
- Enough RAM for PostgreSQL + Python processes
- Good balance of cost and performance
- Room to grow

---

#### **Option 3: High-Performance Start**
```
CPU: 8 vCPU cores
RAM: 16 GB
Storage: 160 GB SSD
Network: 2 Gbps
OS: Ubuntu 22.04 LTS

Estimated Cost: $80-120/month (DigitalOcean, AWS EC2 t3.large)
```

**Suitable for:**
- 200-500 concurrent users
- ~10,000+ requests/day
- High-traffic production
- Enterprise deployments

---

## Resource Breakdown

### **CPU Requirements**
- **Backend (FastAPI)**: 1-2 cores per worker
  - Default: 4 workers = 4-8 cores recommended
  - Each request: ~100-500ms processing time
  - Embedding generation: CPU-intensive

- **PostgreSQL**: 1-2 cores
  - Database queries are relatively lightweight
  - Connection pooling helps

- **System overhead**: 0.5-1 core
  - OS, monitoring, logging

**Total CPU needed:**
- Minimum: 2 cores (single worker, small DB)
- Recommended: 4 cores (4 workers, comfortable)
- Optimal: 8 cores (scaling room)

---

### **RAM Requirements**

#### **Backend Application**
- Python/FastAPI: ~200-400 MB per worker
  - 4 workers = ~800 MB - 1.6 GB
- Embeddings processing: ~100-200 MB
- Auto-training: ~100-200 MB (background)
- **Total Backend: ~1-2 GB**

#### **PostgreSQL Database**
- Base: ~200-500 MB
- Connection pool: ~100-200 MB
- Query cache: ~200-500 MB
- **Total PostgreSQL: ~500 MB - 1.2 GB**

#### **System & Other**
- OS: ~500 MB - 1 GB
- Docker (if used): ~200-500 MB
- Monitoring/logging: ~100-200 MB
- **Total System: ~800 MB - 1.7 GB**

**Total RAM needed:**
- Minimum: 4 GB (tight, may swap)
- Recommended: 8 GB (comfortable)
- Optimal: 16 GB (headroom for growth)

---

### **Storage Requirements**

#### **Application Files**
- Python code: ~100 MB
- Frontend build: ~10-20 MB
- Dependencies: ~500 MB - 1 GB
- **Total App: ~1 GB**

#### **PostgreSQL Database**
- Initial: ~100-500 MB
- Growth: ~10-50 MB/month (chat logs, sessions)
- **Estimated: ~1-5 GB after 1 year**

#### **Uploads & Knowledge Base**
- Header images: ~10-50 MB
- PDF documents: ~100 MB - 1 GB
- Scraped content: ~100-500 MB
- **Total Files: ~500 MB - 2 GB**

#### **System & Logs**
- OS: ~5-10 GB
- Logs: ~100-500 MB/month
- Docker images: ~1-2 GB

**Total Storage needed:**
- Minimum: 40 GB (tight)
- Recommended: 80 GB (comfortable)
- Optimal: 160 GB (room for growth)

---

### **Network Requirements**

#### **Bandwidth**
- Average request: ~5-10 KB (request) + 1-5 KB (response)
- Chat messages: ~1-2 KB each
- File uploads: ~1-10 MB per file
- Static files: ~100-500 KB initial load

**Bandwidth needed:**
- Minimum: 100 Mbps
- Recommended: 1 Gbps (standard)
- Optimal: 2+ Gbps (high traffic)

---

## Cloud Provider Recommendations

### **DigitalOcean**
```
Droplet: 4 vCPU, 8 GB RAM, 160 GB SSD
Cost: ~$48/month
Pros: Simple, predictable pricing, good performance
Cons: Limited regions
```

### **AWS EC2**
```
Instance: t3.medium (2 vCPU, 4 GB) or t3.large (2 vCPU, 8 GB)
Cost: ~$30-60/month (varies by region)
Pros: Global infrastructure, many services
Cons: Complex pricing, can get expensive
```

### **Google Cloud Platform**
```
Instance: e2-medium (2 vCPU, 4 GB) or e2-standard-4 (4 vCPU, 16 GB)
Cost: ~$30-100/month
Pros: Good integration with Gemini API
Cons: Complex pricing
```

### **Linode**
```
Instance: Shared CPU 4GB or Dedicated 8GB
Cost: ~$24-48/month
Pros: Simple, good performance
Cons: Smaller provider
```

### **Vultr**
```
Instance: Regular Performance 4 vCPU, 8 GB
Cost: ~$40/month
Pros: Good performance, competitive pricing
Cons: Smaller provider
```

---

## Database Hosting Options

### **Option 1: Same Server** (Budget-Friendly)
- Run PostgreSQL on same server
- **Pros**: Free, simple setup
- **Cons**: Shares resources, harder to scale
- **Best for**: Initial deployment, low traffic

### **Option 2: Managed Database** (Recommended)
- **DigitalOcean Managed PostgreSQL**: $15-30/month
- **AWS RDS**: $15-50/month
- **Google Cloud SQL**: $20-60/month
- **Pros**: Automatic backups, scaling, monitoring
- **Cons**: Additional cost
- **Best for**: Production, growing traffic

---

## External Services (No Server Resources Needed)

### **Google Gemini API**
- Runs on Google's infrastructure
- Pay-per-use pricing
- No server resources needed

### **Pinecone Vector Database**
- Fully managed service
- Runs on Pinecone's infrastructure
- Pay-per-use pricing
- No server resources needed

---

## Recommended Initial Setup

### **Budget-Conscious Setup**
```
Server: 2 vCPU, 4 GB RAM, 40 GB SSD ($10-20/month)
Database: Same server PostgreSQL (Free)
Total: ~$10-20/month

Handles: 10-50 concurrent users
```

### **Recommended Production Setup** ⭐
```
Server: 4 vCPU, 8 GB RAM, 80 GB SSD ($40-60/month)
Database: Managed PostgreSQL ($20-30/month)
Total: ~$60-90/month

Handles: 50-200 concurrent users
```

### **High-Performance Setup**
```
Server: 8 vCPU, 16 GB RAM, 160 GB SSD ($80-120/month)
Database: Managed PostgreSQL ($40-60/month)
Load Balancer: $10-20/month
Total: ~$130-200/month

Handles: 200-500+ concurrent users
```

---

## Scaling Path

### **Phase 1: Initial Launch** (Month 1-3)
- Start with: 4 vCPU, 8 GB RAM
- Monitor usage and performance
- Expected: 10-100 users/day

### **Phase 2: Growth** (Month 4-6)
- Upgrade to: 8 vCPU, 16 GB RAM
- Add managed database
- Expected: 100-500 users/day

### **Phase 3: Scale** (Month 7+)
- Multiple servers + load balancer
- Separate database server
- CDN for static files
- Expected: 500+ users/day

---

## Cost Optimization Tips

1. **Start Small**: Begin with minimum specs, upgrade as needed
2. **Use Reserved Instances**: 30-50% savings (AWS, GCP)
3. **Monitor Usage**: Right-size based on actual usage
4. **Use Spot Instances**: 50-90% savings (for non-critical workloads)
5. **Optimize Database**: Use connection pooling, query optimization
6. **CDN for Static Files**: Reduce server load

---

## Monitoring & Alerts

### **Key Metrics to Monitor**
- CPU usage (should stay < 70%)
- RAM usage (should stay < 80%)
- Disk usage (should stay < 80%)
- Response times (< 2 seconds)
- Error rates (< 1%)
- Database connections (< 80% of max)

### **When to Upgrade**
- CPU consistently > 70%
- RAM consistently > 80%
- Response times increasing
- High error rates
- Database connection pool exhausted

---

## Quick Start Recommendations

### **For Testing/Development**
- **2 vCPU, 4 GB RAM** - $10-20/month
- Same server PostgreSQL
- **Total: ~$10-20/month**

### **For Production Launch** ⭐
- **4 vCPU, 8 GB RAM** - $40-60/month
- Managed PostgreSQL - $20-30/month
- **Total: ~$60-90/month**

### **For High Traffic**
- **8 vCPU, 16 GB RAM** - $80-120/month
- Managed PostgreSQL - $40-60/month
- Load Balancer - $10-20/month
- **Total: ~$130-200/month**

---

## Summary

**Minimum Viable:**
- 2 vCPU, 4 GB RAM, 40 GB SSD
- Cost: ~$10-20/month
- Handles: 10-50 users/day

**Recommended Start:** ⭐
- 4 vCPU, 8 GB RAM, 80 GB SSD
- Cost: ~$60-90/month (with managed DB)
- Handles: 50-200 users/day

**High Performance:**
- 8 vCPU, 16 GB RAM, 160 GB SSD
- Cost: ~$130-200/month (with managed DB + LB)
- Handles: 200-500+ users/day

**Remember:** You can always start small and scale up as your traffic grows!

