$ErrorActionPreference = "Stop"

$backendPath = Join-Path $PSScriptRoot "backend"
Set-Location -Path $backendPath

if (-not (Test-Path -LiteralPath ".env")) {
    Write-Host "[INFO] Creating backend/.env with the default SQLite settings." -ForegroundColor Yellow
    @'
SECRET_KEY=dev-secret-key-12345
ADMIN_USERNAME=admin
ADMIN_PASSWORD=adminpassword123
DATABASE_URL=sqlite:///school_db.sqlite
'@ | Set-Content -LiteralPath ".env" -Encoding utf8
}

Write-Host "[INFO] Starting the application..." -ForegroundColor Green
Write-Host "[INFO] URL: http://localhost:5000" -ForegroundColor Green
Write-Host "[INFO] Login: admin / adminpassword123" -ForegroundColor Green

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    & $venvPython "app.py"
} else {
    Write-Host "[WARN] .venv was not found. Using the Python launcher." -ForegroundColor Yellow
    & py -3.13 "app.py"
}
