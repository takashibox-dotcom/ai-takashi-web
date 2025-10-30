@echo off
echo AI Takashi Web Client を起動中...
echo.

REM 現在のディレクトリを取得
set "CURRENT_DIR=%~dp0"
echo 現在のディレクトリ: %CURRENT_DIR%

REM Pythonがインストールされているかチェック
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Pythonがインストールされていません
    echo 💡 Python 3.7以上をインストールしてください
    pause
    exit /b 1
)

REM UNCパスの場合は一時ディレクトリにコピーして実行
echo %CURRENT_DIR% | findstr /C:"\\" >nul
if not errorlevel 1 (
    echo ⚠️  UNCパスが検出されました。一時ディレクトリにコピーして実行します...
    
    REM 一時ディレクトリを作成
    set "TEMP_DIR=%TEMP%\ai_takashi_web_client"
    if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
    
    REM ファイルをコピー
    copy "%CURRENT_DIR%serve.py" "%TEMP_DIR%\" >nul
    copy "%CURRENT_DIR%index.html" "%TEMP_DIR%\" >nul
    copy "%CURRENT_DIR%app.js" "%TEMP_DIR%\" >nul
    copy "%CURRENT_DIR%styles.css" "%TEMP_DIR%\" >nul
    copy "%CURRENT_DIR%config.js" "%TEMP_DIR%\" >nul
    copy "%CURRENT_DIR%404.html" "%TEMP_DIR%\" >nul
    
    echo ✅ ファイルを一時ディレクトリにコピーしました: %TEMP_DIR%
    
    REM 一時ディレクトリで実行
    cd /d "%TEMP_DIR%"
    echo 🌐 Webクライアントサーバーを起動しています...
    python serve.py
) else (
    REM 通常のパスの場合は直接実行
    echo 🌐 Webクライアントサーバーを起動しています...
    cd /d "%CURRENT_DIR%"
    python serve.py
)

pause
