@REM Setup script for Personal Data Analytics Dashboard
@REM Run this with: setup.bat

@echo off
echo ========================================
echo Personal Data Analytics Dashboard Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo ^[1/4^] Installing Poetry...
pip install poetry
if errorlevel 1 (
    echo ERROR: Failed to install Poetry
    pause
    exit /b 1
)
echo OK

echo.
echo ^[2/4^] Installing project dependencies...
poetry install
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo OK

echo.
echo ^[3/4^] Initializing database...
poetry run python scripts/init_db.py
if errorlevel 1 (
    echo WARNING: Database initialization failed - continuing anyway
)
echo OK

echo.
echo ^[4/4^] Status check...
poetry --version
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Configure your API credentials in .env
echo   2. Run the backfill: poetry run python scripts/backfill_data.py
echo   3. Start the API: poetry run python -m api.main
echo   4. View docs: http://localhost:8000/docs
echo.
pause
