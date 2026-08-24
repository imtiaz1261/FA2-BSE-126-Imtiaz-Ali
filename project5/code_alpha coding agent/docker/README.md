# Code Alpha Docker & Deployment Guide

**Status**: ✅ **PRODUCTION READY**

Complete containerization and deployment infrastructure for Code Alpha autonomous agent.

---

## 📋 Overview

This directory contains everything needed to containerize, orchestrate, and deploy Code Alpha:

- **4 Service Dockerfiles**: API Gateway, Orchestrator, Sandbox Worker, Indexing Worker
- **3 Docker Compose configurations**: Development, Production, Testing
- **Database initialization**: PostgreSQL schema with audit tables
- **Build scripts**: Automated Docker image building with tagging
- **Health checks**: Comprehensive service health verification

---

## 🏗️ Architecture

### Service Components

```
┌─────────────────────────────────────────────────────┐
│                  API Gateway                         │
│         (FastAPI REST endpoints, routing)            │
│                 :8000                                │
└────────────┬────────────────────────┬────────────────┘
             │                        │
       ┌─────▼─────┐          ┌───────▼────────┐
       │Orchestrator│          │  Sandbox       │
       │  Master    │          │  Workers(×3)   │
       │  :8001     │          │  :8002         │
       └─────┬─────┘          └────────┬────────┘
             │                         │
       ┌─────┴──────────┬──────────────┴─────┐
       │                │                    │
   ┌───▼───┐        ┌───▼───┐          ┌────▼─────┐
   │Redis  │        │Postgres│         │Indexing  │
   │:6379  │        │:5432   │         │Workers(×2)│
   │       │        │        │         │:8003     │
   └───────┘        └────────┘         └──────────┘
```

### Service Responsibilities

| Service | Port | Purpose | Replicas |
|---------|------|---------|----------|
| API Gateway | 8000 | REST API entry point | Dev:1, Prod:2 |
| Orchestrator | 8001 | Task orchestration & scheduling | Dev:1, Prod:1 |
| Sandbox Worker | 8002 | Isolated tool execution | Dev:1, Prod:3 |
| Indexing Worker | 8003 | Context indexing & embeddings | Dev:1, Prod:2 |
| Redis | 6379 | Caching & job queue | Dev:1, Prod:1 |
| PostgreSQL | 5432 | Persistent storage & audit | Dev:1, Prod:1 |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required
- Docker 20.10+
- Docker Compose 2.0+
- 8GB+ RAM
- 10GB+ disk space

# Optional
- docker-compose completion (bash/zsh)
- Make for script execution
```

### Development Setup (Local)

```bash
# 1. Build images
cd docker
bash build.sh

# 2. Start services
docker-compose -f docker-compose.dev.yml up -d

# 3. Verify services
docker-compose -f docker-compose.dev.yml ps

# 4. Check API
curl http://localhost:8000/health

# 5. View logs
docker-compose -f docker-compose.dev.yml logs -f api
```

### Production Setup

```bash
# 1. Create .env file
cat > .env << EOF
REDIS_PASSWORD=your_secure_password_here
DB_PASSWORD=your_secure_db_password_here
EOF

# 2. Build images
bash build.sh

# 3. Start services
docker-compose -f docker-compose.prod.yml up -d

# 4. Monitor
docker-compose -f docker-compose.prod.yml ps
docker stats

# 5. Access
# API: https://your-domain.com (with reverse proxy)
```

### Testing

```bash
# Run test suite in Docker
docker-compose -f docker-compose.test.yml up

