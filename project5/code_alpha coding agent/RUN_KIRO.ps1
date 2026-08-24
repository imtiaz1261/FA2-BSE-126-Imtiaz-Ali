Write-Host ""
Write-Host "Starting Code Alpha Kiro System..."
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Step 1: Checking if backend is running..."

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "Backend is already running!"
} catch {
    Write-Host "Starting backend..."
    $backendDir = Join-Path $scriptDir "kiro_backend"
    Start-Process -FilePath "python" -ArgumentList "app.py" -WorkingDirectory $backendDir -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "Backend started!"
}

Write-Host ""
Write-Host "Step 2: Building extension..."

$extDir = Join-Path $scriptDir "kiro_interface"
Push-Location $extDir
npm run build 2>&1 | Out-Null
Pop-Location

Write-Host "Extension built!"

Write-Host ""
Write-Host "Step 3: Opening VS Code..."

& code "$scriptDir"

Write-Host ""
Write-Host "VS Code is opening..."
Write-Host ""
Write-Host "Next: Press Ctrl+Shift+K to open Kiro interface"
Write-Host ""
