"""
Spotify API routes.
Endpoints for querying Spotify listening data.
"""
from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from pipeline.database import get_db
from pipeline.models import (
    SpotifyTrack,
    SpotifyArtist,
    ListeningSession,
    User,
)
from api.schemas import (
    SpotifyTrackResponse,
    SpotifyArtistResponse,
    ListeningSessionResponse,
    SpotifyStatsResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/spotify", tags=["Spotify"])


@router.get("/stats", response_model=SpotifyStatsResponse)
def get_spotify_stats(
    days: int = Query(30, ge=1, le=730),
    db: Session = Depends(get_db),
):
    """
    Get overall Spotify statistics.
    
    Args:
        days: Number of days to look back (default: 30)
    
    Returns:
        Spotify statistics including listening time, artists, tracks, etc.
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        since_date = datetime.utcnow() - timedelta(days=days)

        # Get listening sessions
        sessions = db.query(ListeningSession).filter(
            ListeningSession.user_id == user.id,
            ListeningSession.played_at >= since_date,
        ).all()

        # Get tracks
        tracks = db.query(SpotifyTrack).filter(
            SpotifyTrack.user_id == user.id,
            SpotifyTrack.first_heard_at >= since_date,
        ).all()

        # Calculate statistics
        total_sessions = len(sessions)
        total_listening_minutes = 0
        unique_artists_set = set()
        
        for session in sessions:
            if session.track and session.track.duration_ms:
                total_listening_minutes += session.track.duration_ms // 60000

        unique_tracks = len(set(s.track_id for s in sessions if s.track_id))
        unique_artists_count = len(unique_artists_set)

        # Get top artists
        artists = db.query(SpotifyArtist).all()
        top_artists = sorted(
            artists,
            key=lambda x: x.popularity or 0,
            reverse=True
        )[:10]

        # Get top tracks
        top_tracks = sorted(tracks, key=lambda x: x.play_count, reverse=True)[:10]

        # Calculate average daily listening
        avg_daily_listening = (
            total_listening_minutes / days if days > 0 else 0
        )

        # Calculate listening streak
        listening_streak = 0
        if sessions:
            session_dates = set(
                datetime.fromisoformat(str(s.played_at)).date()
                for s in sessions
            )
            sorted_dates = sorted(session_dates, reverse=True)
            current_date = date.today()
            
            for session_date in sorted_dates:
                if (current_date - session_date).days == listening_streak:
                    listening_streak += 1
                else:
                    break

        return SpotifyStatsResponse(
            total_tracks_played=total_sessions,
            total_listening_minutes=total_listening_minutes,
            unique_artists=unique_artists_count,
            unique_tracks=unique_tracks,
            average_daily_listening=round(avg_daily_listening, 2),
            top_artists=[SpotifyArtistResponse.model_validate(a) for a in top_artists],
            top_tracks=[SpotifyTrackResponse.model_validate(t) for t in top_tracks],
            listening_streak=listening_streak,
        )

    except Exception as e:
        logger.error(f"Error getting Spotify stats: {str(e)}")
        raise


@router.get("/top-tracks", response_model=list[SpotifyTrackResponse])
def get_top_tracks(
    limit: int = Query(50, ge=1, le=100),
    days: int = Query(30, ge=1, le=730),
    db: Session = Depends(get_db),
):
    """
    Get top tracks by play count.
    
    Args:
        limit: Maximum number of tracks to return
        days: Number of days to look back
    
    Returns:
        List of top tracks
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        since_date = datetime.utcnow() - timedelta(days=days)

        tracks = db.query(SpotifyTrack).filter(
            SpotifyTrack.user_id == user.id,
            SpotifyTrack.first_heard_at >= since_date,
        ).order_by(SpotifyTrack.play_count.desc()).limit(limit).all()

        return [SpotifyTrackResponse.model_validate(t) for t in tracks]

    except Exception as e:
        logger.error(f"Error getting top tracks: {str(e)}")
        raise


@router.get("/top-artists", response_model=list[SpotifyArtistResponse])
def get_top_artists(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get top artists by popularity or listening count.
    
    Args:
        limit: Maximum number of artists to return
    
    Returns:
        List of top artists
    """
    try:
        artists = db.query(SpotifyArtist).order_by(
            SpotifyArtist.popularity.desc()
        ).limit(limit).all()

        return [SpotifyArtistResponse.model_validate(a) for a in artists]

    except Exception as e:
        logger.error(f"Error getting top artists: {str(e)}")
        raise


@router.get("/recently-played", response_model=PaginatedResponse)
def get_recently_played(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    days: int = Query(30, ge=1, le=730),
    db: Session = Depends(get_db),
):
    """
    Get recently played tracks.
    
    Args:
        skip: Number of items to skip
        limit: Number of items to return
        days: Number of days to look back
    
    Returns:
        Paginated list of listening sessions
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        since_date = datetime.utcnow() - timedelta(days=days)

        query = db.query(ListeningSession).filter(
            ListeningSession.user_id == user.id,
            ListeningSession.played_at >= since_date,
        ).order_by(ListeningSession.played_at.desc())

        total = query.count()
        sessions = query.offset(skip).limit(limit).all()

        return PaginatedResponse.create(
            items=[ListeningSessionResponse.model_validate(s) for s in sessions],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Error getting recently played: {str(e)}")
        raise


@router.get("/listening-history", response_model=list[ListeningSessionResponse])
def get_listening_history(
    days: int = Query(30, ge=1, le=730),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get listening history.
    
    Args:
        days: Number of days to look back
        limit: Maximum number of sessions to return
    
    Returns:
        List of listening sessions
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        since_date = datetime.utcnow() - timedelta(days=days)

        sessions = db.query(ListeningSession).filter(
            ListeningSession.user_id == user.id,
            ListeningSession.played_at >= since_date,
        ).order_by(ListeningSession.played_at.desc()).limit(limit).all()

        return [ListeningSessionResponse.model_validate(s) for s in sessions]

    except Exception as e:
        logger.error(f"Error getting listening history: {str(e)}")
        raise


@router.get("/listening-by-hour", response_model=dict)
def get_listening_by_hour(
    days: int = Query(30, ge=1, le=730),
    db: Session = Depends(get_db),
):
    """
    Get listening activity breakdown by hour of day.
    
    Args:
        days: Number of days to look back
    
    Returns:
        Dictionary with hour as key and listening count as value
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        since_date = datetime.utcnow() - timedelta(days=days)

        sessions = db.query(ListeningSession).filter(
            ListeningSession.user_id == user.id,
            ListeningSession.played_at >= since_date,
        ).all()

        # Group by hour
        hour_stats = {str(i): 0 for i in range(24)}
        
        for session in sessions:
            hour = session.played_at.hour
            hour_stats[str(hour)] += 1

        return hour_stats

    except Exception as e:
        logger.error(f"Error getting listening by hour: {str(e)}")
        raise
