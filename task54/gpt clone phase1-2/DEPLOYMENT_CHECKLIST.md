# Production Deployment Checklist

Complete checklist for deploying Chatline to production.

---

## Pre-Deployment

### Infrastructure Setup
- [ ] Kubernetes cluster created and configured
- [ ] Container registry set up (ECR, GCR, GitHub)
- [ ] Domain name registered
- [ ] DNS provider ready (Cloudflare, Route 53, etc.)
- [ ] SSL certificate authority ready (Let's Encrypt, AWS ACM)

### Access & Credentials
- [ ] kubectl configured and tested
- [ ] Docker credentials configured
- [ ] Git repository access verified
- [ ] GitHub secrets configured (KUBECONFIG, registry credentials)
- [ ] Cloud provider credentials stored securely

### Environment Files
- [ ] `.env.example` reviewed and understood
- [ ] `deployment/k8s/secrets.example.yaml` reviewed
- [ ] Production values prepared for all environment variables

---

## Database Setup

### PostgreSQL
- [ ] Database instance created or Helm chart deployed
- [ ] pgvector extension installed
- [ ] Connection pooling configured (PgBouncer or similar)
- [ ] Backups configured and tested
- [ ] Backup retention policy defined (e.g., 30 days)
- [ ] Point-in-time recovery tested
- [ ] Performance tuning applied
- [ ] Monitoring alerts set up

### Alembic Migrations
- [ ] All migrations tested locally
- [ ] Migration order verified
- [ ] Rollback tested
- [ ] Initial schema applied: `alembic upgrade head`

---

## Redis Setup

### Redis Instance
- [ ] Redis instance created or deployed
- [ ] Memory limits configured
- [ ] Persistence enabled (if needed for job queues)
- [ ] Password set and stored securely
- [ ] Connection string verified
- [ ] Failover configured (if high availability needed)
- [ ] Monitoring alerts set up

---

## Storage Setup

### Object Storage (S3/R2/MinIO)
- [ ] S3 bucket created
- [ ] Access keys generated and stored securely
- [ ] Bucket versioning enabled
- [ ] Lifecycle policies configured (if needed)
- [ ] CORS configured for frontend
- [ ] IAM policies restricted (principle of least privilege)
- [ ] Encryption enabled
- [ ] Public access blocked

### Buckets
- [ ] `chatline-documents` - for uploaded documents
- [ ] Other buckets as needed

---

## Docker Images

### Build & Push
- [ ] Backend image built locally and tested
- [ ] Frontend image built locally and tested
- [ ] Worker image built locally and tested
- [ ] Images tagged with version (e.g., `v1.0.0`)
- [ ] Images pushed to registry
- [ ] Image digests verified
- [ ] Image vulnerability scans passed

### Testing
- [ ] Each image runs successfully locally
- [ ] Health checks work
- [ ] Environment variables read correctly
- [ ] Logs output correctly
- [ ] Image sizes are reasonable

---

## Kubernetes Preparation

### Manifests
- [ ] Namespace manifest reviewed
- [ ] ConfigMap values updated for production
- [ ] Secrets file created with real values (from `secrets.example.yaml`)
- [ ] Ingress hostname updated to production domain
- [ ] Resource limits appropriate for your cluster
- [ ] All manifests validated with `kubectl --dry-run`

### Secrets
- [ ] JWT_SECRET_KEY generated (openssl rand -hex 32)
- [ ] DATABASE_URL configured (postgres connection string)
- [ ] REDIS_URL configured
- [ ] GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET configured (if OAuth enabled)
- [ ] GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET configured (if OAuth enabled)
- [ ] S3_ACCESS_KEY and S3_SECRET_KEY configured
- [ ] STRIPE_SECRET_KEY configured (if payments enabled)
- [ ] STRIPE_WEBHOOK_SECRET configured
- [ ] SENTRY_DSN configured
- [ ] SMTP_PASSWORD configured (if email enabled)

### Certificates
- [ ] cert-manager installed in cluster
- [ ] ClusterIssuer configured for Let's Encrypt
- [ ] Certificate request manifest ready

---

## Network & DNS

### Cloudflare Setup (if using)
- [ ] Domain added to Cloudflare
- [ ] Nameservers updated at registrar
- [ ] DNS records created (A records for frontend and API)
- [ ] SSL/TLS mode set to "Full (strict)"
- [ ] "Always Use HTTPS" enabled
- [ ] WAF rules configured
- [ ] Rate limiting rules configured
- [ ] Bot management enabled
- [ ] Page cache configured
- [ ] Security headers configured

### Alternative DNS (if not using Cloudflare)
- [ ] DNS A records created pointing to load balancer
- [ ] TTL set appropriately (300-3600 seconds)
- [ ] DNS propagation verified

### Ingress Controller
- [ ] nginx-ingress or equivalent installed
- [ ] Ingress controller scaled appropriately
- [ ] Service load balancer configured
- [ ] External IP/hostname assigned

---

## Monitoring & Observability Setup

### Prometheus
- [ ] Prometheus deployed in cluster (or externally)
- [ ] Scrape config created for backend (/metrics endpoint)
- [ ] Persistent volume configured for metrics storage
- [ ] Data retention configured (typically 15 days)
- [ ] Prometheus accessible on internal network

### Grafana (optional)
- [ ] Grafana deployed
- [ ] Prometheus data source configured
- [ ] Dashboards imported/created:
  - [ ] Kubernetes cluster dashboard
  - [ ] Backend API metrics
  - [ ] Database metrics
  - [ ] Worker jobs metrics
- [ ] Alerts configured for critical metrics

### Sentry
- [ ] Sentry project created (sentry.io)
- [ ] DSN copied to secrets
- [ ] Alert rules configured
- [ ] Slack integration (if desired)
- [ ] Team members added
- [ ] Notification preferences set

### Logging
- [ ] Log aggregation solution set up (ELK, CloudWatch, etc.)
- [ ] Backend logs collected
- [ ] Log retention policy configured
- [ ] Search/filter indexes configured

---

## Application Configuration

### Email (if using)
- [ ] SMTP server configured
- [ ] SMTP credentials stored securely
- [ ] Test email sent and verified
- [ ] Email templates configured

### OAuth (if using)
- [ ] Google OAuth app created (console.cloud.google.com)
- [ ] GitHub OAuth app created (github.com/settings/developers)
- [ ] Redirect URIs configured correctly
- [ ] Credentials stored securely

### Stripe (if using)
- [ ] Stripe account created (stripe.com)
- [ ] API keys stored securely
- [ ] Webhook endpoint configured
- [ ] Webhook secret stored securely
- [ ] Product/pricing configured
- [ ] Tax rates configured (if needed)

---

## Security & Compliance

### Network Security
- [ ] Network policies applied (Kubernetes)
- [ ] Firewall rules configured
- [ ] API endpoints protected by rate limiting
- [ ] CORS configured (only allowed origins)
- [ ] HTTPS only (HTTP redirects to HTTPS)

### Application Security
- [ ] Password hashing verified (bcrypt)
- [ ] JWT secrets strong enough
- [ ] API keys rotated
- [ ] Sensitive data not logged
- [ ] SQL injection protection verified
- [ ] XSS protection headers present
- [ ] CSRF protection enabled

### Data Protection
- [ ] Data encryption at rest enabled
- [ ] Data encryption in transit (TLS 1.2+)
- [ ] Database backups encrypted
- [ ] Sensitive backups restricted access
- [ ] GDPR compliance measures in place

### Access Control
- [ ] RBAC policies configured
- [ ] Service accounts created
- [ ] Admin access restricted
- [ ] Audit logging enabled
- [ ] Access logs monitored

---

## Testing & Validation

### Local Testing
- [ ] All services start correctly: `docker compose up --build`
- [ ] Frontend loads: http://localhost:5173
- [ ] Backend health: curl http://localhost:8000/health
- [ ] Readiness: curl http://localhost:8000/ready
- [ ] API endpoints respond correctly
- [ ] Database migrations work
- [ ] Redis connectivity verified
- [ ] S3/MinIO connectivity verified
- [ ] Emails send (if configured)
- [ ] OAuth login tested (if configured)

### Kubernetes Testing
- [ ] Dry-run validation: `kubectl apply -f deployment/k8s/ --dry-run=client`
- [ ] All manifests applied successfully
- [ ] Pods become ready within expected time
- [ ] Services have endpoints
- [ ] Ingress routes traffic correctly
- [ ] Health checks pass
- [ ] Logs are generated properly
- [ ] Metrics are collected

### Endpoint Testing
- [ ] `GET /health` returns 200
- [ ] `GET /ready` returns 200 (when ready)
- [ ] `GET /metrics` returns Prometheus format
- [ ] API endpoints respond with correct status codes
- [ ] Error handling works correctly
- [ ] Rate limiting works

### Load Testing (optional)
- [ ] Load test baseline established
- [ ] HPA scaling verified
- [ ] Database handles load
- [ ] No memory leaks detected
- [ ] Response times acceptable

---

## Deployment

### Pre-Deployment Checklist
- [ ] All above items completed
- [ ] Deployment plan documented
- [ ] Rollback plan documented
- [ ] Team notified of deployment window
- [ ] Monitoring dashboards ready
- [ ] On-call engineer standing by

### Deployment Steps
```bash
# 1. Create namespace and config
kubectl apply -f deployment/k8s/namespace.yaml
kubectl apply -f deployment/k8s/configmap.yaml

# 2. Create secrets
kubectl apply -f deployment/k8s/secrets.yaml

# 3. Apply database migrations (if needed)
kubectl exec -it deployment/chatline-backend -n chatline -- \
  alembic upgrade head

# 4. Deploy applications
kubectl apply -f deployment/k8s/backend-deployment.yaml
kubectl apply -f deployment/k8s/frontend-deployment.yaml
kubectl apply -f deployment/k8s/worker-deployment.yaml

# 5. Configure networking
kubectl apply -f deployment/k8s/ingress.yaml
kubectl apply -f deployment/k8s/hpa.yaml

# 6. Verify deployment
kubectl get pods -n chatline
kubectl get services -n chatline
kubectl get ingress -n chatline
```

### Post-Deployment Validation
- [ ] All pods are running: `kubectl get pods -n chatline`
- [ ] All services have endpoints: `kubectl get endpoints -n chatline`
- [ ] Ingress has IP address: `kubectl get ingress -n chatline`
- [ ] Frontend loads at custom domain
- [ ] API responds at custom domain
- [ ] Health checks pass
- [ ] Readiness checks pass
- [ ] No error logs in any pod
- [ ] Metrics being collected
- [ ] User can log in
- [ ] User can create chat
- [ ] User can send message

---

## Post-Deployment

### Monitoring
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboards loading
- [ ] Sentry receiving errors (test error if no real ones)
- [ ] Logs being aggregated
- [ ] Alerts configured and tested

### Performance
- [ ] Response times acceptable
- [ ] No timeouts or errors
- [ ] Database queries performant
- [ ] Memory usage stable
- [ ] CPU usage normal

### Scaling
- [ ] HPA configured and active
- [ ] Metrics being collected for HPA
- [ ] Manual scaling tested
- [ ] Rolling updates work correctly

### Backups
- [ ] Database backups running
- [ ] Backup verification scheduled
- [ ] Restore procedure documented

### Documentation
- [ ] Runbooks created for common issues
- [ ] Emergency procedures documented
- [ ] Team trained on deployment
- [ ] Incident response plan reviewed
- [ ] Change log updated

---

## Ongoing Operations

### Daily
- [ ] Monitor error rates in Sentry
- [ ] Check pod health
- [ ] Review performance metrics
- [ ] Respond to alerts

### Weekly
- [ ] Review logs for anomalies
- [ ] Check backup status
- [ ] Review user feedback
- [ ] Update security patches

### Monthly
- [ ] Performance tuning
- [ ] Cost analysis and optimization
- [ ] Security audit
- [ ] Capacity planning
- [ ] Team retrospective

### Quarterly
- [ ] Major version upgrades (if planned)
- [ ] Disaster recovery test
- [ ] Security audit (external)
- [ ] Architecture review
- [ ] Strategic planning

---

## Rollback Plan

If deployment has critical issues:

```bash
# 1. Scale down current deployment
kubectl scale deployment chatline-backend --replicas=0 -n chatline

# 2. Revert to previous image
kubectl set image deployment/chatline-backend \
  backend=ghcr.io/your-org/chatline/backend:v1.0.0 \
  -n chatline

# 3. Scale back up
kubectl scale deployment chatline-backend --replicas=3 -n chatline

# 4. Monitor
kubectl rollout status deployment/chatline-backend -n chatline
```

Or use Git rollback:
```bash
git revert <commit-hash>
git push origin main
# GitHub Actions will automatically redeploy
```

---

## Success Criteria

Deployment is successful when:

✅ All pods are running and healthy
✅ All services are accessible
✅ API endpoints responding correctly
✅ Database is accessible
✅ User can log in and use application
✅ No critical errors in logs
✅ Monitoring and alerting working
✅ Performance is acceptable (< 200ms API latency)
✅ Zero downtime achieved
✅ Team is comfortable with new state

---

## Sign-Off

- [ ] DevOps Lead: _________________ Date: _______
- [ ] Backend Lead: ________________ Date: _______
- [ ] Frontend Lead: _______________ Date: _______
- [ ] Product Manager: _____________ Date: _______

---

**Good luck with your deployment! 🚀**
