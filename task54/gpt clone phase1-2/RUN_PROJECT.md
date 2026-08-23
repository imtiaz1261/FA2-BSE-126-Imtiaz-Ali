# How to Run the Chatline Project

Complete guide to run the production-ready infrastructure locally.

---

## 📋 Prerequisites

Before starting, ensure you have:

1. **Docker Desktop installed** (version 29.6+)
   - [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
   - Windows 10/11 with WSL 2 enabled

2. **Git** (optional, for version control)
   - [Download Git](https://git-scm.com/)

3. **Minimum System Requirements:**
   - CPU: 4+ cores
   - RAM: 8GB+ (Docker needs ~4GB)
   - Disk: 10GB+ free space

---

## ⚙️ Setup

### Step 1: Verify Docker Installation

**On Windows Command Prompt:**
```cmd
docker --version
docker ps
```

**Expected Output:**
```
Docker version 29.6.2, build dfc4efb
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
(empty list - this is fine for fresh install)
```

If you get an error saying Docker daemon is not running:
- Open **Docker Desktop** application (search in Windows Start menu)
- Wait 30-60 seconds for it to fully start
- Try the commands again

### Step 2: Navigate to Project Directory

```cmd
cd "c:\Users\IJAZ AHMAD\Desktop\Internship Work\week5\task54\gpt clone phase1-2"
```

### Step 3: Verify Project Files

```cmd
# Check docker-compose.yml exists
dir docker-compose.yml

# Check Dockerfiles exist
dir deployment\docker\*.Dockerfile
```

---

## 🚀 Quick Start (Recommended)

### Option 1: PowerShell Script (Easiest)

```powershell
# Run the startup script
.\START_LOCAL_DEV.ps1
```

This script will:
- ✓ Check Docker installation
- ✓ Verify Docker daemon is running
- ✓ Validate docker-compose.yml
- ✓ Start all services
- ✓ Show you the access URLs

### Option 2: Command Prompt Batch Script

```cmd
# Run the startup script
START_LOCAL_DEV.bat
```

### Option 3: Manual Command

```powershell
# Navigate to project directory
cd "c:\Users\IJAZ AHMAD\Desktop\Internship Work\week5\task54\gpt clone phase1-2"

# Build and start all services
docker compose up --build

# Or run in background
docker compose up -d --build
```

---

## 📝 Manual Steps Explained

If you prefer to run commands manually:

### 1. Build Docker Images (takes 5-10 minutes)

```powershell
# Build all images
docker compose build

# Or with no cache
docker compose build --no-cache
```

### 2. Start All Services

```powershell
# Start services (foreground - you see logs)
docker compose up

# Or start in background
docker compose up -d

# Start and rebuild
docker compose up --build
```

### 3. Wait for Services to Be Ready

The services will start in this order:
1. PostgreSQL (database) - ~30 seconds
2. Redis (cache) - ~10 seconds
3. MinIO (object storage) - ~10 seconds
4. Backend API - ~30 seconds (runs migrations)
5. Worker - ~10 seconds
6. Frontend - ~30 seconds (npm install + dev server)

**Total startup time: 3-5 minutes**

### 4. Verify Services Are Running

```powershell
# Check all containers
docker compose ps

# Should show 6 containers all with "Up" status
```

---

## 🌐 Access the Application

Once all services are running:

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:5173 | React UI |
| **API Docs** | http://localhost:8000/docs | Swagger documentation |
| **API Health** | http://localhost:8000/health | Health check |
| **Metrics** | http://localhost:8000/metrics | Prometheus metrics |
| **MinIO Console** | http://localhost:9001 | S3 file browser |

### Credentials

| Service | Username | Password |
|---------|----------|----------|
| MinIO Console | minioadmin | minioadmin |
| PostgreSQL | postgres | postgres |
| Redis | (password) | redis |

---

## 🔍 Verify Everything Works

### Test Backend Health

```powershell
# Backend is healthy
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","service":"backend"}
```

### Test Readiness

```powershell
curl http://localhost:8000/ready

# Should return:
# {"status":"ready","service":"backend","database":"connected","timestamp":"..."}
```

### Test Frontend

Open browser and navigate to:
```
http://localhost:5173
```

You should see the React application loading.

### Test Database Connection

```powershell
# Access PostgreSQL shell
docker compose exec postgres psql -U postgres -d chatline -c "SELECT version();"

# Should return PostgreSQL version info
```

### Test Redis Connection

```powershell
# Access Redis CLI
docker compose exec redis redis-cli

# Type: ping
# Should return: PONG
# Type: exit
```

### Test MinIO

Open browser:
```
http://localhost:9001
```

Login with: `minioadmin` / `minioadmin`

You should see the MinIO console with an empty `chatline` bucket.

---

## 📊 View Logs

### View All Logs

```powershell
# Follow all service logs
docker compose logs -f

# Ctrl+C to stop following
```

### View Specific Service Logs

```powershell
# Backend logs
docker compose logs -f backend

# Frontend logs
docker compose logs -f frontend

# Database logs
docker compose logs -f postgres

# Worker logs
docker compose logs -f worker

# Redis logs
docker compose logs -f redis

# MinIO logs
docker compose logs -f minio
```

### View Last N Lines

```powershell
# Last 100 lines of backend logs
docker compose logs --tail=100 backend

# Last 50 lines of all services
docker compose logs --tail=50
```

---

## 🛠️ Common Tasks

### Restart a Service

```powershell
# Restart backend
docker compose restart backend

# Restart all services
docker compose restart
```

### Stop Services (Keep Data)

```powershell
# Stop all services
docker compose stop

# Start them again
docker compose start
```

### Stop and Remove Everything (Delete Data)

```powershell
# Stop and remove containers
docker compose down

# Remove containers AND volumes (deletes all data!)
docker compose down -v
```

### Rebuild Specific Image

```powershell
# Rebuild backend without cache
docker compose build --no-cache backend

# Rebuild and restart
docker compose up -d --build backend
```

### Access Container Shell

```powershell
# Access backend shell
docker compose exec backend bash

# Access PostgreSQL shell
docker compose exec postgres psql -U postgres

# Access Redis shell
docker compose exec redis redis-cli
```

### Run Database Migrations

```powershell
# Apply migrations
docker compose exec backend alembic upgrade head

# Rollback one migration
docker compose exec backend alembic downgrade -1
```

### Run Tests

```powershell
# Run backend tests
docker compose exec backend pytest tests/

# With coverage
docker compose exec backend pytest tests/ --cov=app
```

---

## 🐛 Troubleshooting

### Docker Daemon Not Running

**Error:** `ERROR: failed to connect to the docker API`

**Solution:**
1. Open Docker Desktop application (search in Start menu)
2. Wait 30-60 seconds for daemon to start
3. Try command again

### Port Already in Use

**Error:** `Error response from daemon: Ports are not available`

**Solution:**
```powershell
# Find what's using port 8000
netstat -ano | findstr :8000

# Or kill the container
docker compose down

# Then try again
docker compose up --build
```

### Out of Memory

**Error:** `Cannot connect to Docker daemon`

**Solution:**
- Increase Docker Desktop memory: Docker Desktop > Settings > Resources > Memory
- Recommended: 6-8GB
- Restart Docker Desktop after changing

### Disk Space Full

**Error:** `no space left on device`

**Solution:**
```powershell
# Clean up Docker (removes unused images/containers)
docker system prune -a

# Or rebuild
docker compose down -v
docker compose up --build
```

### Backend Won't Start (Import Errors)

**Error:** `ModuleNotFoundError: No module named 'app.worker'`

**Solution:**
```powershell
# Rebuild backend without cache
docker compose build --no-cache backend

# Restart
docker compose up -d backend

# Check logs
docker compose logs backend
```

### Database Won't Initialize

**Error:** `PostgreSQL failed to start`

**Solution:**
```powershell
# Check postgres logs
docker compose logs postgres

# Reset database completely
docker compose down -v

# Start fresh
docker compose up --build postgres
```

### Frontend Not Loading

**Error:** `Cannot connect to http://localhost:5173`

**Solution:**
```powershell
# Check frontend status
docker compose ps frontend

# Check frontend logs
docker compose logs frontend

# Rebuild frontend
docker compose build --no-cache frontend

# Restart
docker compose up -d frontend
```

---

## 📈 Performance Tips

### Speed Up Initial Build

```powershell
# Build without pulling latest base images
docker compose build

# (vs. docker compose up --build which pulls latest)
```

### Reduce Memory Usage

```powershell
# Stop services you're not using
docker compose stop worker  # Stop worker if you don't need it

# Or configure less RAM in Docker Desktop settings
```

### Speed Up Development

```powershell
# For backend changes, just restart (code reloads automatically)
docker compose restart backend

# For frontend changes, they reload automatically via Vite

# Rebuild only when dependencies change
docker compose build backend
docker compose up -d backend
```

---

## 📖 Next Steps

1. **Explore the API:**
   - Go to http://localhost:8000/docs
   - You'll see Swagger/OpenAPI documentation
   - Try API endpoints interactively

2. **Test Frontend:**
   - Go to http://localhost:5173
   - Explore the React application
   - Test authentication and chat features

3. **Monitor Services:**
   - View metrics at http://localhost:8000/metrics
   - Check Prometheus format output
   - Use for monitoring dashboards

4. **View Code:**
   - Backend: `backend/app/`
   - Frontend: `frontend/src/`
   - Infrastructure: `deployment/`

5. **Read Documentation:**
   - [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment
   - [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Command reference
   - [INFRASTRUCTURE_SUMMARY.md](INFRASTRUCTURE_SUMMARY.md) - Architecture

---

## 🎯 You're All Set!

The application is now running locally with:

✅ Full-stack setup (frontend, backend, workers)  
✅ PostgreSQL with pgvector  
✅ Redis caching  
✅ MinIO object storage  
✅ Health checks  
✅ Structured logging  
✅ Prometheus metrics  
✅ Sentry error tracking  

**Start developing! 🚀**

---

## 📞 Need Help?

Check these resources:

1. **Issues with setup:**
   - See "Troubleshooting" section above
   - Check [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

2. **Understanding the architecture:**
   - Read [INFRASTRUCTURE_SUMMARY.md](INFRASTRUCTURE_SUMMARY.md)
   - See `docker-compose.yml` for service definitions

3. **Common commands:**
   - See [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

4. **Production deployment:**
   - See [DEPLOYMENT.md](DEPLOYMENT.md)
   - See [CLOUDFLARE.md](CLOUDFLARE.md)

---

**Happy coding! 💻**
