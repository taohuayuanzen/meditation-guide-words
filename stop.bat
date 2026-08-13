@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Shutdown completed with exit code %EXIT_CODE%. Review the messages above.
  pause
)
exit /b %EXIT_CODE%
