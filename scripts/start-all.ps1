# Start both backend and frontend
$ProjectDir = "D:\股票程序\minervini-screener"

# Start backend (Python FastAPI)
$python = "C:\Program Files\Python39\python.exe"
$backendJob = Start-Job -Name "Backend" -ScriptBlock {
    param($dir, $python)
    Set-Location -LiteralPath $dir
    & $python app.py
} -ArgumentList $ProjectDir, $python

# Wait for backend
Start-Sleep -Seconds 8

# Test backend
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
    Write-Host "[OK] Backend: $($r | ConvertTo-Json -Compress)"
} catch {
    Write-Host "[FAIL] Backend: $_"
}

# Start frontend (Vite)
$npm = "npm"
$frontendJob = Start-Job -Name "Frontend" -ScriptBlock {
    param($dir, $npm)
    Set-Location -LiteralPath "$dir\frontend"
    & $npm run dev
} -ArgumentList $ProjectDir, $npm

Start-Sleep -Seconds 6

# Test frontend
try {
    $r = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 5 -UseBasicParsing
    Write-Host "[OK] Frontend: HTTP $($r.StatusCode)"
} catch {
    Write-Host "[FAIL] Frontend: $_"
}

Write-Host ""
Write-Host "=========================="
Write-Host "Backend:  http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"
Write-Host "Docs:     http://localhost:8000/docs"
Write-Host "=========================="
Write-Host ""
Write-Host "Jobs:"
Get-Job | Select-Object Id, Name, State
