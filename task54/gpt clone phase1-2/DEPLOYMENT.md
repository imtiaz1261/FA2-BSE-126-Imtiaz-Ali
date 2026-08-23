# Deployment & Infrastructure Guide

Production-ready deployment infrastructure for Chatline AI SaaS platform with Docker, Kubernetes, CI/CD, monitoring, and scaling.

**Table of Contents**
- [Architecture](#architecture)
- [Local Development](#local-development)
- [Deployment](#deployment)
- [Kubernetes](#kubernetes)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       End Users                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │Cloudflare│ (CDN, DDoS protection, HTTPS)
                    │    CDN   │
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    ┌───▼───┐      ┌────▼────┐      ┌───▼───┐
    │Frontend│      │ Backend  │      │ Health│
    │Nginx   │      │ FastAPI  │      │ Check │
    │(React) │      │ API      │      │       │
    └───┬───┘      └────┬────┘      └───┬───┘
        │               │               │
        └───────┬───────┴───────┬───────┘
                │               │
        ┌───────▼────┐   ┌─────▼──────┐
        │ PostgreSQL  │   │   Redis    │
        │ + pgvector  │   │  (Cache)   │
        └────────────┘   └────────────┘
                │
        ┌───────▼──────────┐
        │  Worker Pool     │
        │  (RAG/Agents)    │
        └─────────────────┘
                │
        ┌───────▼──────────┐
        │  Object Storage  │
        │  (S3/R2/MinIO)   │
        └────────────────┘
```

### Component Breakdown

**Frontend**
- React SPA served through Nginx
- Static asset caching (Cloudflare CDN)
- SPA routing configured
- Security headers (HSTS, CSP, etc.)

**Backend API**
- FastAPI application with Uvicorn workers
- Gunicorn process manager (production)
- Health checks (/health, /ready endpoints)
- Structured JSON logging
- Prometheus metrics (/metrics)
- Sentry error tracking

**Worker Process**
- Separate RAG/Agent job processor
- Independent scaling from API
- Document ingestion and processing
- Embedding generation
- Agent sandbox execution

**Database**
- PostgreSQL with pgvector extension
- Connection pooling
- Async queries (asyncpg)
- Alembic migrations

**Redis**
- Caching layer
- Job queue management
- Rate limiting
- Session storage

**Object Storage**
- S3-compatible (AWS S3, Cloudflare R2, MinIO)
- Document uploads
- File artifacts

---

## Local Development

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/chatline.git
cd chatline

# Start complete local stack
docker compose up --build

# Access services
Frontend:  http://localhost:5173
Backend:   http://localhost:8000
Nginx:     http://localhost:80
MinIO:     http://localhost:9001
```

### Environment Setup

```bash
# Copy example env file
cp .env.example .env

# Edit with local values (or leave as-is for development)
# nano .env
```

### Services

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Frontend (Dev) | 5173 | http://localhost:5173 | React dev server |
| Backend | 8000 | http://localhost:8000 | FastAPI API |
| Nginx | 80 | http://localhost:80 | Production-like proxy |
| PostgreSQL | 5432 | localhost:5432 | Database |
| Redis | 6379 | localhost:6379 | Cache & queue |
| MinIO Console | 9001 | http://localhost:9001 | S3 management |
| MinIO API | 9000 | http://localhost:9000 | S3 API |

### Useful Commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# Execute commands in container
docker compose exec backend bash
docker compose exec backend python -m alembic upgrade head

# Stop and clean
docker compose down -v  # -v removes volumes

# Rebuild images
docker compose build --no-cache

# Run tests locally
docker compose exec backend pytest tests/
```

### Database Migrations

```bash
# Create new migration
docker compose exec backend alembic revision --autogenerate -m "add column"

# Apply migrations
docker compose exec backend alembic upgrade head

# Rollback
docker compose exec backend alembic downgrade -1
```

---

## Deployment

### Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, or self-managed)
- `kubectl` configured
- Container registry (ECR, GCR, GitHub Container Registry)
- Domain name
- SSL certificate (automated with cert-manager + Let's Encrypt)
- Secrets management configured

### Image Building

```bash
# Build backend image
docker build -f deployment/docker/backend.Dockerfile -t chatline/backend:latest .

# Build frontend image
docker build -f deployment/docker/frontend.Dockerfile -t chatline/frontend:latest .

# Build worker image
docker build -f deployment/docker/worker.Dockerfile -t chatline/worker:latest .

# Tag for registry
docker tag chatline/backend:latest ghcr.io/your-org/chatline/backend:latest
docker tag chatline/frontend:latest ghcr.io/your-org/chatline/frontend:latest
docker tag chatline/worker:latest ghcr.io/your-org/chatline/worker:latest

# Push to registry
docker push ghcr.io/your-org/chatline/backend:latest
docker push ghcr.io/your-org/chatline/frontend:latest
docker push ghcr.io/your-org/chatline/worker:latest
```

### Environment Configuration

1. **Create secrets file** (from example):
```bash
cp deployment/k8s/secrets.example.yaml deployment/k8s/secrets.yaml
# Edit with real values
nano deployment/k8s/secrets.yaml
```

2. **Update ConfigMap** values in `deployment/k8s/configmap.yaml`

3. **Update Ingress** hostname in `deployment/k8s/ingress.yaml`

---

## Kubernetes

### Deploy to Cluster

```bash
# Create namespace and secrets
kubectl apply -f deployment/k8s/namespace.yaml
kubectl apply -f deployment/k8s/configmap.yaml
kubectl apply -f deployment/k8s/secrets.yaml

# Deploy applications
kubectl apply -f deployment/k8s/backend-deployment.yaml
kubectl apply -f deployment/k8s/frontend-deployment.yaml
kubectl apply -f deployment/k8s/worker-deployment.yaml

# Deploy networking
kubectl apply -f deployment/k8s/ingress.yaml
kubectl apply -f deployment/k8s/hpa.yaml

# Verify deployment
kubectl get pods -n chatline
kubectl get services -n chatline
kubectl get ingress -n chatline
```

### Scaling

#### Horizontal Pod Autoscaling (HPA)

```bash
# View HPA status
kubectl get hpa -n chatline

# Manual scaling (if needed)
kubectl scale deployment chatline-backend --replicas=5 -n chatline
```

**Backend HPA:**
- Min: 2 pods, Max: 10 pods
- Scales on: CPU (70%), Memory (80%)
- Scale-up: Aggressive (100% increase)
- Scale-down: Conservative (50% decrease)

**Worker HPA:**
- Min: 1 pod, Max: 5 pods
- Scales on: CPU (75%), Memory (85%)
- More aggressive scale-up

**Frontend HPA:**
- Min: 2 pods, Max: 5 pods
- Conservative scaling

#### Metrics Server

Required for HPA. Install if not present:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Rolling Updates

```bash
# Update image
kubectl set image deployment/chatline-backend \
  backend=ghcr.io/your-org/chatline/backend:v1.2.0 \
  -n chatline

# Monitor rollout
kubectl rollout status deployment/chatline-backend -n chatline

# Rollback if needed
kubectl rollout undo deployment/chatline-backend -n chatline
```

### Pod Disruption Budgets

To prevent disruptions during cluster maintenance:

```bash
kubectl apply -f - <<EOF
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: chatline-backend-pdb
  namespace: chatline
spec:
  minAvailable: 1
  selector:
    matchLabels:
      component: backend
EOF
```

---

## Monitoring

### Prometheus

Scrape metrics from backend:

```yaml
scrape_configs:
  - job_name: 'chatline-backend'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - chatline
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
```

### Grafana

Import dashboard templates for Chatline metrics.

**Key metrics to monitor:**
- HTTP request latency (p50, p95, p99)
- Error rate (4xx, 5xx)
- Database query latency
- Redis hit ratio
- Worker job duration
- Active users
- Token usage

### Sentry

Visit [sentry.io](https://sentry.io) to set up error tracking:

1. Create project (Python)
2. Get DSN
3. Add to `.env.example` and Kubernetes secrets:
```
SENTRY_DSN=https://your-key@sentry.io/project-id
SENTRY_ENVIRONMENT=production
```

### Health Checks

```bash
# Liveness probe
curl http://localhost:8000/health
# Response: {"status":"healthy","service":"backend"}

# Readiness probe
curl http://localhost:8000/ready
# Response: {"status":"ready","service":"backend","database":"connected","timestamp":"..."}
```

---

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod chatline-backend-xxxx -n chatline

# Check logs
kubectl logs chatline-backend-xxxx -n chatline

# Previous logs (if crashed)
kubectl logs chatline-backend-xxxx -n chatline --previous
```

### Database Connection Issues

```bash
# Test database connection from pod
kubectl exec -it chatline-backend-0 -n chatline -- psql $DATABASE_URL

# Check connection pooling
kubectl exec -it chatline-backend-0 -n chatline -- curl localhost:8000/health
```

### Memory/CPU Issues

```bash
# Check resource usage
kubectl top pod -n chatline

# Increase limits in deployment
kubectl set resources deployment chatline-backend \
  --limits=cpu=2,memory=2Gi \
  -n chatline
```

### Slow Queries

```bash
# Enable query logging in PostgreSQL
kubectl exec -it postgres-0 -n chatline -- psql -c "
ALTER DATABASE chatline SET log_min_duration_statement = 1000;
"

# Check slow query log
kubectl logs postgres-0 -n chatline | grep "duration:"
```

### Worker Not Processing Jobs

```bash
# Check queue depth
kubectl exec -it redis-0 -n chatline -- redis-cli LLEN document_ingestion_queue

# Check worker logs
kubectl logs chatline-worker-0 -n chatline

# Manually trigger job processing
kubectl exec -it chatline-worker-0 -n chatline -- python -c "
import asyncio
from app.worker import tasks
asyncio.run(tasks.process_document_ingestion_queue())
"
```

---

## CI/CD

### GitHub Actions Pipeline

Pipeline triggers on push to `main` and pull requests:

1. **Lint** - Backend (flake8, black, isort) and Frontend (ESLint)
2. **Test** - Backend tests against PostgreSQL/Redis
3. **Security** - Trivy vulnerability scanning
4. **Build** - Docker images for backend/frontend/worker
5. **Deploy** - Apply Kubernetes manifests to cluster

### GitHub Secrets Required

```
KUBECONFIG           # Base64-encoded kubeconfig
SLACK_WEBHOOK        # Slack notification webhook
DOCKER_REGISTRY_TOKEN # Container registry credentials
```

---

## Production Checklist

- [ ] Environment variables configured
- [ ] Kubernetes secrets created
- [ ] Database backups configured
- [ ] Monitoring and alerting set up
- [ ] SSL certificates provisioned
- [ ] CDN configured (Cloudflare)
- [ ] Rate limiting configured
- [ ] CORS properly restricted
- [ ] Secrets manager integrated
- [ ] Disaster recovery plan documented
- [ ] Load testing completed
- [ ] Security audit passed

---

## Cost Optimization

### Resource Requests/Limits

Configured for balanced performance:

**Backend**: 250m-1000m CPU, 512Mi-1Gi memory
**Worker**: 500m-2000m CPU, 1Gi-2Gi memory
**Frontend**: 100m-500m CPU, 128Mi-512Mi memory

### Auto-Scaling

- Backend scales 2-10 pods
- Worker scales 1-5 pods
- Frontend scales 2-5 pods

### Storage

- PostgreSQL: Persistent volume (adjust size as needed)
- Redis: In-memory (no persistent volume by default)

---

## Security

### Network Policies

```bash
# Apply network policies
kubectl apply -f deployment/k8s/ingress.yaml  # Includes network policy
```

### RBAC

Service accounts created with minimal permissions:

- `chatline-backend` - database/redis access
- `chatline-worker` - job queue access
- `chatline-frontend` - read-only

### Secrets Management

- Never commit secrets to Git
- Use `.env.example` for template
- Rotate secrets regularly
- Use external secret manager (Vault, AWS Secrets Manager)

---

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Cloudflare Documentation](https://developers.cloudflare.com/)

For questions or issues, check GitHub issues or contact the team.
