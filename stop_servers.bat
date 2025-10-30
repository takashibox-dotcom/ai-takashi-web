@echo off
chcp 65001 >nul
echo AI Takashi Server Stop
echo ======================

echo Stopping API Server (port 8000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Killing process %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo Stopping Web Client (port 3000)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do (
    echo Killing process %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo ======================
echo Servers stopped!
echo ======================
pause
