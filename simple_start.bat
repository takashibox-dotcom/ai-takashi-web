@echo off
chcp 65001 >nul
echo AI Takashi Simple Startup
echo =========================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)

REM Check if API Server is already running
netstat -ano | findstr :8000 >nul 2>&1
if not errorlevel 1 (
    echo API Server is already running on port 8000
) else (
    echo Starting API Server...
    start "AI Takashi API Server" cmd /k "cd /d %~dp0 && python api_server.py"
)

REM Wait
echo Waiting 3 seconds...
timeout /t 3 /nobreak >nul

REM Check if Web Client is already running
netstat -ano | findstr :3000 >nul 2>&1
if not errorlevel 1 (
    echo Web Client is already running on port 3000
) else (
    echo Starting Web Client...
    start "AI Takashi Web Client" cmd /k "cd /d %~dp0web-client && python serve.py"
)

echo =========================
echo Servers started!
echo API: http://localhost:8000
echo Web: http://localhost:3000
echo =========================
echo.
echo Press any key to close this window...
pause >nul
