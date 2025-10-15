@echo off
echo 🚀 GitHub Pages デプロイスクリプト
echo.

REM 現在のディレクトリを確認
if not exist "web-client" (
    echo ❌ web-client ディレクトリが見つかりません
    echo 💡 このスクリプトはプロジェクトルートで実行してください
    pause
    exit /b 1
)

echo 📁 プロジェクト構成を確認中...

REM Gitが初期化されているかチェック
if not exist ".git" (
    echo 🔧 Gitリポジトリを初期化中...
    git init
    echo ✅ Git初期化完了
)

REM ファイルを追加
echo 📝 ファイルを追加中...
git add .

REM 変更があるかチェック
git diff --cached --quiet
if errorlevel 1 (
    echo 💾 変更をコミット中...
    git commit -m "Deploy to GitHub Pages - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    echo ✅ コミット完了
) else (
    echo ℹ️  コミットする変更がありません
)

REM リモートリポジトリの確認
git remote -v >nul 2>&1
if errorlevel 1 (
    echo ⚠️  リモートリポジトリが設定されていません
    echo.
    echo 💡 以下のコマンドでリモートリポジトリを設定してください:
    echo    git remote add origin https://github.com/YOUR_USERNAME/ai-takashi-web.git
    echo.
    echo 📋 設定後、以下のコマンドでプッシュしてください:
    echo    git branch -M main
    echo    git push -u origin main
    echo.
    echo 🌐 GitHub Pagesの設定:
    echo    1. GitHubリポジトリの Settings → Pages
    echo    2. Source: Deploy from a branch
    echo    3. Branch: main, Folder: /web-client
    echo    4. Save
    echo.
    pause
    exit /b 0
)

echo 🚀 GitHubにプッシュ中...
git push origin main

if errorlevel 1 (
    echo ❌ プッシュに失敗しました
    echo 💡 以下を確認してください:
    echo    - GitHubの認証情報
    echo    - リモートリポジトリのURL
    echo    - インターネット接続
) else (
    echo ✅ プッシュ完了！
    echo.
    echo 🌐 デプロイ完了！
    echo 📱 GitHub Pagesの設定を確認してください:
    echo    1. GitHubリポジトリの Settings → Pages
    echo    2. Source: Deploy from a branch
    echo    3. Branch: main, Folder: /web-client
    echo    4. Save
    echo.
    echo ⏱️  デプロイには数分かかる場合があります
    echo 🔗 URL: https://YOUR_USERNAME.github.io/ai-takashi-web/
)

echo.
pause
