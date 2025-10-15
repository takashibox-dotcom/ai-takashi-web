@echo off
echo AI Takashi Web Client を起動中...
echo.

REM Pythonがインストールされているかチェック
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Pythonがインストールされていません
    echo 💡 Python 3.7以上をインストールしてください
    pause
    exit /b 1
)

REM サーバー起動
echo 🌐 Webクライアントサーバーを起動しています...
python serve.py

pause
