@echo off
setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PY=%ROOT%\.venv\Scripts\python.exe"
set "NSSM=C:\tools\nssm\nssm.exe"
set "STDERR=%ROOT%\data\studytrace-stderr.log"

echo ===================================================
echo   StudyTrace service repair (stop - clean - register - start)
echo   No code or data will be changed.
echo ===================================================
echo.

echo [0/5] Self-check...
if not exist "%PY%" ( echo [FAIL] venv python not found: %PY% & goto :fail )
if not exist "%NSSM%" ( echo [FAIL] nssm not found: %NSSM% & goto :fail )
echo   venv python and nssm both exist.
echo.

echo [1/5] Stopping old service (if running)...
"%NSSM%" stop StudyTrace
ping -n 4 127.0.0.1 >nul

echo [2/5] Freeing port 28000 (if occupied)...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 28000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"
ping -n 2 127.0.0.1 >nul

echo [3/5] Removing old service registration...
"%NSSM%" remove StudyTrace confirm

echo [4/5] Registering service...
"%NSSM%" install StudyTrace "%PY%" "run.py"
"%NSSM%" set StudyTrace AppDirectory "%ROOT%"
"%NSSM%" set StudyTrace AppStdout "%ROOT%\data\studytrace-stdout.log"
"%NSSM%" set StudyTrace AppStderr "%STDERR%"
"%NSSM%" set StudyTrace AppEnvironmentExtra PYTHONUTF8=1
"%NSSM%" set StudyTrace ObjectName LocalSystem
"%NSSM%" set StudyTrace Start SERVICE_AUTO_START
"%NSSM%" set StudyTrace DisplayName "StudyTrace Backend Server"

echo [5/5] Starting service...
"%NSSM%" start StudyTrace
ping -n 13 127.0.0.1 >nul

"%NSSM%" status StudyTrace
echo.
echo === last 30 lines of stderr log (shown if start failed) ===
powershell -NoProfile -Command "Get-Content '%STDERR%' -Tail 30 -ErrorAction SilentlyContinue"
echo.
echo If you see SERVICE_RUNNING above, refresh the phone.
echo If SERVICE_STOPPED, send me a screenshot of this window.
goto :done

:fail
echo.
echo Self-check failed. Nothing was changed. Check the messages above.

:done
echo.
pause
