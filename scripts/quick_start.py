"""
Quick start script for the entire pipeline.
Sets up and starts all components.

Usage:
    poetry run python scripts/quick_start.py
"""
import sys
import subprocess
from pathlib import Path

# Add src directory to path for imports when running from source checkout
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.config import get_settings
from pipeline.database import init_db
from loguru import logger


def run_command(cmd: str, description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return False


def main():
    """Quick start the pipeline."""
    settings = get_settings()

    print("\n" + "=" * 60)
    print("Personal Data Analytics Dashboard - Quick Start")
    print("=" * 60)

    print(f"\nEnvironment: {settings.environment}")
    print(f"Database: {settings.database_url}")

    # Check credentials
    print("\n" + "-" * 60)
    print("Checking API Credentials")
    print("-" * 60)

    checks = {
        "GitHub Token": bool(settings.github_token),
        "GitHub Username": bool(settings.github_username),
        "Spotify Client ID": bool(settings.spotify_client_id),
        "Spotify Client Secret": bool(settings.spotify_client_secret),
    }

    for check_name, check_result in checks.items():
        status = "✓" if check_result else "✗"
        print(f"  {status} {check_name}")

    if not all(checks.values()):
        print("\n⚠ Warning: Some credentials are missing.")
        print("  Add missing credentials to .env file")
        print("  Copy from .env.example if needed: cp .env.example .env")

    # Initialize database
    print("\n" + "-" * 60)
    print("Database Setup")
    print("-" * 60)

    try:
        print("  Initializing database...")
        init_db()
        print("  ✓ Database tables created")
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        sys.exit(1)

    # Backfill data
    print("\n" + "-" * 60)
    print("Initial Data Collection")
    print("-" * 60)

    print("  Running backfill (this may take a minute)...")
    if run_command(
        "poetry run python scripts/backfill_data.py",
        "  Backfill"
    ):
        print("  ✓ Data backfill complete")
    else:
        print("  ⚠ Backfill had issues, continuing anyway...")

    # Summary
    print("\n" + "=" * 60)
    print("✓ Quick Start Complete!")
    print("=" * 60)

    print("\nNext, you can run these commands in separate terminals:")
    print("\n  1. Scheduler (data collection):")
    print("     poetry run python -m pipeline_jobs.scheduler")
    print("\n  2. API (backend):")
    print("     poetry run python -m api.main")
    print("\n  3. Dashboard (frontend):")
    print("     poetry run python -m dashboard.app")

    print("\nOr deploy to Railway:")
    print("  1. Push to GitHub")
    print("  2. Go to https://railway.app")
    print("  3. Connect your repository")
    print("  4. Add PostgreSQL service")
    print("  5. Deploy!")


if __name__ == "__main__":
    main()
