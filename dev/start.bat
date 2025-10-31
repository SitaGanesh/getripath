@echo off
title TSP Distance Optimizer - Quick Start (dev)
echo Starting backend (dev)...
start "TSP Optimizer - Backend Server" cmd /k "python .\app.py"
timeout /t 5 /nobreak >nul
start "" "%CD%\.\index.html"
pause
