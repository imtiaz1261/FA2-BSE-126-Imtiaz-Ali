@echo off
REM ============================================
REM Code Alpha Kiro - Complete Startup Script
REM ============================================

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║          CODE ALPHA - KIRO INTERFACE                   ║
echo ║     Autonomous Code Generation AI System               ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo [INFO] Starting Code Alpha Kiro System...
echo [INFO] Working directory: %cd%
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo [ERROR] Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

echo [OK] Python detected
python --version

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH!
    echo [ERROR] Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)

echo [OK] Node.js detected
node --version

echo.
echo ════════════════════════════════════════════════════════
echo [PHASE 1] Starting Backend Server...
echo ════════════════════════════════════════════════════════
echo.

REM Start backend in new window
if exist "kiro_backend\app.py" (
    echo [INFO] Launching backend on http://localhost:8000
    start "Code Alpha Backend" cmd /k "cd kiro_backend && python app.py"
    echo [OK] Backend starting in new window...
) else (
    echo [ERROR] Backend file not found: kiro_backend\app.py
    pause
    exit /b 1
)

REM Wait for backend to start
echo [INFO] Waiting for backend to initialize...
timeout /t 3 /nobreak

REM Test backend health
echo [INFO] Testing backend connectivity...
for /L %%i in (1,1,10) do (
    powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch { exit 1 }"
    if errorlevel 0 (
        echo [OK] Backend is responsive!
        goto backend_ready
    )
    timeout /t 1 /nobreak
)

echo [WARNING] Backend may not be ready, continuing anyway...

:backend_ready

echo.
echo ════════════════════════════════════════════════════════
echo [PHASE 2] Starting VS Code with Extension...
echo ════════════════════════════════════════════════════════
echo.

REM Check if VS Code is installed
where code >nul 2>&1
if errorlevel 1 (
    echo [WARNING] VS Code not found in PATH
    echo [INFO] Please install VS Code or add it to PATH
    echo [INFO] If VS Code is installed, you can manually open it and install the extension
    echo.
    echo [INFO] Extension location: %SCRIPT_DIR%kiro_interface
    echo.
    pause
    exit /b 0
)

echo [OK] VS Code detected
code --version | findstr /R "^[0-9]"

REM Install extension dependencies
if exist "kiro_interface\package.json" (
    echo [INFO] Installing extension dependencies...
    cd "kiro_interface"
    call npm install --quiet 2>nul
    if errorlevel 0 (
        echo [OK] Dependencies installed
    ) else (
        echo [WARNING] Some dependencies may not have installed properly
    )
    cd ..
) else (
    echo [ERROR] Extension package.json not found
)

echo.
echo [INFO] Opening VS Code with Kiro Interface...
echo [IMPORTANT] To open the Kiro interface:
echo   1. VS Code will open in a few seconds
echo   2. Press Ctrl+Shift+K to open the Kiro interface
echo   3. Or run command: "Code Alpha: Open Interface"
echo.

REM Open VS Code with project folder
REM Note: We open the project folder, not the extension folder
REM The extension will be loaded automatically by VS Code
echo [INFO] Launching VS Code...
code "%SCRIPT_DIR%"

echo.
echo ════════════════════════════════════════════════════════
echo [SUCCESS] System Startup Complete!
echo ════════════════════════════════════════════════════════
echo.
echo [BACKEND]   Running on http://localhost:8000
echo [API DOCS]  http://localhost:8000/docs (interactive docs)
echo [EXTENSION] Press Ctrl+Shift+K in VS Code
echo.
echo ════════════════════════════════════════════════════════
echo QUICK START GUIDE:
echo ════════════════════════════════════════════════════════
echo.
echo 1. VS Code will open shortly
echo 2. Press Ctrl+Shift+K to open Code Alpha Kiro interface
echo 3. Enter a task (e.g., "Create fibonacci function")
echo 4. Click EXECUTE and watch real-time code generation
echo 5. View generated code in the Code tab
echo.
echo EXAMPLE TASKS:
echo   - Create a fibonacci function
echo   - Build a REST API with user endpoints
echo   - Write unit tests for calculator
echo   - Create a data model with database operations
echo   - Generate hello world program
echo.
echo Backend Output:
echo   - Check backend terminal for execution logs
echo   - Generated files saved to: %TEMP%\code_alpha_tasks
echo.
echo KEYBOARD SHORTCUTS:
echo   - Ctrl+Shift+K       Open/Focus Kiro Interface
echo   - Tab                Switch between Logs/Code views
echo.
echo ════════════════════════════════════════════════════════
echo.

endlocal
