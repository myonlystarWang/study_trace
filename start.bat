@echo off
title StudyTrace

set "FNM_NODE_DIR=%APPDATA%\fnm\node-versions\v22.23.2\installation"
set "FNM_BIN_DIR=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Schniz.fnm_Microsoft.Winget.Source_8wekyb3d8bbwe"
set "UV_BIN_DIR=%USERPROFILE%\.local\bin"

if exist "%FNM_NODE_DIR%" (
    set "PATH=%FNM_NODE_DIR%;%FNM_BIN_DIR%;%UV_BIN_DIR%;%PATH%"
) else (
    set "PATH=%FNM_BIN_DIR%;%UV_BIN_DIR%;%PATH%"
)

where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv is not found in PATH or %UV_BIN_DIR%.
    pause
    exit /b 1
)

echo [StudyTrace] Starting service...
uv run python run.py %*
if errorlevel 1 (
    echo.
    echo [Notice] Service exited with error. Check logs above.
    pause
)
