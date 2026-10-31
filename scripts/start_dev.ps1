$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath (Join-Path $projectRoot ".env"))) {
    throw "Missing .env. Run scripts\configure_local.ps1 first."
}
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing virtual environment. Run: python -m venv .venv"
}

Push-Location $projectRoot
try {
    & $python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
    & $python -m uvicorn app.main:app --reload
}
finally {
    Pop-Location
}
