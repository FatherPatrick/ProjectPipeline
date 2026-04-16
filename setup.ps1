# PowerShell Setup Script for Personal Data Analytics Dashboard
# Run this with: .\setup.ps1

Write-Host "========================================"
Write-Host "Personal Data Analytics Dashboard Setup"
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Step 1: Check Python
Write-Host "[1/4] Checking Python installation..."
try {
    python --version
}
catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "OK" -ForegroundColor Green
Write-Host ""

# Step 2: Install Poetry
Write-Host "[2/4] Installing/updating Poetry..."
python -m pip install --upgrade poetry
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install Poetry" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "OK" -ForegroundColor Green
Write-Host ""

# Step 3: Install Project Dependencies
Write-Host "[3/4] Installing project dependencies..."
poetry install
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "OK" -ForegroundColor Green
Write-Host ""

# Step 4: Initialize Database
Write-Host "[4/4] Initializing database..."
poetry run python scripts/init_db.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Database initialization failed - continuing anyway" -ForegroundColor Yellow
}
Write-Host "OK" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "========================================"
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Configure your API credentials in .env"
Write-Host "  2. Start the app: poetry run python scripts/start_app.py"
Write-Host "  3. View API docs: http://localhost:8000/docs"
Write-Host "  4. Open dashboard: http://localhost:8050"
Write-Host ""
