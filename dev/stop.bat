@echo off
echo Stopping dev backend (kills python.exe instances)
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID:"') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo Stopped.
pause
