@echo off
chcp 65001 > nul
echo ========================================
echo AI Takashi APIサーバー起動
echo ========================================
echo.

:: 仮想環境の確認
if not exist "venv" (
    echo ❌ 仮想環境が見つかりません
    echo まず setup_server.bat を実行してください
    pause
    exit /b 1
)

:: 必要なファイルの確認
if not exist "api_server.py" (
    echo ❌ api_server.py が見つかりません
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

:: 環境変数の確認
echo.
echo 環境変数を確認中...
python -c "import os; print('GOOGLE_API_KEY:', '設定済み' if os.getenv('GOOGLE_API_KEY') else '未設定')" 2>nul
if errorlevel 1 (
    echo ❌ Pythonの実行に失敗しました
    pause
    exit /b 1
)

:: サーバーを起動
echo.
echo APIサーバーを起動中...
echo サーバーURL: http://localhost:8000
echo ドキュメント: http://localhost:8000/docs
echo.
echo サーバーを停止するには Ctrl+C を押してください
echo.

python api_server.py

:: エラーが発生した場合
if errorlevel 1 (
    echo.
    echo ❌ サーバーの起動に失敗しました
    echo エラーログを確認してください
    echo.
    echo 一般的な問題:
    echo - GOOGLE_API_KEY が設定されていない
    echo - 必要なファイルが不足している
    echo - ポート8000が既に使用されている
    pause
)
