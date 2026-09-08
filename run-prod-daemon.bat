@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set "FNM_NODE_DIR=%APPDATA%\fnm\node-versions\v22.23.2\installation"
set "FNM_BIN_DIR=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Schniz.fnm_Microsoft.Winget.Source_8wekyb3d8bbwe"
set "UV_BIN_DIR=%USERPROFILE%\.local\bin"
set "CLOUDFLARED_DIR=C:\Program Files (x86)\cloudflared"

set "PATH=%FNM_NODE_DIR%;%FNM_BIN_DIR%;%UV_BIN_DIR%;%CLOUDFLARED_DIR%;%PATH%"

cd /d "D:\工作\ww\personal_work\study_trace"

rem 协议由 %USERPROFILE%\.cloudflared\config.yml 的 protocol 决定，当前 http2
start "" /b cloudflared.exe --logfile "data\cloudflared.log" tunnel run study-trace
uv.exe run python run.py
