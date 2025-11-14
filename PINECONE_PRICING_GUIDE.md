# Pinecone Pricing Guide

## Pinecone Pricing Plans (2024)

### 🆓 **Starter Plan (Free Tier)**

**Included:**
- **2 GB** index storage
- **2 million** write units (vector upserts)
- **1 million** read units (queries)
- Access to embedding models
- Access to reranking models
- **1 project**
- Community support

**Limitations:**
- Single project only
- No backup/restore
- No RBAC (Role-Based Access Control)
- No SLA guarantee

**Best for:**
- Development and testing
- Small applications
- Learning and prototyping
- Initial deployment (< 1000 queries/day)

**Cost: $0/month**

---

### 💼 **Standard Plan (Production)**

**Pricing:**
- **Minimum: $50/month**
- Pay-as-you-go for usage beyond included limits

**Included Features:**
- Multiple projects
- Multiple users
- SAML SSO
- Backup and restore
- Role-based access control (RBAC)
- Bulk import
- Standard support

**Usage-Based Pricing:**
- **Storage**: ~$0.096 per GB/month
- **Reads (Queries)**: ~$0.0001 per query
- **Writes (Upserts)**: ~$0.0001 per write

**Best for:**
- Production applications
- Medium to large scale
- Multiple team members
- Need for backups and RBAC

**Cost: $50+/month** (minimum $50, then pay-as-you-go)

---

### 🏢 **Enterprise Plan**

**Pricing:**
- **Minimum: $500/month**
- Custom pricing for additional usage

**Includes Standard Plan features plus:**
- **99.95% uptime SLA**
- Private networking
- Customer-managed encryption keys
- Audit logs
- Service accounts
- Admin APIs
- HIPAA compliance
- Premium support

**Best for:**
- Mission-critical applications
- Large enterprises
- Compliance requirements
- High availability needs

**Cost: $500+/month**

---

### 🔒 **Dedicated Plan**

**Pricing:**
- Custom pricing based on requirements

**Includes Enterprise features plus:**
- Bring-your-own-cloud (BYOC)
- Dedicated infrastructure
- Premium support
- Custom SLAs

**Best for:**
- Maximum security requirements
- Very large scale
- Custom infrastructure needs

**Cost: Custom pricing**

---

## Standard Trial (21 Days)

**What you get:**
- **$300 in credits** (21 days)
- Access to Standard plan features
- Full production capabilities
- No credit card required initially

**Best for:**
- Testing production features
- Evaluating before committing
- Initial deployment testing

---

## Cost Estimation for Your Chatbot Application

### **Usage Scenarios**

#### **Scenario 1: Small Application (Free Tier)**
```
Users: 10-50/day
Queries: ~100-500/day
Writes: ~10-50/day (knowledge base updates)

Monthly Usage:
- Queries: ~3,000-15,000/month
- Writes: ~300-1,500/month
- Storage: ~100-500 MB

Cost: $0/month (within free tier limits)
```

#### **Scenario 2: Medium Application (Standard Plan)**
```
Users: 50-200/day
Queries: ~500-2,000/day
Writes: ~50-200/day

Monthly Usage:
- Queries: ~15,000-60,000/month
- Writes: ~1,500-6,000/month
- Storage: ~500 MB - 2 GB

Cost: $50/month (minimum) + minimal overage
Total: ~$50-60/month
```

#### **Scenario 3: Large Application (Standard Plan)**
```
Users: 200-1,000/day
Queries: ~2,000-10,000/day
Writes: ~200-1,000/day

Monthly Usage:
- Queries: ~60,000-300,000/month
- Writes: ~6,000-30,000/month
- Storage: ~2-10 GB

Cost: $50/month (minimum) + usage overage
- Storage: ~$0.20-1.00/month
- Queries: ~$6-30/month
- Writes: ~$0.60-3.00/month
Total: ~$57-84/month
```

#### **Scenario 4: Very Large Application (Enterprise)**
```
Users: 1,000+/day
Queries: ~10,000+/day
Writes: ~1,000+/day

Monthly Usage:
- Queries: ~300,000+/month
- Writes: ~30,000+/month
- Storage: ~10+ GB

Cost: $500+/month (Enterprise minimum)
```

---

## How Your Application Uses Pinecone

### **Read Operations (Queries)**
- **When**: Every user query searches the knowledge base
- **Frequency**: 1 query per user message (with query expansion, can be 5-8 queries)
- **Cost**: ~$0.0001 per query

**Example:**
- 100 queries/day = ~3,000/month = **$0.30/month**
- 1,000 queries/day = ~30,000/month = **$3/month**
- 10,000 queries/day = ~300,000/month = **$30/month**

### **Write Operations (Upserts)**
- **When**: 
  - Uploading PDFs to knowledge base
  - Web crawling and ingesting content
  - Auto-training (adding learned conversations)
- **Frequency**: Depends on knowledge base updates
- **Cost**: ~$0.0001 per write

**Example:**
- 10 PDFs uploaded = ~1,000-5,000 writes = **$0.10-0.50**
- Auto-training: ~10-50 writes/day = ~300-1,500/month = **$0.03-0.15/month**

### **Storage**
- **What**: Vector embeddings of your knowledge base
- **Size**: ~1-2 KB per chunk (depends on embedding model)
- **Cost**: ~$0.096 per GB/month

**Example:**
- 1,000 chunks = ~1-2 MB
- 10,000 chunks = ~10-20 MB
- 100,000 chunks = ~100-200 MB
- 1,000,000 chunks = ~1-2 GB

