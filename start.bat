@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ===================================================
echo   時間割・教室自動割り当てシステム 起動スクリプト
echo ===================================================

cd /d "%~dp0backend"

:: .env ファイルが存在しない場合は、ひな形を作成
if not exist ".env" (
    echo [INFO] backend/.env が見つからないため、初期設定ファイルを作成します...
    (
        echo # Flask設定
        echo SECRET_KEY=dev-secret-key-12345
        echo ADMIN_USERNAME=admin
        echo ADMIN_PASSWORD=adminpassword123
        echo.
        echo # MySQL接続設定（環境に合わせて修正してください）
        echo MYSQL_HOST=localhost
        echo MYSQL_PORT=3306
        echo MYSQL_USER=root
        echo MYSQL_PASSWORD=root
        echo MYSQL_DATABASE=scrum_db
        echo.
        echo # または以下のように DATABASE_URL を直接指定することも可能です
        echo # DATABASE_URL=mysql+pymysql://root:root@localhost:3306/scrum_db
    ) > .env
    echo [INFO] backend/.env を作成しました。
    echo        パスワードやDB名が異なる場合は backend\.env を編集してください。
    echo ---------------------------------------------------
)

echo [INFO] アプリケーションを起動しています...
echo [INFO] URL: http://localhost:5000
echo [INFO] 管理者アカウント: admin / adminpassword123
echo ---------------------------------------------------

:: ブラウザを自動で開く
start http://localhost:5000

:: Python 3.13 でサーバー起動
py -3.13 app.py
if errorlevel 1 (
    echo.
    echo [ERROR] 起動に失敗しました。
    echo         MySQLが起動しているか、backend\.env の接続設定を確認してください。
    pause
)
