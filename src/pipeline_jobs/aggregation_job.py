"""
Aggregation job for calculating daily metrics.
Aggregates GitHub and Spotify data into daily summaries.
"""
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from loguru import logger

from pipeline.database import SessionLocal
from pipeline.models import (
    User,
    GitHubContribution,
    ListeningSession,
    DailyAggregation,
)


def run_aggregation_job():
    """
    Main aggregation job.
    Calculates and stores daily aggregated metrics from all data sources.
    """
    logger.info("=" * 60)
    logger.info("Daily Aggregation Job Started")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # Get all users
        users = db.query(User).all()
        logger.info(f"Aggregating data for {len(users)} users")

        for user in users:
            _aggregate_user_data(db, user)

        logger.info("✓ Aggregation job completed successfully")

    except Exception as e:
        logger.error(f"Aggregation job failed: {str(e)}")
        db.rollback()
        raise

    finally:
        db.close()


def _aggregate_user_data(db: Session, user: User):
    """Aggregate data for a single user."""
    logger.debug(f"Aggregating data for user: {user.username}")

    # Get date range for aggregation
    # Aggregate last 30 days by default
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    current_date = start_date
    while current_date <= end_date:
        # Check if aggregation already exists
        existing = db.query(DailyAggregation).filter(
            DailyAggregation.user_id == user.id,
            DailyAggregation.aggregation_date == current_date,
        ).first()

        if not existing:
            aggregation = _calculate_daily_metrics(db, user, current_date)
            if aggregation:
                db.add(aggregation)

        current_date += timedelta(days=1)

    db.commit()
    logger.debug(f"Aggregations stored for {user.username}")


def _calculate_daily_metrics(db: Session, user: User, target_date: date) -> DailyAggregation:
    """Calculate metrics for a single day."""
    # GitHub metrics
    github_contrib = db.query(GitHubContribution).filter(
        GitHubContribution.user_id == user.id,
        GitHubContribution.contribution_date == target_date,
    ).first()

    github_commits = github_contrib.commit_count if github_contrib else 0
    github_additions = github_contrib.total_additions if github_contrib else 0
    github_deletions = github_contrib.total_deletions if github_contrib else 0
    github_repos = github_contrib.repos_contributed if github_contrib else 0

    # Spotify metrics
    listening_sessions = db.query(ListeningSession).filter(
        ListeningSession.user_id == user.id,
        func.date(ListeningSession.played_at) == target_date,
    ).all()

    spotify_tracks_played = len(listening_sessions)
    
    # Calculate listening time in minutes
    spotify_listening_minutes = 0
    unique_artists = set()
    
    for session in listening_sessions:
        if session.track and session.track.duration_ms:
            spotify_listening_minutes += session.track.duration_ms // 60000
            for artist in session.track.artists:
                unique_artists.add(artist.id)

    spotify_unique_artists = len(unique_artists)

    # Calculate productivity score (weighted combination)
    # Weight: 30% GitHub commits, 20% code additions, 50% listening minutes
    github_score = github_commits * 0.3 + (github_additions / 100) * 0.2
    spotify_score = (spotify_listening_minutes / 60) * 0.5  # Hours listened
    productive_score = github_score + spotify_score

    return DailyAggregation(
        user_id=user.id,
        aggregation_date=target_date,
        github_commits=github_commits,
        github_additions=github_additions,
        github_deletions=github_deletions,
        github_repos_touched=github_repos,
        spotify_tracks_played=spotify_tracks_played,
        spotify_listening_minutes=spotify_listening_minutes,
        spotify_unique_artists=spotify_unique_artists,
        productive_score=productive_score,
    )
