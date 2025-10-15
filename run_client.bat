@echo off
chcp 65001 > nul
echo ========================================
echo AI Takashi クライアント起動
echo ========================================
echo.

:: 仮想環境の確認
if not exist "venv" (
    echo ❌ 仮想環境が見つかりません
    echo まず setup_client.bat を実行してください
    pause
    exit /b 1
)

:: 必要なファイルの確認
if not exist "client_ui.py" (
    echo ❌ client_ui.py が見つかりません
    pause
    exit /b 1
)

if not exist "client_api.py" (
    echo ❌ client_api.py が見つかりません
    pause
    exit /b 1
)

:: 仮想環境をアクティベート
echo 仮想環境をアクティベート中...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ 仮想環境のアクティベートに失敗しました
    pause
    exit /b 1
)

:: クライアントを起動
echo.
echo クライアントを起動中...
echo サーバーに接続できない場合は、APIサーバーが起動しているか確認してください
echo.

python client_ui.py

:: エラーが発生した場合
if errorlevel 1 (
    echo.
    echo ❌ クライアントの起動に失敗しました
    echo エラーログを確認してください
    pause
)
