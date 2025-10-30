@echo off
echo AI Takashi ローカル起動スクリプト
echo =================================

REM ローカルディレクトリを設定
set "LOCAL_DIR=C:\AI_Takashi"

echo ローカルディレクトリ: %LOCAL_DIR%

REM ローカルディレクトリが存在するかチェック
if not exist "%LOCAL_DIR%" (
    echo ❌ ローカルディレクトリが存在しません
    echo 💡 まず copy_to_local.bat を実行してください
    pause
    exit /b 1
)

REM ローカルディレクトリに移動
cd /d "%LOCAL_DIR%"

echo ✅ ローカルディレクトリに移動しました
echo 現在のディレクトリ: %CD%

REM サーバーを起動
echo サーバーを起動中...
call start_servers.bat

pause
