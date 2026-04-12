@echo off
REM Launch the Hidden Opportunities Agent dashboard using the project venv.
REM Usage: run.bat

cd /d %~dp0

IF NOT EXIST ".venv\Scripts\activate.bat" (
    echo [error] Virtual environment not found. Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

call .venv\Scripts\activate.bat
echo [info] Using Python: %VIRTUAL_ENV%

REM Seed the database if it does not exist yet
IF NOT EXIST "data\db\opportunities.db" (
    echo [info] First run - seeding database...
    python scripts/seed_db.py
)

echo [info] Starting Streamlit dashboard at http://localhost:8501
streamlit run src/ui/app.py --server.port=8501 --server.headless=false
