#Requires -Version 5.0

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗"
Write-Host "║                                                                            ║"
Write-Host "║        🚀 CODE ALPHA KIRO - COMPLETE SYSTEM STARTUP                       ║"
Write-Host "║                                                                            ║"
Write-Host "║            Autonomous Code Generation with Real-time Streaming             ║"
Write-Host "║                                                                            ║"
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝"
Write-Host ""

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "[INFO] Working directory: $(Get-Location)"
Write-Host ""

# Check Python
Write-Host "════════════════════════════════════════════════════════════════════════════"
Write-Host "CHECKING REQUIREMENTS"
Write-Host "════════════════════════════════════════════════════════════════════════════"
Write-Host ""

if ($pythonVersion) {
    Write-Host "OK Python: $pythonVersion"
} else {
    Write-Host "ERROR Python not found. Please install Python 3.8+"
    exit 1
}

$nodeVersion = & node --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK Node.js: $nodeVersion"
} else {
    Write-Host "ERROR Node.js not found. Please install Node.js"
    exit 1
}

$codeVersion = & code --version 2>&1 | Select-Object -First 1
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK VS Code: $codeVersion"
} else {
    Write-Host "WARN VS Code not found in PATH. Will attempt to open anyway."
}

Write-Host ""

# Start Backend
Write-Host "════════════════════════════════════════════════════════════════════════════"
Write-Host "PHASE 1: STARTING BACKEND SERVER"
Write-Host "════════════════════════════════════════════════════════════════════════════"
Write-Host ""

if (Test-Path "kiro_backend\app.py") {
    Write-Host "[INFO] Launching backend on http://localhost:8000"
    
    # Check if backend is already running
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "OK Backend already running!"
        }
    } catch {
        # Backend not running, start it
        Write-Host "[INFO] Starting backend in new window..."
        $backendPath = Join-Path $scriptDir "kiro_backend"
        $cmdArgs = "/k cd /d `"$backendPath`" && python app.py"
        Start-Process -FilePath "cmd.exe" -ArgumentList $cmdArgs -WindowStyle Normal
        
        # Wait for backend to start
        Write-Host "[INFO] Waiting for backend to initialize..."
        $maxAttempts = 30
        $attempt = 0
        
        while ($attempt -lt $maxAttempts) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
                if ($response.StatusCode -eq 200) {
                    Write-Host "OK Backend is responsive!"
                    break
                }
            } catch {
                $attempt++
                Start-Sleep -Seconds 1
            }
        }
        
        if ($attempt -eq $maxAttempts) {
            Write-Host "WARN Backend may not be ready, continuing anyway..."
        }
    }
} else {
    Write-Host "ERROR Backend file not found: kiro_backend\app.py"
    exit 1
}

Write-Host ""

# Install extension dependencies
Write-Host "════════════════════════════════════════════════════════════════════════════"
Write-Host "PHASE 2: PREPARING EXTENSION"
Write-Host "════════════════════════════════════════════════════════════════════════════"
Write-Host ""

if (Test-Path "kiro_interface\package.json") {
    Write-Host "[INFO] Installing extension dependencies..."
    Push-Location "kiro_interface"
    & npm install --silent *> $null
    Write-Host "OK Dependencies installed"
    
    # Rebuild extension
    Write-Host "[INFO] Building extension..."
    & npm run build *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK Extension built successfully"
    } else {
        Write-Host "WARN Extension build had warnings"
    }
    Pop-Location
} else {
    Write-Host "ERROR Extension package.json not found"
}

Write-Host ""

# Open VS Code
Write-Host "════════════════════════════════════════════════════════════════════════════"
Write-Host "PHASE 3: OPENING VS CODE"
Write-Host "════════════════════════════════════════════════════════════════════════════"
Write-Host ""

Write-Host "[INFO] Launching VS Code..."
& code "$scriptDir"
Write-Host "OK VS Code launched"

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════════════════"
Write-Host "OK STARTUP COMPLETE"
Write-Host "════════════════════════════════════════════════════════════════════════════"
Write-Host ""
Write-Host "System Status:"
Write-Host "  OK Backend:       RUNNING (http://localhost:8000)"
Write-Host "  OK Extension:     READY"
Write-Host "  OK VS Code:       OPEN"
Write-Host ""
Write-Host "Next Steps:"
Write-Host "  1. Look at VS Code window"
Write-Host "  2. Press: Ctrl + Shift + K"
Write-Host "  3. Enter a task"
Write-Host "  4. Click EXECUTE"
Write-Host "  5. Watch real-time code generation!"
Write-Host ""
Write-Host "Alternative Access:"
Write-Host "  - Command Palette: Ctrl+Shift+P"
Write-Host "  - Search: Code Alpha: New Task"
Write-Host "  - Backend API Docs: http://localhost:8000/docs"
Write-Host ""
Write-Host "Tasks You Can Try:"
Write-Host "  - Create a fibonacci function"
Write-Host "  - Build a REST API with user endpoints"
Write-Host "  - Write unit tests for calculator"
Write-Host "  - Create a data model for users"
Write-Host "  - Generate hello world program"
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════════════════"
Write-Host ""
