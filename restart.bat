@echo off
chcp 65001 >nul
title 重启 StudyTrace 服务

:: 自动请求 UAC 管理员权限
%1 mshta vbscript:CreateObject("Shell.Application").ShellExecute("cmd.exe","/c %~s0 ::","","runas",1)(window.close)&&exit

echo ======================================================
echo  正在重启 StudyTrace 后端服务...
echo ======================================================
net stop StudyTrace
net start StudyTrace

echo.
echo ======================================================
echo  StudyTrace 服务已成功重启并生效！
echo ======================================================
timeout /t 3
