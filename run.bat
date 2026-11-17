@echo off
REM Launch the Hidden Opportunities Agent (FastAPI backend + React frontend).
REM Usage: run.bat

cd /d %~dp0

IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo [error] Virtual environment not found.
    echo         Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

call .venv\Scripts\activate.bat
echo [info] Using Python: %VIRTUAL_ENV%

REM Seed the database if it does not exist yet
IF NOT EXIST "data\db\opportunities.db" (
    echo [info] First run - seeding database...
    python scripts/seed_db.py
    python scripts/run_detection.py
)

REM Start FastAPI backend in a new window
echo [info] Starting FastAPI backend at http://localhost:8000
start "HOA Backend" cmd /k "uvicorn backend.main:app --reload --port 8000"

REM Start React frontend in a new window
echo [info] Starting React frontend at http://localhost:5173
start "HOA Frontend" cmd /k "cd frontend && npm run dev"

REM Wait a moment then open the browser
timeout /t 4 /nobreak >nul
start http://localhost:5173

echo [info] Both servers started. Close their windows to stop.
