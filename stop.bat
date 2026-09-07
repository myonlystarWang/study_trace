@echo off
chcp 65001 >nul
echo [StudyTrace] Stopping background service on port 28000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":28000" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
taskkill /f /im cloudflared.exe >nul 2>&1
echo [StudyTrace] Service and tunnel stopped.