**Storage Cost:**
- 100 MB = **$0.01/month**
- 1 GB = **$0.10/month**
- 10 GB = **$1/month**

---

## Cost Breakdown for Your Application

### **Initial Setup (Free Tier)**
```
Knowledge Base: ~100-500 PDFs
Chunks: ~10,000-50,000
Storage: ~10-50 MB

Monthly Usage:
- Queries: ~1,000-5,000/month
- Writes: ~100-500/month (initial uploads)
- Storage: ~10-50 MB

Cost: $0/month ✅
```

### **Small Production (Free Tier)**
```
Users: 20-50/day
Queries: ~200-500/day = ~6,000-15,000/month
Writes: ~20-50/month (updates)
Storage: ~50-200 MB

Cost: $0/month ✅ (within free tier)
```

### **Medium Production (Standard Plan)**
```
Users: 100-200/day
Queries: ~1,000-2,000/day = ~30,000-60,000/month
Writes: ~100-200/month
Storage: ~200 MB - 1 GB

Cost Breakdown:
- Base: $50/month
- Storage: ~$0.02-0.10/month
- Queries: ~$3-6/month
- Writes: ~$0.01-0.02/month

Total: ~$53-56/month
```

### **Large Production (Standard Plan)**
```
Users: 500-1,000/day
Queries: ~5,000-10,000/day = ~150,000-300,000/month
Writes: ~500-1,000/month
Storage: ~1-5 GB

Cost Breakdown:
- Base: $50/month
- Storage: ~$0.10-0.50/month
- Queries: ~$15-30/month
- Writes: ~$0.05-0.10/month

Total: ~$65-80/month
```

---

## Free Tier Limits & When You'll Exceed

### **Free Tier Limits:**
- **2 GB storage** ✅ (plenty for most applications)
- **2 million writes/month** ✅ (more than enough)
- **1 million queries/month** ✅ (good for ~33,000 queries/day)

### **When You'll Need Standard Plan:**

**You'll exceed free tier if:**
- **> 33,000 queries/day** (~1,000 queries/hour)
- **> 2 GB storage** (very large knowledge base)
- **Need multiple projects** (different chatbots)
- **Need backups** (production requirement)
- **Need RBAC** (team access control)

**For most applications:**
- Free tier is sufficient for **months or years**
- Only upgrade when you hit limits or need features

---

## Cost Optimization Tips

### 1. **Start with Free Tier**
- Use free tier for development and initial launch
- Monitor usage before upgrading
- Free tier is very generous

### 2. **Optimize Query Frequency**
- Current implementation: 5-8 queries per user message (query expansion)
- Consider caching frequent queries
- Reduce query expansion if not needed

### 3. **Optimize Storage**
- Remove unused knowledge base content
- Archive old content
- Use efficient chunking (current: ~1000 chars/chunk)

### 4. **Use Standard Trial**
- Get $300 credits for 21 days
- Test production features
- Evaluate before committing

### 5. **Monitor Usage**
- Track queries, writes, and storage
- Set up alerts before hitting limits
- Right-size based on actual usage

---

## Pricing Comparison

| Plan | Monthly Cost | Storage | Queries/Month | Writes/Month | Best For |
|------|-------------|---------|---------------|--------------|----------|
| **Starter (Free)** | $0 | 2 GB | 1M | 2M | Development, Small apps |
| **Standard** | $50+ | Unlimited | Unlimited | Unlimited | Production, Medium-Large |
| **Enterprise** | $500+ | Unlimited | Unlimited | Unlimited | Enterprise, Compliance |
| **Dedicated** | Custom | Custom | Custom | Custom | Maximum security |

---

## Recommendations for Your Application

### **Phase 1: Initial Launch** (Months 1-3)
- **Use Free Tier**
- Expected: 10-100 users/day
- Expected: ~500-5,000 queries/month
- **Cost: $0/month** ✅

### **Phase 2: Growth** (Months 4-6)
- **Use Free Tier** (if under limits)
- **Upgrade to Standard** if needed
- Expected: 100-500 users/day
- Expected: ~15,000-150,000 queries/month
- **Cost: $0-65/month**

### **Phase 3: Scale** (Month 7+)
- **Use Standard Plan**
- Expected: 500+ users/day
- Expected: ~150,000+ queries/month
- **Cost: $65-100/month**

---

## Summary

### **For Initial Deployment:**
- **Start with Free Tier** - $0/month
- More than enough for initial launch
- 1M queries/month = ~33,000 queries/day
- 2 GB storage = ~1-2 million chunks

### **When to Upgrade:**
- **> 33,000 queries/day** → Standard Plan ($50+/month)
- **> 2 GB storage** → Standard Plan ($50+/month)
- **Need backups/RBAC** → Standard Plan ($50+/month)

### **Expected Costs:**
- **Initial (Free Tier)**: $0/month
- **Small Production**: $0/month (free tier)
- **Medium Production**: $50-60/month
- **Large Production**: $65-100/month

**Bottom Line:** Pinecone's free tier is very generous. You can likely run your application for free for months or even years, depending on traffic. Only upgrade when you hit limits or need production features like backups and RBAC.

---

## Additional Resources

- **Pinecone Pricing Page**: https://www.pinecone.io/pricing/
- **Free Tier Details**: https://docs.pinecone.io/guides/get-started/free-tier
- **Standard Trial**: https://docs.pinecone.io/guides/organizations/manage-billing/standard-trial
- **Usage Calculator**: Check Pinecone dashboard for real-time usage

