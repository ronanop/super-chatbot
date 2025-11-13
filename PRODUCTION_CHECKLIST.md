# Production Deployment Checklist

Use this checklist to ensure your application is production-ready before deploying.

## Pre-Deployment

### Environment Configuration
- [ ] `.env` file created from `.env.example`
- [ ] All required environment variables set
- [ ] `SESSION_SECRET_KEY` is strong (32+ characters, randomly generated)
- [ ] Database credentials are secure
- [ ] API keys are valid and have proper permissions
- [ ] `ALLOWED_ORIGINS` configured (not `*` in production)
- [ ] `ENVIRONMENT=production` set

### Security
- [ ] Strong passwords for database and admin panel
- [ ] HTTPS/SSL certificates configured
- [ ] CORS origins restricted to your domain(s)
- [ ] Firewall rules configured
- [ ] `.env` file is in `.gitignore` (not committed)
- [ ] No hardcoded secrets in code
- [ ] Admin panel login credentials changed from defaults

### Application Build
- [ ] Frontend widget built (`npm run build`)
- [ ] `chatbot-widget/dist/` folder exists with assets
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Python virtual environment created and activated
- [ ] No build errors or warnings

### Database
- [ ] PostgreSQL database created
- [ ] Database migrations run (if applicable)
- [ ] Database connection tested
- [ ] Backup strategy configured
- [ ] Connection pooling configured

### Testing
- [ ] Health check endpoint works (`/health`)
- [ ] Admin panel accessible (`/admin`)
- [ ] Chatbot API responds (`/chat`)
- [ ] Embed endpoint works (`/embed`)
- [ ] Static files serve correctly (`/static/widget/`)
- [ ] Widget loads in browser
- [ ] Chatbot responds to messages
- [ ] Voice input works (if enabled)
- [ ] Form submission works (if enabled)

## Deployment

### Docker Deployment
- [ ] Docker image builds successfully
- [ ] `docker-compose.yml` configured correctly
- [ ] Environment variables passed to containers
- [ ] Volumes mounted correctly
- [ ] Containers start without errors
- [ ] Health checks pass

### Manual Deployment
- [ ] Server has required resources (CPU, RAM, disk)
- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed (for building)
- [ ] PostgreSQL accessible
- [ ] Application starts without errors
- [ ] Process manager configured (systemd, supervisor, etc.)
- [ ] Logs directory writable

### Network & Firewall
- [ ] Port 8000 (or configured port) open
- [ ] Database port accessible (if external)
- [ ] Reverse proxy configured (Nginx, etc.)
- [ ] SSL/TLS certificates valid
- [ ] Domain DNS configured

## Post-Deployment

### Verification
- [ ] Application accessible via domain
- [ ] Health check returns `200 OK`
- [ ] Admin panel login works
- [ ] Chatbot widget loads
- [ ] Chatbot responds correctly
- [ ] No errors in logs
- [ ] Performance is acceptable

### Monitoring
- [ ] Logging configured
- [ ] Error tracking set up (if applicable)
- [ ] Health check monitoring configured
- [ ] Resource usage monitoring
- [ ] Database monitoring
- [ ] Uptime monitoring

### Backup & Recovery
- [ ] Database backup automated
- [ ] File backups configured (`uploads/`, `knowledge_base/`)
- [ ] Backup restoration tested
- [ ] Recovery procedure documented

### Documentation
- [ ] Deployment process documented
- [ ] Environment variables documented
- [ ] Troubleshooting guide available
- [ ] Contact information for support

## Performance Optimization

- [ ] Worker count optimized (`WORKERS` environment variable)
- [ ] Database connection pool sized correctly
- [ ] Static files cached properly
- [ ] CDN configured (if applicable)
- [ ] Compression enabled (gzip)

## Security Hardening

- [ ] Regular security updates scheduled
- [ ] Dependencies updated (`pip list --outdated`, `npm outdated`)
- [ ] Security headers configured
- [ ] Rate limiting configured (if applicable)
- [ ] Input validation working
- [ ] SQL injection protection verified
- [ ] XSS protection verified

## Rollback Plan

- [ ] Previous version tagged/backed up
- [ ] Database migration rollback tested
- [ ] Rollback procedure documented
- [ ] Quick rollback script prepared

## Go-Live

- [ ] All checklist items completed
- [ ] Team notified of deployment
- [ ] Monitoring alerts configured
- [ ] Support team ready
- [ ] Documentation accessible

---

**After Deployment:**
1. Monitor logs for first 24 hours
2. Check error rates
3. Verify all features work
4. Monitor resource usage
5. Collect user feedback

