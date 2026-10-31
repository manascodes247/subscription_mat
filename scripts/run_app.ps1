# Brightloop Application Launcher
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "       BRIGHTLOOP SUBSCRIPTION MANAGEMENT          " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Ensure .env exists
$envFile = Join-Path $projectRoot ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Host "[1/4] Generating default .env file..." -ForegroundColor Yellow
    @"
DATABASE_URL=sqlite:///./brightloop.db
BRIGHTLOOP_SECRET_KEY=development-only-secret-key-that-is-at-least-64-characters-long-for-security-brightloop
BRIGHTLOOP_ENV=development
BRIGHTLOOP_TOKEN_HOURS=8
BRIGHTLOOP_BILLING_TIMEZONE=Asia/Kolkata
BRIGHTLOOP_CURRENCY=INR
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173
"@ | Out-File -FilePath $envFile -Encoding utf8
}

# 2. Database migration & seed
Push-Location $projectRoot
try {
    Write-Host "[2/4] Running database migrations..." -ForegroundColor Yellow
    & $python -m alembic upgrade head

    Write-Host "[3/4] Seeding demonstration data..." -ForegroundColor Yellow
    & $python -m scripts.seed_demo_data
} finally {
    Pop-Location
}

# 3. Launch Backend and Frontend
Write-Host "[4/4] Starting Brightloop Backend and Frontend..." -ForegroundColor Green
Write-Host ""
Write-Host "Services will be accessible at:" -ForegroundColor Cyan
Write-Host "  * Web Application: http://localhost:5173" -ForegroundColor White
Write-Host "  * Swagger API Docs: http://127.0.0.1:8001/docs" -ForegroundColor White
Write-Host "  * API Health Check: http://127.0.0.1:8001/health" -ForegroundColor White
Write-Host ""
Write-Host "Pre-seeded Accounts:" -ForegroundColor Cyan
Write-Host "  * Admin:    admin@example.com    / Admin!Brightloop2026" -ForegroundColor White
Write-Host "  * Staff:    staff@example.com    / Staff!Brightloop2026" -ForegroundColor White
Write-Host "  * Customer: customer@example.com / Customer!Brightloop2026" -ForegroundColor White
Write-Host ""

# Start Backend on port 8001 and Frontend
$backendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload" -PassThru
$frontendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\frontend'; npm run dev" -PassThru

Write-Host "Backend (PID $($backendProcess.Id)) and Frontend (PID $($frontendProcess.Id)) launched successfully in separate terminal windows." -ForegroundColor Green
