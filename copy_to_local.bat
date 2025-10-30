@echo off
echo AI Takashi をローカルディレクトリにコピーします
echo ================================================

REM ローカルディレクトリを設定
set "LOCAL_DIR=C:\AI_Takashi"

echo コピー先: %LOCAL_DIR%

REM ローカルディレクトリを作成
if not exist "%LOCAL_DIR%" mkdir "%LOCAL_DIR%"

echo ファイルをコピー中...
xcopy "%~dp0*" "%LOCAL_DIR%\" /E /I /Y

echo ================================================
echo ✅ コピーが完了しました
echo ローカルディレクトリ: %LOCAL_DIR%
echo ================================================
echo ローカルディレクトリでサーバーを起動しますか？ (Y/N)
set /p choice="選択: "

if /i "%choice%"=="Y" (
    echo ローカルディレクトリに移動してサーバーを起動...
    cd /d "%LOCAL_DIR%"
    call start_servers.bat
) else (
    echo 手動で起動する場合:
    echo cd /d "%LOCAL_DIR%"
    echo start_servers.bat
)

pause
