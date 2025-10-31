@echo off
REM =================================================================
REM Run Complete Application - Frontend + Backend (dev folder copy)
REM =================================================================

title TSP Distance Optimizer - Application Runner (dev)

echo.
echo ============================================================
echo   TSP Distance Optimizer - Starting Application (dev)
echo ============================================================
echo.

REM Start backend in a new window
start "TSP Optimizer - Backend Server" cmd /k "python .\app.py"

REM Wait for backend to start
echo [WAIT] Waiting for backend to start (5 seconds)...
timeout /t 5 /nobreak >nul

REM Open frontend
start "" "http://localhost:5000/ui/"

pause