# View results
cat test_results/coverage/index.html
```

---

## 📦 Docker Images

### Dockerfile Locations

```
docker/
├── Dockerfile.api-gateway       # REST API server
├── Dockerfile.orchestrator      # Task orchestrator
├── Dockerfile.sandbox-worker    # Isolated execution
└── Dockerfile.indexing-worker   # Context indexing
```

### Image Details

#### API Gateway (`Dockerfile.api-gateway`)
- **Base**: python:3.10-slim
- **Entrypoint**: FastAPI Uvicorn server
- **Port**: 8000
- **Dependencies**: fastapi, uvicorn, pydantic
- **Health check**: HTTP GET /health
- **Use case**: REST API, request routing, load balancing

#### Orchestrator (`Dockerfile.orchestrator`)
- **Base**: python:3.10-slim
- **Entrypoint**: Custom orchestrator service
- **Port**: 8001
- **Dependencies**: Redis client, database driver
- **Health check**: HTTP GET /health
- **Use case**: Task scheduling, state management, worker coordination

#### Sandbox Worker (`Dockerfile.sandbox-worker`)
- **Base**: python:3.10-slim
- **Special**: Docker-in-Docker capability
- **Port**: 8002
- **Mounts**: `/var/run/docker.sock` for container spawning
- **Health check**: HTTP GET /health
- **Use case**: Isolated tool execution, sandbox enforcement

#### Indexing Worker (`Dockerfile.indexing-worker`)
- **Base**: python:3.10-slim
- **Port**: 8003
- **Extra dependencies**: sentence-transformers, scikit-learn
- **Volume**: `/app/vectors` for embedding storage
- **Health check**: HTTP GET /health
- **Use case**: Parallel context indexing, embedding generation

---

## 🐳 Docker Compose Configurations

### Development (`docker-compose.dev.yml`)

**Purpose**: Local development with full debug logging

**Features**:
- Single instance of each service
- Debug logging (LOG_LEVEL=DEBUG)
- Mounted source code for live reload
- Exposed all ports for direct access
- No resource limits

**Services**: 5 (API, Orchestrator, Sandbox Worker, Indexing Worker, Redis, PostgreSQL)

**Usage**:
```bash
docker-compose -f docker/docker-compose.dev.yml up
docker-compose -f docker/docker-compose.dev.yml logs -f
docker-compose -f docker/docker-compose.dev.yml down
```

**Access**:
- API: http://localhost:8000
- Orchestrator: http://localhost:8001
- Sandbox: http://localhost:8002
- Indexing: http://localhost:8003
- Redis: localhost:6379
- PostgreSQL: localhost:5432

### Production (`docker-compose.prod.yml`)

**Purpose**: High-availability production deployment

**Features**:
- Multiple replicas (API:2, Sandbox:3, Indexing:2)
- Resource limits and reservations
- INFO-level logging
- Read-only source code mount
- Automated restart policies
- Log rotation (json-file driver)
- Production safety mode (STRICT)

**Services**: 6 (same as dev, with replicas)

**Deployment**:
```bash
docker-compose -f docker/docker-compose.prod.yml up -d
docker-compose -f docker/docker-compose.prod.yml ps
```

**Scaling**:
```bash
# Increase sandbox workers
docker-compose -f docker/docker-compose.prod.yml up -d --scale sandbox-worker=5

# Increase API replicas
docker-compose -f docker/docker-compose.prod.yml up -d --scale api=3
```

### Testing (`docker-compose.test.yml`)

**Purpose**: Automated test execution with coverage

**Features**:
- Lightweight Redis (no persistence)
- Separate PostgreSQL instance
- pytest integration
- Coverage report generation
- JUnit XML output

**Services**: 3 (Redis, PostgreSQL, Test Runner)

**Usage**:
```bash
docker-compose -f docker/docker-compose.test.yml up

# View coverage
open test_results/coverage/index.html
```

---

## 🛠️ Building Images

### Build All Images

```bash
cd docker
bash build.sh

# Output:
# Building API Gateway...
# Building Orchestrator...
# Building Sandbox Worker...
# Building Indexing Worker...
# ✓ All images built successfully!
```

### Build Specific Image

```bash
docker build -f docker/Dockerfile.api-gateway -t codealpha/api:latest .
docker build -f docker/Dockerfile.orchestrator -t codealpha/orchestrator:latest .
```

### Custom Registry

```bash
DOCKER_REGISTRY=myregistry.azurecr.io DOCKER_TAG=v1.0.0 bash build.sh

# Tag and push
docker tag codealpha/api:latest myregistry.azurecr.io/codealpha/api:v1.0.0
docker push myregistry.azurecr.io/codealpha/api:v1.0.0
```

---

## 📊 Service Management

### View Logs

```bash
# All services
docker-compose -f docker/docker-compose.dev.yml logs

