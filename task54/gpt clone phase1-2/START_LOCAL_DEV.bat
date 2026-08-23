@echo off
REM Chatline Development Environment Startup Script (Windows Command Prompt)
REM This script starts the complete local development stack with Docker Compose

cls
echo.
echo ================================
echo Chatline Development Environment
echo ================================
echo.

REM Check if Docker is installed
echo 1. Checking Docker installation...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo X Docker not found. Please install Docker Desktop.
    echo   Download: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo [OK] Docker found

REM Check if Docker daemon is running
echo.
echo 2. Checking Docker daemon...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo X Docker daemon is not running
    echo   Action: Open Docker Desktop and wait for it to start (takes 30-60 seconds^)
    pause
    exit /b 1
)
echo [OK] Docker daemon is running

REM Check if Docker Compose is installed
echo.
echo 3. Checking Docker Compose...
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    echo X Docker Compose not found
    pause
    exit /b 1
)
echo [OK] Docker Compose found

REM Check if docker-compose.yml exists
echo.
echo 4. Project Directory: %cd%
if not exist docker-compose.yml (
    echo X docker-compose.yml not found
    pause
    exit /b 1
)
echo [OK] docker-compose.yml found

if not exist "deployment\docker\backend.Dockerfile" (
    echo X Dockerfiles not found
    pause
    exit /b 1
)
echo [OK] Dockerfiles found

REM Validate configuration
echo.
echo 5. Validating docker-compose configuration...
docker compose config >nul 2>&1
if %errorlevel% neq 0 (
    echo X Configuration validation failed
    pause
    exit /b 1
)
echo [OK] Configuration is valid

REM Display startup information
echo.
echo 6. Ready to start development environment
echo.
echo Services that will start:
echo   - PostgreSQL + pgvector (port 5432^)
echo   - Redis (port 6379^)
echo   - MinIO S3 (port 9000, console 9001^)
echo   - Backend API (port 8000^)
echo   - Frontend React (port 5173^)
echo   - Worker (background processor^)
echo.
echo Estimated startup time: 3-5 minutes
echo.
set /p response="Start development environment? (yes/no): "

if /i not "%response%"=="yes" (
    echo Cancelled.
    exit /b 0
)

echo.
echo Starting services...
echo.

REM Start services
docker compose up --build

REM Display completion message
echo.
echo ================================
echo Services Started Successfully!
echo ================================
echo.
echo Access the services:
echo   Frontend:      http://localhost:5173
echo   API Docs:      http://localhost:8000/docs
echo   MinIO Console: http://localhost:9001
echo.
echo Credentials:
echo   MinIO: minioadmin / minioadmin
echo   DB:    postgres / postgres
echo.
echo View logs in another terminal:
echo   docker compose logs -f backend
echo   docker compose logs -f frontend
echo.
echo Stop services:
echo   docker compose down
echo.
pause
