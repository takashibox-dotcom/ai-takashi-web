@echo off
chcp 65001 > nul
echo ========================================
echo AI Takashi APIサーバー セットアップ
echo ========================================
echo.

:: Pythonの確認
echo [1/5] Pythonの確認中...
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Pythonがインストールされていません
    echo Python 3.8以上をインストールしてください
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)
echo ✅ Pythonが見つかりました

:: 仮想環境の作成
echo.
echo [2/5] 仮想環境を作成中...
if exist "venv" (
    echo 既存の仮想環境を削除中...
    rmdir /s /q venv
)

python -m venv venv
if errorlevel 1 (
    echo ❌ 仮想環境の作成に失敗しました
    pause
    exit /b 1
)
echo ✅ 仮想環境を作成しました

:: 仮想環境のアクティベート
echo.
echo [3/5] 仮想環境をアクティベート中...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ 仮想環境のアクティベートに失敗しました
    pause
    exit /b 1
)
echo ✅ 仮想環境をアクティベートしました

:: 依存関係のインストール
echo.
echo [4/5] 依存関係をインストール中...
pip install --upgrade pip
pip install fastapi uvicorn google-generativeai python-dotenv PyQt5 requests pillow cryptography

if errorlevel 1 (
    echo ❌ 依存関係のインストールに失敗しました
    pause
    exit /b 1
)
echo ✅ 依存関係をインストールしました

:: 必要なファイルの確認
echo.
echo [5/5] 必要なファイルを確認中...
set missing_files=0

if not exist "api_server.py" (
    echo ❌ api_server.py が見つかりません
    set missing_files=1
)

if not exist "text_build.py" (
    echo ❌ text_build.py が見つかりません
    set missing_files=1
)

if not exist "security_utils.py" (
    echo ❌ security_utils.py が見つかりません
    set missing_files=1
)

if not exist "custom_gpt_manager.py" (
    echo ❌ custom_gpt_manager.py が見つかりません
    set missing_files=1
)

if not exist "memory_manager.py" (
    echo ❌ memory_manager.py が見つかりません
    set missing_files=1
)

if not exist "response_time_manager.py" (
    echo ❌ response_time_manager.py が見つかりません
    set missing_files=1
)

if %missing_files%==1 (
    echo.
    echo ❌ 必要なファイルが見つかりません
    echo 元のプロジェクトファイルをすべてコピーしてください
    pause
    exit /b 1
)

echo ✅ 必要なファイルがすべて見つかりました

:: セットアップ完了
echo.
echo ========================================
echo セットアップ完了！
echo ========================================
echo.
echo 次の手順:
echo 1. 環境変数 GOOGLE_API_KEY を設定してください
echo 2. サーバーを起動してください (run_server.bat)
echo.
echo 注意事項:
echo - APIサーバーは localhost:8000 で起動します
echo - クライアントから接続する場合は同じネットワーク内である必要があります
echo.
pause
