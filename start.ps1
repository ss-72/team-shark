$ErrorActionPreference = "Stop"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  時間割・教室自動割り当てシステム 起動スクリプト" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

Set-Location -Path "$PSScriptRoot\backend"

if (-not (Test-Path ".env")) {
    Write-Host "[INFO] backend/.env が見つからないため初期設定ファイルを作成します..." -ForegroundColor Yellow
    @"
# Flask設定
SECRET_KEY=dev-secret-key-12345
ADMIN_USERNAME=admin
ADMIN_PASSWORD=adminpassword123

# MySQL接続設定（環境に合わせて修正してください）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=scrum_db
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "[INFO] backend/.env を作成しました。" -ForegroundColor Green
    Write-Host "       MySQLの接続設定が異なる場合は backend\.env を編集してください。" -ForegroundColor Gray
}

Write-Host "[INFO] アプリケーションを起動しています..." -ForegroundColor Green
Write-Host "[INFO] URL: http://localhost:5000" -ForegroundColor Green
Write-Host "[INFO] 管理者アカウント: admin / adminpassword123" -ForegroundColor Green
Write-Host "---------------------------------------------------" -ForegroundColor Cyan

# ブラウザを開く
Start-Process "http://localhost:5000"

# Python起動
py -3.13 app.py
