@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if "%~1"=="" (
  start "" pythonw -m citizensolver.launcher
) else (
  python -m citizensolver %*
)
exit /b %errorlevel%