# Specific service
docker-compose -f docker/docker-compose.dev.yml logs -f api

# Last 100 lines
docker-compose -f docker/docker-compose.dev.yml logs --tail=100 orchestrator

# With timestamps
docker-compose -f docker/docker-compose.dev.yml logs -t api
```

### Monitor Health

```bash
# Check all services
docker-compose -f docker/docker-compose.dev.yml ps

# Get service stats
docker stats --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}"

# Health check specific service
docker inspect codealpha-api-dev | jq '.[] | .State.Health'
```

### Execute Commands

```bash
# Access service shell
docker-compose -f docker/docker-compose.dev.yml exec api bash

# Run command in container
docker-compose -f docker/docker-compose.dev.yml exec api python -m pytest

# Check database
docker-compose -f docker/docker-compose.dev.yml exec postgres psql -U codealpha -d codealpha_dev
```

### Restart Services

```bash
# Restart all
docker-compose -f docker/docker-compose.dev.yml restart

# Restart specific service
docker-compose -f docker/docker-compose.dev.yml restart api

# Stop, remove, restart
docker-compose -f docker/docker-compose.dev.yml down
docker-compose -f docker/docker-compose.dev.yml up -d
```

---

## 💾 Database Management

### Schema Initialization

Database schema is automatically initialized via `init-db.sql`:

```sql
-- Schemas
- code_alpha      (main tables)
- audit           (audit logs)
- metrics         (task metrics)

-- Tables
- audit.audit_log              (append-only audit trail)
- metrics.task_metrics         (task metrics/blast radius)
- code_alpha.tasks             (task records)
- code_alpha.approval_requests (approval workflow)
- code_alpha.safety_events     (safety violations)
- code_alpha.policy_violations (policy violations)
```

### Connect to PostgreSQL

```bash
# From host
psql -h localhost -U codealpha -d codealpha_dev

# From container
docker-compose exec postgres psql -U codealpha -d codealpha_dev

# Common queries
SELECT * FROM code_alpha.tasks;
SELECT * FROM audit.audit_log WHERE task_id = 'task_1';
SELECT * FROM metrics.task_metrics;
SELECT * FROM code_alpha.pending_approvals;
```

### Backup Database

```bash
# Dump schema and data
docker-compose exec postgres pg_dump -U codealpha codealpha_dev > backup.sql

# Restore
docker-compose exec -T postgres psql -U codealpha codealpha_dev < backup.sql
```

---

## 🔐 Security Considerations

### Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| Logging | DEBUG | INFO |
| Safety Mode | standard | strict |
| Resource Limits | None | Yes |
| Restart Policy | unless-stopped | always |
| Secrets | In files | Environment variables |
| Network | Bridge | Custom |

### Secrets Management

```bash
# Create .env file (DO NOT commit)
cat > .env << EOF
REDIS_PASSWORD=secure_password_here
DB_PASSWORD=db_password_here
ORCHESTRATOR_TOKEN=jwt_token_here
EOF

# Use in compose
docker-compose --env-file .env up

# Or set environment variables
export REDIS_PASSWORD=...
docker-compose up
```

### Network Security

```yaml
# Production: Use named network with restrictions
networks:
  codealpha-net-prod:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

# Limit exposure: Use reverse proxy (nginx, traefik)
# Only expose port 443 (HTTPS)
```

---

## 🚨 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs api

# Common issues
# 1. Port already in use
lsof -i :8000

# 2. Out of memory
docker stats

# 3. Permission issues
docker-compose exec -u root api chmod 755 /app
```

### Database Connection Failed

```bash
# Check PostgreSQL
docker-compose exec postgres pg_isready

# Check credentials in .env
docker-compose exec api env | grep DATABASE_URL

# Restart PostgreSQL
docker-compose restart postgres
```

### Health Check Failing

```bash
# Manual health check
curl http://localhost:8000/health -v

# Check service logs
docker-compose logs api

# Increase start_period
# Edit docker-compose.yml: start_period: 60s
```

### Memory Issues

```bash
# Monitor memory
docker stats

# Reduce replicas (production)
docker-compose up -d --scale sandbox-worker=1

# Increase host memory or adjust limits in docker-compose.yml
```

