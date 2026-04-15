"""
Backfill historical data from GitHub and Spotify.
Populates the database with up to 2 years of historical data.

Usage:
    poetry run python scripts/backfill_data.py
"""
import sys
from pathlib import Path
from datetime import datetime

# Add src directory to path for imports when running from source checkout
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.config import get_settings
from pipeline.database import init_db
from pipeline_jobs.github_job import run_github_job
from pipeline_jobs.spotify_job import run_spotify_job
from pipeline_jobs.aggregation_job import run_aggregation_job
from loguru import logger


def main():
    """Run backfill process."""
    settings = get_settings()

    print("\n" + "=" * 60)
    print("Data Backfill Tool")
    print("=" * 60)

    # Setup logging
    logger.add(
        settings.log_file,
        rotation="00:00",
        retention="30 days",
        level=settings.log_level,
    )

    logger.info(f"Starting backfill in {settings.environment} mode")

    print(f"\nEnvironment: {settings.environment}")
    print(f"Database: {settings.database_url}")
    print(f"Backfill Period: {settings.github_backfill_days} days")

    # Initialize database
    print("\n1. Initializing database...")
    try:
        init_db()
        print("   ✓ Database initialized")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        sys.exit(1)

    # Collect GitHub data
    print("\n2. Collecting GitHub data...")
    try:
        run_github_job()
        print("   ✓ GitHub data collected and stored")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        logger.error(f"GitHub backfill failed: {str(e)}", exc_info=True)

    # Collect Spotify data
    print("\n3. Collecting Spotify data...")
    try:
        run_spotify_job()
        print("   ✓ Spotify data collected and stored")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        logger.error(f"Spotify backfill failed: {str(e)}", exc_info=True)

    # Run aggregation
    print("\n4. Calculating aggregations...")
    try:
        run_aggregation_job()
        print("   ✓ Daily aggregations calculated")
    except Exception as e:
        print(f"   ✗ Error: {str(e)}")
        logger.error(f"Aggregation failed: {str(e)}", exc_info=True)

    print("\n" + "=" * 60)
    print("✓ Backfill complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Start the scheduler: poetry run python -m pipeline_jobs.scheduler")
    print("  2. Start the API: poetry run python -m api.main")
    print("  3. Start the dashboard: poetry run python -m dashboard.app")


if __name__ == "__main__":
    main()
