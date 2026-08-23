# Quick Reference Guide

Fast commands for common tasks.

---

## Local Development

```bash
# Start everything
docker compose up --build

# Stop everything
docker compose down

# View logs
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f worker

# Access container shell
docker compose exec backend bash

# Run migrations
docker compose exec backend alembic upgrade head

# Run tests
docker compose exec backend pytest tests/

# Rebuild only backend
docker compose build backend
docker compose up -d backend

# Reset everything (WARNING: deletes data)
docker compose down -v
docker compose up --build
```

---

## Kubernetes - Viewing Status

```bash
# Get all resources
kubectl get all -n chatline

# Get pods with detailed view
kubectl get pods -n chatline -o wide

# Get services
kubectl get svc -n chatline

# Get ingress
kubectl get ingress -n chatline

# Watch pod updates (live)
kubectl get pods -n chatline -w

# Describe pod (for troubleshooting)
kubectl describe pod chatline-backend-xxx -n chatline

# Get logs from pod
kubectl logs chatline-backend-xxx -n chatline

# Get logs from all pods in deployment
kubectl logs -l app=chatline,component=backend -n chatline --tail=100

# Follow logs in real-time
kubectl logs -f deployment/chatline-backend -n chatline
```

---

## Kubernetes - Deployments

```bash
# Apply all manifests
kubectl apply -f deployment/k8s/

# Apply specific file
kubectl apply -f deployment/k8s/backend-deployment.yaml

# Create namespace only
kubectl apply -f deployment/k8s/namespace.yaml

# Create secrets (after updating secrets.yaml with real values)
kubectl apply -f deployment/k8s/secrets.yaml

# Update image manually
kubectl set image deployment/chatline-backend \
  backend=ghcr.io/your-org/chatline/backend:v1.2.0 \
  -n chatline

# Check rollout status
kubectl rollout status deployment/chatline-backend -n chatline

# Rollback to previous version
kubectl rollout undo deployment/chatline-backend -n chatline

# Scale deployment
kubectl scale deployment chatline-backend --replicas=5 -n chatline

# Restart deployment (forces pod recreation)
kubectl rollout restart deployment/chatline-backend -n chatline

# Delete deployment
kubectl delete deployment chatline-backend -n chatline

# View rollout history
kubectl rollout history deployment/chatline-backend -n chatline
```

---

## Kubernetes - Debugging

```bash
# Port forward to pod
kubectl port-forward pod/chatline-backend-xxx 8000:8000 -n chatline
# Then: curl http://localhost:8000/health

# Exec into pod
kubectl exec -it pod/chatline-backend-xxx -n chatline -- bash

# Check pod events
kubectl describe pod chatline-backend-xxx -n chatline

# Check HPA status
kubectl get hpa -n chatline

# View HPA metrics
kubectl get hpa chatline-backend-hpa -n chatline -w

# Check resource requests/limits
kubectl describe node node-name

# Get pod resource usage
kubectl top pods -n chatline

# Get node resource usage
kubectl top nodes
```

---

## Docker

```bash
# Build image
docker build -f deployment/docker/backend.Dockerfile -t chatline/backend:latest .

# Run container
docker run -p 8000:8000 chatline/backend:latest

# Tag image
docker tag chatline/backend:latest ghcr.io/your-org/chatline/backend:v1.0.0

# Push to registry
docker push ghcr.io/your-org/chatline/backend:v1.0.0

# View images
docker images

# Remove image
docker rmi chatline/backend:latest

# View image layers
docker history chatline/backend:latest

# Run container with env file
docker run --env-file .env -p 8000:8000 chatline/backend:latest

# Inspect image
docker inspect chatline/backend:latest
```

---

## Database

```bash
# Connect to database (from pod)
kubectl exec -it deployment/postgres -n chatline -- \
  psql -U postgres -d chatline

# Create migration
docker compose exec backend alembic revision --autogenerate -m "message"

# View migrations
docker compose exec backend alembic current
docker compose exec backend alembic history

# Apply migration
docker compose exec backend alembic upgrade head

# Rollback one migration
docker compose exec backend alembic downgrade -1

# Check PostgreSQL logs
kubectl logs deployment/postgres -n chatline

# Backup database
kubectl exec -it deployment/postgres -n chatline -- \
  pg_dump -U postgres chatline > backup.sql

# Restore database
kubectl exec -it deployment/postgres -n chatline -- \
  psql -U postgres chatline < backup.sql
```

