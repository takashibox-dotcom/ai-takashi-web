# AI Takashi サーバー起動スクリプト (PowerShell版)
Write-Host "AI Takashi サーバー起動スクリプト" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# 現在のディレクトリを取得
$MainDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WebDir = Join-Path $MainDir "web-client"

Write-Host "メインディレクトリ: $MainDir" -ForegroundColor Yellow
Write-Host "Webディレクトリ: $WebDir" -ForegroundColor Yellow

# UNCパスかどうかチェック
if ($MainDir -like "\\*") {
    Write-Host "⚠️  UNCパスが検出されました。一時ディレクトリを使用します..." -ForegroundColor Yellow
    
    # 一時ディレクトリを作成
    $TempMain = Join-Path $env:TEMP "ai_takashi_main"
    $TempWeb = Join-Path $env:TEMP "ai_takashi_web"
    
    if (!(Test-Path $TempMain)) { New-Item -ItemType Directory -Path $TempMain -Force | Out-Null }
    if (!(Test-Path $TempWeb)) { New-Item -ItemType Directory -Path $TempWeb -Force | Out-Null }
    
    # ファイルをコピー
    Copy-Item "$MainDir\*.py" $TempMain -Force
    Copy-Item "$MainDir\*.json" $TempMain -Force
    Copy-Item "$MainDir\*.txt" $TempMain -Force
    Copy-Item "$WebDir\*" $TempWeb -Force
    
    Write-Host "✅ ファイルを一時ディレクトリにコピーしました" -ForegroundColor Green
    
    # APIサーバーを起動
    Write-Host "APIサーバーを起動中..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$TempMain'; python api_server.py" -WindowStyle Normal
    
    # 3秒待機
    Write-Host "3秒待機中..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    # Webクライアントを起動
    Write-Host "Webクライアントを起動中..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$TempWeb'; python serve.py" -WindowStyle Normal
    
} else {
    # 通常のパスの場合は直接実行
    # APIサーバーを起動
    Write-Host "APIサーバーを起動中..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$MainDir'; python api_server.py" -WindowStyle Normal
    
    # 3秒待機
    Write-Host "3秒待機中..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    # Webクライアントを起動
    Write-Host "Webクライアントを起動中..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$WebDir'; python serve.py" -WindowStyle Normal
}

Write-Host "================================" -ForegroundColor Green
Write-Host "両方のサーバーが起動しました" -ForegroundColor Green
Write-Host "API Server: http://localhost:8000" -ForegroundColor White
Write-Host "Web Client: http://localhost:3000" -ForegroundColor White
Write-Host "================================" -ForegroundColor Green
Write-Host "このウィンドウを閉じてもサーバーは動作し続けます" -ForegroundColor Yellow

Read-Host "Enterキーを押して終了"
