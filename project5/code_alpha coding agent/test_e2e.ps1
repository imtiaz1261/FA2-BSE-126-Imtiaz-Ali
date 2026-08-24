$ErrorActionPreference = "Stop"
$repoPath = "c:\Users\IJAZ AHMAD\Desktop\Internship Work\week5\task56"

Write-Host "=== E2E TEST ===" -ForegroundColor Cyan

# 1. Health
$h = Invoke-RestMethod "http://localhost:8000/health"
Write-Host "Backend version: $($h.version)" -ForegroundColor Green

# 2. Create REST API task
$body = @{ prompt = "create a rest api for user management"; repo_path = $repoPath } | ConvertTo-Json
$task = Invoke-RestMethod "http://localhost:8000/tasks" -Method POST -Body $body -ContentType "application/json"
Write-Host "Task ID  : $($task.task_id)"
Write-Host "Pattern  : $($task.pattern)"
Write-Host "File     : $($task.file_name)"
Write-Host "Status   : $($task.status)"

if ($task.pattern -ne "rest_api") {
    Write-Host "FAIL: wrong pattern $($task.pattern)" -ForegroundColor Red
    exit 1
}

# 3. Poll until complete
Write-Host "Polling..." -ForegroundColor Yellow
$done = $false
for ($i = 1; $i -le 20; $i++) {
    Start-Sleep -Seconds 1
    $t = Invoke-RestMethod "http://localhost:8000/tasks/$($task.task_id)"
    $comp  = @($t.sub_tasks | Where-Object { $_.status -eq "complete" }).Count
    $run   = @($t.sub_tasks | Where-Object { $_.status -eq "running"  }).Count
    $pend  = @($t.sub_tasks | Where-Object { $_.status -eq "pending"  }).Count
    Write-Host "  ${i}s  overall=$($t.status)  complete=$comp running=$run pending=$pend"
    if ($t.status -eq "complete") {
        Write-Host ""
        Write-Host "PASS: task complete" -ForegroundColor Green
        Write-Host "  File      : $($t.file_name)"
        Write-Host "  Code len  : $($t.generated_code.Length) chars"
        Write-Host "  File exists: $(Test-Path $t.file_path)"
        Write-Host ""
        Write-Host "Sub-task final states:" -ForegroundColor Cyan
        foreach ($st in $t.sub_tasks) {
            $icon = if ($st.status -eq "complete") { "[OK]" } else { "[??]" }
            Write-Host "  $icon $($st.name)"
        }
        Write-Host ""
        Write-Host "First 300 chars of generated code:" -ForegroundColor Cyan
        Write-Host ($t.generated_code.Substring(0, [Math]::Min(300, $t.generated_code.Length)))
        $done = $true
        break
    }
}

if (-not $done) {
    Write-Host "FAIL: timed out waiting for completion" -ForegroundColor Red
    exit 1
}

# 4. Test HTML page pattern
Write-Host ""
Write-Host "=== Testing HTML pattern ===" -ForegroundColor Cyan
$b2 = @{ prompt = "create an html page"; repo_path = $repoPath } | ConvertTo-Json
$t2 = Invoke-RestMethod "http://localhost:8000/tasks" -Method POST -Body $b2 -ContentType "application/json"
Write-Host "HTML task pattern: $($t2.pattern)  file: $($t2.file_name)"
if ($t2.pattern -eq "html_page") { Write-Host "PASS: HTML matched" -ForegroundColor Green }
else { Write-Host "FAIL: got $($t2.pattern)" -ForegroundColor Red }

# 5. Test fibonacci NOT matching rest api
Write-Host ""
Write-Host "=== Testing fibonacci does NOT match REST API ===" -ForegroundColor Cyan
$b3 = @{ prompt = "fibonacci sequence"; repo_path = $repoPath } | ConvertTo-Json
$t3 = Invoke-RestMethod "http://localhost:8000/tasks" -Method POST -Body $b3 -ContentType "application/json"
Write-Host "Fib task pattern: $($t3.pattern)  file: $($t3.file_name)"
if ($t3.pattern -eq "fibonacci") { Write-Host "PASS: fibonacci matched" -ForegroundColor Green }
else { Write-Host "FAIL: got $($t3.pattern)" -ForegroundColor Red }

Write-Host ""
Write-Host "=== ALL TESTS DONE ===" -ForegroundColor Green
