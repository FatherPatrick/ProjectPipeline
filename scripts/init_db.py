"""
Database initialization script.
Run this to create all tables in the database.

Usage:
    python scripts/init_db.py
"""
import sys
from pathlib import Path

# Add src directory to path for imports when running from source checkout
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.database import init_db, drop_db, engine
from pipeline.models import Base
from pipeline.config import get_settings


def main():
    """Initialize the database."""
    settings = get_settings()
    
    print("=" * 60)
    print("Personal Data Analytics Dashboard - Database Initialization")
    print("=" * 60)
    print(f"\nEnvironment: {settings.environment}")
    print(f"Database URL: {settings.database_url}")
    print(f"Debug Mode: {settings.debug}\n")
    
    try:
        # Check if database exists
        print("Testing database connection...")
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        print("✓ Database connection successful\n")
        
        # Create tables
        print("Creating database tables...")
        init_db()
        
        print("\nDatabase initialization complete!")
        print("\nTables created:")
        print("  - users")
        print("  - github_repositories")
        print("  - github_commits")
        print("  - github_contributions")
        print("  - spotify_artists")
        print("  - spotify_tracks")
        print("  - spotify_track_artists")
        print("  - listening_sessions")
        print("  - daily_aggregations")
        
        print("\n" + "=" * 60)
        print("✓ Database ready for data collection!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error initializing database: {e}")
        print("\nMake sure:")
        print("  1. PostgreSQL is running")
        print("  2. DATABASE_URL in .env is correct")
        print("  3. The database exists and is accessible")
        sys.exit(1)


if __name__ == "__main__":
    main()
