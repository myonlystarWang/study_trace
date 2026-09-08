@echo off
chcp 65001 >nul
rem 单独启动/重启 cloudflared 隧道（不影响已在运行的后端服务）
rem 协议由 config\cloudflared\config.yml 的 protocol 决定，当前为 http2

set "CLOUDFLARED_DIR=C:\Program Files (x86)\cloudflared"
set "PATH=%CLOUDFLARED_DIR%;%PATH%"

cd /d "D:\工作\ww\personal_work\study_trace"

taskkill /IM cloudflared.exe /F >nul 2>&1
start "" /b cloudflared.exe --config "D:\工作\ww\personal_work\study_trace\config\cloudflared\config.yml" --logfile "D:\工作\ww\personal_work\study_trace\data\cloudflared.log" tunnel run study-trace
echo tunnel restarted (http2)
