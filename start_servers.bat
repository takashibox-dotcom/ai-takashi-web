@echo off
echo AI Takashi サーバー起動スクリプト
echo ================================

REM 現在のディレクトリを取得
set "MAIN_DIR=%~dp0"
set "WEB_DIR=%MAIN_DIR%web-client"

echo メインディレクトリ: %MAIN_DIR%
echo Webディレクトリ: %WEB_DIR%

REM UNCパスかどうかチェック
echo %MAIN_DIR% | findstr /C:"\\" >nul
if not errorlevel 1 (
    echo ⚠️  UNCパスが検出されました。一時ディレクトリを使用します...
    
    REM 一時ディレクトリを作成
    set "TEMP_MAIN=%TEMP%\ai_takashi_main"
    set "TEMP_WEB=%TEMP%\ai_takashi_web"
    
    if not exist "%TEMP_MAIN%" mkdir "%TEMP_MAIN%"
    if not exist "%TEMP_WEB%" mkdir "%TEMP_WEB%"
    
    REM メインファイルをコピー
    copy "%MAIN_DIR%api_server.py" "%TEMP_MAIN%\" >nul
    copy "%MAIN_DIR%user_manager.py" "%TEMP_MAIN%\" >nul
    copy "%MAIN_DIR%custom_gpt_manager.py" "%TEMP_MAIN%\" >nul
    copy "%MAIN_DIR%memory_manager.py" "%TEMP_MAIN%\" >nul
    copy "%MAIN_DIR%image_recognition_manager.py" "%TEMP_MAIN%\" >nul
    copy "%MAIN_DIR%security_utils.py" "%TEMP_MAIN%\" >nul
    copy "%MAIN_DIR%text_build.py" "%TEMP_MAIN%\" >nul
    copy "%MAIN_DIR%users.json" "%TEMP_MAIN%\" >nul
    copy "%MAIN_DIR%requirements.txt" "%TEMP_MAIN%\" >nul
    
    REM Webファイルをコピー
    copy "%WEB_DIR%\*" "%TEMP_WEB%\" >nul
    
    echo ✅ ファイルを一時ディレクトリにコピーしました
    
    echo APIサーバーを起動中...
    start "API Server" cmd /k "cd /d \"%TEMP_MAIN%\" && python api_server.py"
    
    echo 3秒待機中...
    timeout /t 3 /nobreak > nul
    
    echo Webクライアントを起動中...
    start "Web Client" cmd /k "cd /d \"%TEMP_WEB%\" && python serve.py"
    
) else (
    REM 通常のパスの場合は直接実行
    echo APIサーバーを起動中...
    start "API Server" cmd /k "cd /d \"%MAIN_DIR%\" && python api_server.py"
    
    echo 3秒待機中...
    timeout /t 3 /nobreak > nul
    
    echo Webクライアントを起動中...
    start "Web Client" cmd /k "cd /d \"%WEB_DIR%\" && python serve.py"
)

echo ================================
echo 両方のサーバーが起動しました
echo API Server: http://localhost:8000
echo Web Client: http://localhost:3000
echo ================================
echo このウィンドウを閉じてもサーバーは動作し続けます
pause
