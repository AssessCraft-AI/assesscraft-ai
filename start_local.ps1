# ==============================================================================
# AssessCraft AI - Local Deployment & Service Runner (Windows PowerShell)
# Starts FastAPI backend (port 8080) and Next.js frontend (port 3000)
# ==============================================================================

$rootDir = $PSScriptRoot
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  🚀 AssessCraft AI - Local Stack Launch (Windows)        " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start Frontend (Next.js)
Write-Host "[Frontend] Starting Next.js Frontend (port 3000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Next.js Frontend...' -ForegroundColor Cyan; cd '$frontendDir'; npm run dev"

# 2. Resolve Python interpreter (prefer repo virtual environment if present)
$python = "python"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
    Write-Host "Using virtual environment: $venvPython" -ForegroundColor Gray
}

# 3. Start FastAPI Backend (port 8080)
Write-Host "[Backend] Starting FastAPI Backend (port 8080)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting FastAPI Backend...' -ForegroundColor Cyan; cd '$backendDir'; & '$python' -m uvicorn app.main:app --host 0.0.0.0 --port 8080"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Launch commands initiated in separate windows!          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Frontend:  http://localhost:3000                         " -ForegroundColor White
Write-Host "  Backend:   http://localhost:8080                         " -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan
