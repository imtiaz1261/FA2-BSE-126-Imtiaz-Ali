# Chatline Development Environment Startup Script (Windows PowerShell)
# This script starts the complete local development stack with Docker Compose

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Chatline Development Environment" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
Write-Host "1. Checking Docker installation..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    Write-Host "  Download: https://www.docker.com/products/docker-desktop" -ForegroundColor Gray
    exit 1
}

# Check if Docker daemon is running
Write-Host ""
Write-Host "2. Checking Docker daemon..." -ForegroundColor Yellow
try {
    $dockerPs = docker ps 2>$null
    Write-Host "✓ Docker daemon is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker daemon is not running" -ForegroundColor Red
    Write-Host "  Action: Open Docker Desktop and wait for it to start (takes 30-60 seconds)" -ForegroundColor Yellow
    exit 1
}

# Check if Docker Compose is installed
Write-Host ""
Write-Host "3. Checking Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker compose version 2>$null
    Write-Host "✓ Docker Compose found: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Compose not found" -ForegroundColor Red
    exit 1
}

# Get current directory
$projectDir = Get-Location
Write-Host ""
Write-Host "4. Project Directory" -ForegroundColor Yellow
Write-Host "   Location: $projectDir" -ForegroundColor Gray

# Check if docker-compose.yml exists
if (!(Test-Path "docker-compose.yml")) {
    Write-Host "✗ docker-compose.yml not found in current directory" -ForegroundColor Red
    exit 1
}
Write-Host "✓ docker-compose.yml found" -ForegroundColor Green

# Check if Dockerfile exists
if (!(Test-Path "deployment/docker/backend.Dockerfile")) {
    Write-Host "✗ Dockerfiles not found" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Dockerfiles found" -ForegroundColor Green

# Validate docker-compose configuration
Write-Host ""
Write-Host "5. Validating docker-compose configuration..." -ForegroundColor Yellow
try {
    docker compose config > $null 2>&1
    Write-Host "✓ Configuration is valid" -ForegroundColor Green
} catch {
    Write-Host "✗ Configuration validation failed" -ForegroundColor Red
    exit 1
}

# Confirm startup
Write-Host ""
Write-Host "6. Ready to start development environment" -ForegroundColor Yellow
Write-Host ""
Write-Host "Services that will start:" -ForegroundColor Cyan
Write-Host "  • PostgreSQL + pgvector (port 5432)" -ForegroundColor Gray
Write-Host "  • Redis (port 6379)" -ForegroundColor Gray
Write-Host "  • MinIO S3 (port 9000, console 9001)" -ForegroundColor Gray
Write-Host "  • Backend API (port 8000)" -ForegroundColor Gray
Write-Host "  • Frontend React (port 5173)" -ForegroundColor Gray
Write-Host "  • Worker (background processor)" -ForegroundColor Gray
Write-Host ""
Write-Host "Estimated startup time: 3-5 minutes" -ForegroundColor Gray
Write-Host ""

# Ask for confirmation
$response = Read-Host "Start development environment? (yes/no)"

if ($response -ne "yes") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Starting services..." -ForegroundColor Cyan
Write-Host ""

# Start services
docker compose up --build

# Startup complete
Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "Services Started Successfully!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access the services:" -ForegroundColor Cyan
Write-Host "  Frontend:      http://localhost:5173" -ForegroundColor Green
Write-Host "  API Docs:      http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  MinIO Console: http://localhost:9001" -ForegroundColor Green
Write-Host ""
Write-Host "Credentials:" -ForegroundColor Cyan
Write-Host "  MinIO: minioadmin / minioadmin" -ForegroundColor Gray
Write-Host "  DB:    postgres / postgres" -ForegroundColor Gray
Write-Host ""
Write-Host "View logs in another terminal:" -ForegroundColor Cyan
Write-Host "  docker compose logs -f backend" -ForegroundColor Gray
Write-Host "  docker compose logs -f frontend" -ForegroundColor Gray
Write-Host ""
Write-Host "Stop services:" -ForegroundColor Cyan
Write-Host "  docker compose down" -ForegroundColor Gray
Write-Host ""
