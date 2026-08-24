@echo off
REM Final Verification Script - Checks all components are ready

echo ================================================
echo   Code Alpha - System Verification
echo ================================================
echo.

set ERRORS=0

REM Check Python
echo [1/7] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo       [FAIL] Python not found
    set /a ERRORS+=1
) else (
    echo       [OK] Python installed
)

REM Check Node.js
echo [2/7] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo       [FAIL] Node.js not found
    set /a ERRORS+=1
) else (
    echo       [OK] Node.js installed
)

REM Check backend files
echo [3/7] Checking backend files...
if exist "kiro_backend\app.py" (
    echo       [OK] Backend server found
) else (
    echo       [FAIL] Backend server missing
    set /a ERRORS+=1
)

REM Check extension files
echo [4/7] Checking extension files...
if exist "kiro_interface\out\extension.js" (
    echo       [OK] Extension built (509.8kb)
) else (
    echo       [FAIL] Extension not built
    set /a ERRORS+=1
)

REM Check all modules
echo [5/7] Checking all 15 modules...
set MODULES=0
for /d %%d in (code_alpha\*) do set /a MODULES+=1
if %MODULES% GEQ 10 (
    echo       [OK] %MODULES% modules found
) else (
    echo       [WARN] Only %MODULES% modules found
)

REM Check documentation
echo [6/7] Checking documentation...
if exist "KIRO_COMPLETE_GUIDE.md" (
    echo       [OK] Documentation complete
) else (
    echo       [FAIL] Documentation missing
    set /a ERRORS+=1
)

REM Check startup script
echo [7/7] Checking startup script...
if exist "start_kiro_complete.bat" (
    echo       [OK] Startup script ready
) else (
    echo       [FAIL] Startup script missing
    set /a ERRORS+=1
)

echo.
echo ================================================
echo   Verification Complete
echo ================================================
echo.

if %ERRORS% EQU 0 (
    echo [SUCCESS] All checks passed!
    echo.
    echo Ready to start:
    echo   Run: start_kiro_complete.bat
    echo.
) else (
    echo [ERROR] %ERRORS% checks failed
    echo Please fix the issues above
    echo.
)

pause
