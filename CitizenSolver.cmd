@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if "%~1"=="" (
  python -m citizensolver --help
) else (
  python -m citizensolver %*
)
exit /b %errorlevel%