---

## Redis

```bash
# Connect to Redis (from pod)
kubectl exec -it deployment/redis -n chatline -- redis-cli

# Common Redis commands (inside redis-cli)
PING                    # Test connection
KEYS *                  # List all keys
GET key_name           # Get value
DEL key_name           # Delete key
FLUSHDB                # Delete all keys
DBSIZE                 # Size of database
INFO                   # Server info

# Check Redis logs
kubectl logs deployment/redis -n chatline

# Monitor Redis commands (from pod)
kubectl exec -it deployment/redis -n chatline -- \
  redis-cli MONITOR
```

---

## Metrics & Monitoring

```bash
# Port forward to Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n monitoring

# Query metrics
curl http://localhost:9090/api/v1/query?query=http_requests_total

# View metrics in backend
curl http://localhost:8000/metrics | head -20

# Port forward to Grafana
kubectl port-forward svc/grafana 3000:3000 -n monitoring

# Check scrape targets
curl http://localhost:9090/api/v1/targets

# Get metric metadata
curl http://localhost:9090/api/v1/metadata
```

---

## Environment Variables

```bash
# View ConfigMap
kubectl get configmap chatline-config -n chatline -o yaml

# Edit ConfigMap
kubectl edit configmap chatline-config -n chatline

# View Secrets (base64 encoded)
kubectl get secrets chatline-secrets -n chatline -o yaml

# Decode secret value
kubectl get secret chatline-secrets -n chatline \
  -o jsonpath='{.data.JWT_SECRET_KEY}' | base64 -d

# Update secret
kubectl create secret generic chatline-secrets \
  --from-literal=JWT_SECRET_KEY=new-value \
  -n chatline --dry-run=client -o yaml | kubectl apply -f -
```

---

## Network & Ingress

```bash
# View ingress
kubectl get ingress -n chatline

# Describe ingress
kubectl describe ingress chatline-ingress -n chatline

# Get ingress IP
kubectl get ingress chatline-ingress -n chatline -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Test endpoint
curl -v https://chatline.example.com/api/health

# Check certificate status
kubectl describe certificate chatline-cert -n chatline

# View network policies
kubectl get networkpolicies -n chatline

# Describe network policy
kubectl describe networkpolicy chatline-network-policy -n chatline
```

---

## GitHub Actions CI/CD

```bash
# View workflow runs
gh run list --repo your-org/chatline

# View latest run
gh run list --repo your-org/chatline --limit=1

# View run details
gh run view {run-id} --repo your-org/chatline

# View workflow file
cat .github/workflows/ci-cd.yml

# Trigger workflow manually (if enabled)
gh workflow run ci-cd.yml --repo your-org/chatline

# Check workflow status
gh workflow list --repo your-org/chatline

# Re-run failed jobs
gh run rerun {run-id} --failed --repo your-org/chatline
```

---

## Sentry

```bash
# Check Sentry integration
curl -X POST \
  -H 'Content-Type: application/json' \
  -d '{"message":"test"}' \
  http://localhost:8000/api/test-sentry

# View Sentry releases
curl -X GET \
  -H "Authorization: Bearer {TOKEN}" \
  https://sentry.io/api/0/organizations/{org}/releases/

# Create Sentry release
curl -X POST \
  -H "Authorization: Bearer {TOKEN}" \
  https://sentry.io/api/0/organizations/{org}/releases/ \
  -d '{"version":"1.0.0"}'
```

---

## Common Tasks

### Deploy New Version

```bash
# 1. Build and push image
docker build -f deployment/docker/backend.Dockerfile \
  -t ghcr.io/your-org/chatline/backend:v1.1.0 .
docker push ghcr.io/your-org/chatline/backend:v1.1.0

# 2. Update deployment
kubectl set image deployment/chatline-backend \
  backend=ghcr.io/your-org/chatline/backend:v1.1.0 \
  -n chatline

# 3. Monitor rollout
kubectl rollout status deployment/chatline-backend -n chatline

# 4. Verify
kubectl get pods -n chatline
curl https://chatline.example.com/api/health
```

### Add New Secret

```bash
# 1. Create secret
kubectl create secret generic chatline-secrets \
  --from-literal=NEW_SECRET=value \
  -n chatline --dry-run=client -o yaml

# 2. Get all secrets
kubectl get secrets -n chatline

# 3. Redeploy to pick up new secret
kubectl rollout restart deployment/chatline-backend -n chatline
```