---

## 📈 Monitoring & Observability

### Built-in Health Checks

All services include health checks:

```bash
# View health status
docker inspect <container_id> | jq '.[] | .State.Health'

# Manual test
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Logging Strategy

- **Development**: Console output (DEBUG)
- **Production**: JSON structured logs with rotation

```bash
# View logs with timestamps
docker-compose logs -t --follow api

# Filter by service
docker-compose logs --follow orchestrator sandbox-worker

# Export logs
docker-compose logs > all-logs.txt
```

### Metrics Collection

PostgreSQL tables for metrics:

```sql
-- Query task metrics
SELECT * FROM metrics.task_summary WHERE task_id = 'task_1';

-- Audit trail
SELECT * FROM audit.audit_log WHERE task_id = 'task_1' ORDER BY timestamp DESC;

-- Safety events
SELECT * FROM code_alpha.safety_events WHERE severity = 'critical';
```

---

## 📚 Docker Best Practices Used

✅ **Multi-stage builds** (implicit via shared base)
✅ **Non-root user** (codealpha:1000)
✅ **Health checks** (all services)
✅ **Resource limits** (production)
✅ **Log rotation** (json-file driver)
✅ **Named volumes** (data persistence)
✅ **Network isolation** (named networks)
✅ **Environment variables** (configuration)
✅ **Health dependencies** (service ordering)
✅ **.dockerignore** (optimized build context)

---

## 🔗 Integration

### With Kubernetes (Module 15b)

Images built here deploy to Kubernetes:

```bash
# Push to registry
docker push myregistry.azurecr.io/codealpha/api:latest

# Reference in k8s manifests
image: myregistry.azurecr.io/codealpha/api:latest
imagePullPolicy: IfNotPresent
```

### With CI/CD (Module 15c)

GitHub Actions can use these Dockerfiles:

```yaml
- name: Build Docker images
  run: |
    cd docker
    bash build.sh

- name: Push to registry
  run: |
    docker push ${{ env.REGISTRY }}/api:${{ env.TAG }}
```

---

## 📦 Deliverables (Module 15a)

### Docker Files (4)
- ✅ `Dockerfile.api-gateway` (100+ LOC)
- ✅ `Dockerfile.orchestrator` (100+ LOC)
- ✅ `Dockerfile.sandbox-worker` (100+ LOC)
- ✅ `Dockerfile.indexing-worker` (100+ LOC)

### Docker Compose (3)
- ✅ `docker-compose.dev.yml` (150+ LOC, local development)
- ✅ `docker-compose.prod.yml` (200+ LOC, HA production)
- ✅ `docker-compose.test.yml` (80+ LOC, automated testing)

### Supporting Files
- ✅ `.dockerignore` (optimized build context)
- ✅ `init-db.sql` (PostgreSQL schema, 250+ LOC)
- ✅ `build.sh` (automated image building)
- ✅ `README.md` (this file, comprehensive guide)

### Features Implemented
- ✅ 4 specialized service images
- ✅ Development, production, testing stacks
- ✅ Database initialization and migrations
- ✅ Health checks (all services)
- ✅ Resource limits and reservations (production)
- ✅ Log rotation and structured logging
- ✅ Network isolation
- ✅ Secrets management (environment variables)
- ✅ Volume management (persistence, ephemeral)
- ✅ Service dependencies (startup ordering)

---

## ✅ Status

**Module 15a Status**: ✅ **PRODUCTION READY**

- 4 Dockerfiles created and tested
- 3 Docker Compose configurations (dev/prod/test)
- Complete database schema
- Build automation
- Comprehensive documentation

Ready for **Module 15b: Kubernetes Manifests & Scaling**

---

## 📞 Support

For deployment issues:

1. **Check logs**: `docker-compose logs <service>`
2. **Verify configuration**: `.env`, `docker-compose.yml`
3. **Test connectivity**: `docker-compose exec <service> curl <endpoint>`
4. **Monitor resources**: `docker stats`
5. **Review documentation**: This README and service Dockerfiles

---

**Next**: Module 15b - Kubernetes Manifests for orchestration and scaling
