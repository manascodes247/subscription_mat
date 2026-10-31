param(
    [string]$DatabaseHost = "localhost",
    [int]$DatabasePort = 5432,
    [string]$DatabaseName = "brightloop",
    [string]$DatabaseUser = "brightloop_app"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"

if (Test-Path -LiteralPath $envFile) {
    $replace = Read-Host ".env already exists. Replace it? (yes/no)"
    if ($replace -ne "yes") {
        Write-Host "Configuration unchanged."
        exit 0
    }
}

$securePassword = Read-Host "PostgreSQL password for $DatabaseUser" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    $encodedPassword = [Uri]::EscapeDataString($plainPassword)
    $secretBytes = New-Object byte[] 48
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($secretBytes) } finally { $rng.Dispose() }
    $jwtSecret = [Convert]::ToBase64String($secretBytes)
    $lines = @(
        "DATABASE_URL=postgresql+psycopg://${DatabaseUser}:${encodedPassword}@${DatabaseHost}:${DatabasePort}/${DatabaseName}",
        "BRIGHTLOOP_SECRET_KEY=$jwtSecret",
        "BRIGHTLOOP_ENV=development",
        "BRIGHTLOOP_TOKEN_HOURS=8",
        "BRIGHTLOOP_BILLING_TIMEZONE=Asia/Kolkata",
        "BRIGHTLOOP_CURRENCY=INR",
        "REDIS_URL=redis://localhost:6379/0",
        "FRONTEND_URL=http://localhost:5173",
        "CORS_ORIGINS=http://localhost:5173",
        "DB_POOL_SIZE=10",
        "DB_MAX_OVERFLOW=20",
        "DB_POOL_RECYCLE_SECONDS=1800",
        "SMTP_HOST=",
        "SMTP_PORT=587",
        "SMTP_FROM=",
        "SMTP_USERNAME=",
        "SMTP_PASSWORD=",
        "SMTP_STARTTLS=true",
        "STRIPE_SECRET_KEY=",
        "STRIPE_PUBLISHABLE_KEY=",
        "STRIPE_WEBHOOK_SECRET="
    )
    [IO.File]::WriteAllLines($envFile, $lines, [Text.UTF8Encoding]::new($false))
    Write-Host "Created $envFile. Secrets were not printed."
}
finally {
    if ($passwordPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer) }
    $plainPassword = $null
}
