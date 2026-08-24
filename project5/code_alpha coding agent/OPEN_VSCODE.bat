@echo off
REM ============================================
REM Code Alpha - Open VS Code with Kiro Interface
REM ============================================

setlocal

set "PROJECT_DIR=c:\Users\IJAZ AHMAD\Desktop\Internship Work\week5\task56"

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║         Opening VS Code with Kiro Interface...            ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Open VS Code with project folder
echo Opening VS Code...
start "" code "%PROJECT_DIR%"

echo.
echo ✅ VS Code is starting!
echo.
echo ════════════════════════════════════════════════════════════
echo NEXT STEPS:
echo ════════════════════════════════════════════════════════════
echo.
echo 1️⃣  Wait for VS Code to fully load (10-15 seconds)
echo.
echo 2️⃣  Press: Ctrl + Shift + K
echo    (This opens the Code Alpha Kiro interface)
echo.
echo 3️⃣  You will see the 3D interface:
echo    • Left:  3D animated canvas with particles
echo    • Right: Task input and output panels
echo.
echo 4️⃣  Enter a task in the textarea:
echo    Example: "Create a fibonacci function"
echo.
echo 5️⃣  Click: ▶ EXECUTE button
echo.
echo 6️⃣  Watch real-time code generation! ✨
echo    • Logs show execution progress
echo    • Code tab displays generated Python
echo    • Progress bar fills 0→100%
echo    • 3D animation runs in background
echo.
echo ════════════════════════════════════════════════════════════
echo AVAILABLE TASKS:
echo ════════════════════════════════════════════════════════════
echo.
echo • "Create a fibonacci function"
echo • "Build a REST API with user endpoints"
echo • "Write unit tests for calculator"
echo • "Create a data model for users"
echo • "Generate hello world program"
echo.
echo ════════════════════════════════════════════════════════════
echo BACKEND:
echo ════════════════════════════════════════════════════════════
echo.
echo Backend is running on: http://localhost:8000
echo API Documentation:    http://localhost:8000/docs
echo.
echo ════════════════════════════════════════════════════════════
echo.

endlocal
