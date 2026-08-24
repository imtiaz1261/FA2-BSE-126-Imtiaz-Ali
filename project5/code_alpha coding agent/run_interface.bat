@echo off
REM Code Alpha - Quick Start Script for Kiro Interface
REM This script starts everything you need

echo ==========================================
echo Code Alpha - Kiro Interface Launcher
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed. Please install Node.js 18+
    pause
    exit /b 1
)

echo [1/5] Checking dependencies...
echo.

REM Install Python dependencies
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate
echo Installing Python dependencies...
pip install -r requirements_cli_api.txt

REM Install Node.js dependencies for extension
cd kiro_interface
if not exist "node_modules" (
    echo Installing Node.js dependencies...
    npm install
)
cd ..

echo.
echo [2/5] Building VS Code Extension...
cd kiro_interface
call npm run build
cd ..

echo.
echo [3/5] Starting Code Alpha API Server...
start "Code Alpha API" cmd /k "venv\Scripts\activate && codealpha api --start"

REM Wait for server to start
timeout /t 5 /nobreak >nul

echo.
echo [4/5] Server started on http://localhost:8000
echo API Documentation: http://localhost:8000/api/docs
echo.

echo [5/5] Opening VS Code with Code Alpha...
echo.
echo ==========================================
echo INSTRUCTIONS:
echo ==========================================
echo.
echo 1. VS Code will open shortly
echo 2. Press Ctrl+Shift+K to start a new task
echo 3. Type your coding task
echo 4. Click "Run Task" to execute
echo 5. Review changes in the diff view
echo 6. Approve or reject changes
echo.
echo Keyboard Shortcuts:
echo   Ctrl+Shift+K      - New Task
echo   Ctrl+Shift+Enter  - Run Task
echo   Ctrl+Shift+R      - Review Changes
echo.
echo API Server: http://localhost:8000
echo API Docs:   http://localhost:8000/api/docs
echo.
pause

REM Open VS Code with the extension
code --extensionDevelopmentPath="%cd%\kiro_interface" .