### Scale Backend Up

```bash
# Via kubectl
kubectl scale deployment chatline-backend --replicas=5 -n chatline

# Via HPA (automatic)
# Edit deployment and change HPA max replicas
kubectl edit hpa chatline-backend-hpa -n chatline
```

### View Recent Errors

```bash
# Backend logs with error filter
kubectl logs deployment/chatline-backend -n chatline | grep -i error

# Sentry (via API)
curl -H "Authorization: Bearer {TOKEN}" \
  "https://sentry.io/api/0/projects/{org}/{project}/events/?query=level:error"

# From pod
kubectl exec -it deployment/chatline-backend -n chatline -- \
  bash -c 'tail -100 /var/log/app.log | grep ERROR'
```

### Update Configuration

```bash
# 1. Update ConfigMap
kubectl edit configmap chatline-config -n chatline

# 2. Restart pods to pick up changes
kubectl rollout restart deployment/chatline-backend -n chatline

# 3. Verify changes applied
kubectl get configmap chatline-config -n chatline -o yaml
```

### View Real-Time Metrics

```bash
# Pod CPU/Memory
kubectl top pods -n chatline --sort-by=memory

# Node utilization
kubectl top nodes

# HPA metrics
kubectl get hpa -n chatline -w

# Database connections
kubectl exec -it deployment/postgres -n chatline -- \
  psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## Useful Aliases

Add to `~/.bash_profile` or `~/.zshrc`:

```bash
alias k=kubectl
alias kn='kubectl -n chatline'
alias kgp='kubectl get pods -n chatline'
alias kgs='kubectl get svc -n chatline'
alias kdp='kubectl describe pod -n chatline'
alias kl='kubectl logs -n chatline'
alias klf='kubectl logs -f -n chatline'
alias kx='kubectl exec -it -n chatline'
alias kaf='kubectl apply -f'
alias kdl='kubectl delete -n chatline'

# Examples:
# k get pods
# kn get pods
# kgp
# kl deployment/chatline-backend
# klf deployment/chatline-backend
# kx pod/chatline-backend-xxx -- bash
```

---

## Emergency Troubleshooting

```bash
# Pod won't start?
kubectl describe pod <pod-name> -n chatline

# Pod keeps restarting?
kubectl logs <pod-name> -n chatline --previous

# Database can't connect?
kubectl exec -it pod/chatline-backend-xxx -n chatline -- \
  curl $DATABASE_URL

# Out of memory?
kubectl top pods -n chatline --sort-by=memory
kubectl set resources deployment/chatline-backend \
  --limits=memory=2Gi -n chatline

# High CPU?
kubectl top pods -n chatline --sort-by=cpu
kubectl scale deployment/chatline-backend --replicas=5 -n chatline

# Network issues?
kubectl exec -it pod/chatline-backend-xxx -n chatline -- \
  curl http://chatline-backend:8000/health

# DNS not resolving?
kubectl exec -it pod/chatline-backend-xxx -n chatline -- nslookup kubernetes.default
```

---

## External Tools

Useful commands for external operations:

```bash
# Check DNS propagation
dig chatline.example.com @8.8.8.8

# Test HTTPS certificate
openssl s_client -connect chatline.example.com:443

# Check HTTP headers
curl -I https://chatline.example.com

# Benchmark API
ab -n 100 -c 10 https://chatline.example.com/api/health

# Load test with wrk
wrk -t12 -c400 -d30s https://chatline.example.com/api/health
```

---

## Most Important Commands (Top 10)

1. `docker compose up --build` - Start local stack
2. `kubectl get pods -n chatline` - View pod status
3. `kubectl logs deployment/chatline-backend -n chatline` - View logs
4. `kubectl apply -f deployment/k8s/` - Deploy to K8s
5. `kubectl rollout status deployment/chatline-backend -n chatline` - Monitor deployment
6. `kubectl describe pod <pod> -n chatline` - Troubleshoot pod
7. `kubectl set image deployment/chatline-backend backend=image:tag -n chatline` - Update image
8. `kubectl scale deployment/chatline-backend --replicas=5 -n chatline` - Scale manually
9. `curl https://chatline.example.com/api/health` - Test endpoint
10. `kubectl port-forward pod/<pod> 8000:8000 -n chatline` - Debug locally

---

**Keep this file bookmarked for quick reference during deployment and operations!**
