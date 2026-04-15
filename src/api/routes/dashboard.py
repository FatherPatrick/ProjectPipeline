"""
Dashboard API routes.
Endpoints for combined dashboard data.
"""
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from pipeline.database import get_db
from pipeline.models import (
    User,
    GitHubRepository,
    GitHubCommit,
    GitHubContribution,
    SpotifyTrack,
    SpotifyArtist,
    ListeningSession,
    DailyAggregation,
)
from api.schemas import (
    GitHubStatsResponse,
    SpotifyStatsResponse,
    DailyAggregationResponse,
    DashboardOverviewResponse,
    GitHubContributionResponse,
    GitHubRepositoryResponse,
    ListeningSessionResponse,
    SpotifyTrackResponse,
    SpotifyArtistResponse,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    days: int = Query(30, ge=1, le=730),
    db: Session = Depends(get_db),
):
    """
    Get complete dashboard overview combining all metrics.
    
    Args:
        days: Number of days to look back
    
    Returns:
        Combined dashboard data
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        since_datetime = datetime.utcnow() - timedelta(days=days)
        since_date = since_datetime.date()
        end_date = date.today()

        # ===== GitHub Data =====
        repos = db.query(GitHubRepository).filter(
            GitHubRepository.user_id == user.id
        ).all()

        commits = db.query(GitHubCommit).filter(
            GitHubCommit.user_id == user.id,
            GitHubCommit.commit_date >= since_datetime,
        ).all()

        contributions = db.query(GitHubContribution).filter(
            GitHubContribution.user_id == user.id,
            GitHubContribution.contribution_date >= since_date,
        ).all()

        # ===== Spotify Data =====
        sessions = db.query(ListeningSession).filter(
            ListeningSession.user_id == user.id,
            ListeningSession.played_at >= since_datetime,
        ).all()

        tracks = db.query(SpotifyTrack).filter(
            SpotifyTrack.user_id == user.id,
            SpotifyTrack.first_heard_at >= since_datetime,
        ).all()

        artists = db.query(SpotifyArtist).all()

        # ===== Aggregations =====
        aggregations = db.query(DailyAggregation).filter(
            DailyAggregation.user_id == user.id,
            DailyAggregation.aggregation_date >= since_date,
        ).order_by(DailyAggregation.aggregation_date.desc()).all()

        # ===== Build GitHub Stats =====
        total_additions = sum(c.additions for c in commits)
        total_deletions = sum(c.deletions for c in commits)
        
        language_breakdown = {}
        for repo in repos:
            if repo.language:
                language_breakdown[repo.language] = language_breakdown.get(repo.language, 0) + 1

        most_used_language = max(
            language_breakdown,
            key=language_breakdown.get
        ) if language_breakdown else None

        top_repos = sorted(repos, key=lambda x: x.stars, reverse=True)[:5]

        github_stats = GitHubStatsResponse(
            total_repositories=len(repos),
            total_commits=len(commits),
            total_additions=total_additions,
            total_deletions=total_deletions,
            average_commits_per_day=round(len(commits) / days, 2) if days > 0 else 0,
            most_used_language=most_used_language,
            language_breakdown=language_breakdown,
            contribution_days=len(contributions),
            consecutive_days=_calculate_consecutive_days(contributions),
            top_repositories=[GitHubRepositoryResponse.model_validate(r) for r in top_repos],
        )

        # ===== Build Spotify Stats =====
        total_listening_minutes = 0
        unique_artists_set = set()
        
        for session in sessions:
            if session.track and session.track.duration_ms:
                total_listening_minutes += session.track.duration_ms // 60000

        unique_tracks = len(set(s.track_id for s in sessions if s.track_id))

        top_artists_sorted = sorted(
            artists,
            key=lambda x: x.popularity or 0,
            reverse=True
        )[:10]

        top_tracks_sorted = sorted(tracks, key=lambda x: x.play_count, reverse=True)[:10]

        spotify_stats = SpotifyStatsResponse(
            total_tracks_played=len(sessions),
            total_listening_minutes=total_listening_minutes,
            unique_artists=len(unique_artists_set),
            unique_tracks=unique_tracks,
            average_daily_listening=round(total_listening_minutes / days, 2) if days > 0 else 0,
            top_artists=[SpotifyArtistResponse.model_validate(a) for a in top_artists_sorted],
            top_tracks=[SpotifyTrackResponse.model_validate(t) for t in top_tracks_sorted],
            listening_streak=_calculate_listening_streak(sessions),
        )

        # ===== Find Top Productive Days =====
        top_productive_days = sorted(
            aggregations,
            key=lambda x: x.productive_score,
            reverse=True
        )[:7]

        # ===== Calculate Trends =====
        avg_daily_commits = round(len(commits) / days, 2) if days > 0 else 0
        avg_daily_listening_minutes = round(total_listening_minutes / days, 2) if days > 0 else 0

        # Simple trend detection
        if len(aggregations) >= 7:
            recent_week = aggregations[:7]
            previous_week = aggregations[7:14]
            
            recent_score = sum(a.productive_score for a in recent_week) / 7
            previous_score = sum(a.productive_score for a in previous_week) / 7 if len(previous_week) >= 7 else recent_score
            
            if recent_score > previous_score * 1.1:
                productivity_trend = "up"
            elif recent_score < previous_score * 0.9:
                productivity_trend = "down"
            else:
                productivity_trend = "stable"
        else:
            productivity_trend = "stable"

        return DashboardOverviewResponse(
            date_range={
                "start": since_date.isoformat(),
                "end": end_date.isoformat(),
            },
            github_stats=github_stats,
            github_recent_contributions=[
                GitHubContributionResponse.model_validate(c) 
                for c in sorted(contributions, key=lambda x: x.contribution_date, reverse=True)[:7]
            ],
            spotify_stats=spotify_stats,
            spotify_recent_sessions=[
                ListeningSessionResponse.model_validate(s)
                for s in sorted(sessions, key=lambda x: x.played_at, reverse=True)[:10]
            ],
            daily_aggregations=[
                DailyAggregationResponse.model_validate(a) for a in aggregations[:30]
            ],
            top_productive_days=[
                DailyAggregationResponse.model_validate(a) for a in top_productive_days
            ],
            avg_daily_commits=avg_daily_commits,
            avg_daily_listening_minutes=avg_daily_listening_minutes,
            productivity_trend=productivity_trend,
        )

    except Exception as e:
        logger.error(f"Error getting dashboard overview: {str(e)}")
        raise


@router.get("/aggregations", response_model=list[DailyAggregationResponse])
def get_aggregations(
    days: int = Query(30, ge=1, le=730),
    db: Session = Depends(get_db),
):
    """
    Get daily aggregations.
    
    Args:
        days: Number of days to look back
    
    Returns:
        List of daily aggregations
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        since_date = date.today() - timedelta(days=days)

        aggregations = db.query(DailyAggregation).filter(
            DailyAggregation.user_id == user.id,
            DailyAggregation.aggregation_date >= since_date,
        ).order_by(DailyAggregation.aggregation_date.desc()).all()

        return [DailyAggregationResponse.model_validate(a) for a in aggregations]

    except Exception as e:
        logger.error(f"Error getting aggregations: {str(e)}")
        raise


def _calculate_consecutive_days(contributions) -> int:
    """Calculate consecutive days of contributions."""
    if not contributions:
        return 0
    
    consecutive_days = 0
    sorted_contribs = sorted(contributions, key=lambda x: x.contribution_date, reverse=True)
    current_date = date.today()
    
    for contrib in sorted_contribs:
        if (current_date - contrib.contribution_date).days == consecutive_days:
            consecutive_days += 1
        else:
            break
    
    return consecutive_days


def _calculate_listening_streak(sessions) -> int:
    """Calculate consecutive days of listening."""
    if not sessions:
        return 0
    
    listening_streak = 0
    session_dates = set(
        session.played_at.date() for session in sessions
    )
    sorted_dates = sorted(session_dates, reverse=True)
    current_date = date.today()
    
    for session_date in sorted_dates:
        if (current_date - session_date).days == listening_streak:
            listening_streak += 1
        else:
            break
    
    return listening_streak
