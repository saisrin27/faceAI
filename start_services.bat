@echo off
title Face AI Attendance System Launcher
echo ========================================================
echo   Face AI Attendance System Setup and Launcher
echo ========================================================
echo.
echo Step 1: Installing Python dependencies...
echo.
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo Warning: Some dependencies failed to install or pip is not on your path.
    echo Please make sure you have python installed and pip is available.
)
echo.
echo Step 2: Launching Backend (FastAPI)...
echo.
start "Face AI API - Backend" cmd /k "uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"

echo Step 3: Waiting 5 seconds for backend server initialization...
timeout /t 5 /nobreak

echo.
echo Step 4: Launching Frontend (Streamlit UI)...
echo.
start "Face AI UI - Frontend" cmd /k "streamlit run frontend/app.py"

echo.
echo ========================================================
echo   Launch Completed!
echo   Keep both opened terminal windows running to use system.
echo ========================================================
echo.
pause
