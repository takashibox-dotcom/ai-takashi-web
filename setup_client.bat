@echo off
chcp 65001 > nul
echo ========================================
echo AI Takashi クライアント セットアップ
echo ========================================
echo.

:: Pythonの確認
echo [1/4] Pythonの確認中...
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
echo [2/4] 仮想環境を作成中...
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
echo [3/4] 仮想環境をアクティベート中...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ 仮想環境のアクティベートに失敗しました
    pause
    exit /b 1
)
echo ✅ 仮想環境をアクティベートしました

:: 依存関係のインストール
echo.
echo [4/4] 依存関係をインストール中...
pip install --upgrade pip
pip install PyQt5 requests fastapi uvicorn

if errorlevel 1 (
    echo ❌ 依存関係のインストールに失敗しました
    pause
    exit /b 1
)
echo ✅ 依存関係をインストールしました

:: セットアップ完了
echo.
echo ========================================
echo セットアップ完了！
echo ========================================
echo.
echo 次の手順:
echo 1. APIサーバーを起動してください (api_server.py)
echo 2. クライアントを起動してください (run_client.bat)
echo.
echo 必要なファイル:
echo - client_ui.py (クライアントUI)
echo - client_api.py (API通信モジュール)
echo.
pause
