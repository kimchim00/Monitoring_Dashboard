@echo off
echo Starting Monitoring Dashboard...
echo.

REM Check that dependencies are installed
if not exist "frontend\node_modules" (
    echo ERROR: Frontend dependencies not installed.
    echo Run: cd frontend ^&^& npm install
    pause
    exit /b 1
)

echo Starting Monitoring API on port 8002...
start "Monitoring API" cmd /k "cd /d %~dp0backend && uvicorn main:app --reload --port 8002"

REM Wait a moment for the API to start
timeout /t 2 /nobreak > nul

echo Starting Monitoring Frontend on port 4000...
start "Monitoring Frontend" cmd /k "cd /d %~dp0frontend && npm start"

echo.
echo All services starting in separate windows.
echo.
echo   Monitoring API:        http://localhost:8002
echo   Monitoring Dashboard:  http://localhost:4000
echo   API Docs:              http://localhost:8002/docs
echo.
echo Close each terminal window to stop its service.
