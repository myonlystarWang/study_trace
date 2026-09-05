@echo off
chcp 65001 >nul
title 学迹 StudyTrace

set "PATH=%USERPROFILE%\.local\bin;%PATH%"

where fnm >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=*" %%i in ('fnm env --use-on-cd') do %%i
)

where uv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [错误] 未找到 uv 包管理器，请检查是否已正确安装。
    pause
    exit /b 1
)

echo [学迹 StudyTrace] 正在启动...
uv run python run.py %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo [提示] 程序异常退出，请查看上方报错信息。
    pause
)
