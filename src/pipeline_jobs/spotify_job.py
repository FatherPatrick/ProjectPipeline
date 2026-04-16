"""
Spotify data collection and storage job.
Fetches Spotify data and persists it to the database.
"""
from datetime import datetime
from sqlalchemy.orm import Session
from loguru import logger

from pipeline.database import SessionLocal
from pipeline.config import get_settings
from pipeline.models import User, SpotifyTrack, SpotifyArtist, ListeningSession
from collectors.spotify_client import SpotifyClient


def run_spotify_job():
    """
    Main Spotify data collection job.
    Fetches data from Spotify API and stores it in the database.
    """
    settings = get_settings()
    
    logger.info("=" * 60)
    logger.info("Spotify Data Collection Job Started")
    logger.info("=" * 60)

    if not settings.spotify_client_id or not settings.spotify_client_secret:
        logger.error("Spotify credentials not configured. Skipping job.")
        return

    db = SessionLocal()

    try:
        # Create or get user
        user = db.query(User).filter(User.spotify_username != None).first()
        if not user:
            user = User(
                username="spotify_user",  # Will be updated after auth
                spotify_access_token=None,
                spotify_refresh_token=None,
            )
            db.add(user)
            db.commit()
            logger.info("Created new Spotify user")
        else:
            logger.info(f"Using existing Spotify user: {user.spotify_username}")

        # Initialize Spotify client
        client = SpotifyClient(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            access_token=user.spotify_access_token or settings.spotify_access_token or None,
            refresh_token=user.spotify_refresh_token or settings.spotify_refresh_token or None,
            redirect_uri=settings.spotify_redirect_uri,
        )

        # Validate credentials
        logger.info("Validating Spotify credentials...")
        client.validate()

        # Get user profile
        logger.info("Fetching user profile...")
        profile = client.get_current_user()
        
        if profile:
            user.spotify_username = profile.get("id")
            user.spotify_access_token = client.access_token
            if client.refresh_token:
                user.spotify_refresh_token = client.refresh_token
            if client.token_expires_at:
                user.spotify_token_expires_at = client.token_expires_at
            db.commit()

        # Collect data
        logger.info("Collecting Spotify data...")
        data = client.collect()

        # Store artists
        logger.info(f"Storing {len(data['top_artists'])} artists...")
        _store_artists(db, data['top_artists'])

        # Store tracks and listening sessions
        logger.info(f"Storing {len(data['listening_history'])} listening sessions...")
        _store_listening_sessions(db, user, data['listening_history'])

        # Store top tracks
        logger.info(f"Storing {len(data['top_tracks'])} top tracks...")
        _store_top_tracks(db, user, data['top_tracks'])

        logger.info("✓ Spotify job completed successfully")

    except Exception as e:
        logger.error(f"Spotify job failed: {str(e)}")
        db.rollback()
        raise

    finally:
        db.close()


def _store_artists(db: Session, artists: list):
    """Store artists in the database."""
    for artist_data in artists:
        artist = db.query(SpotifyArtist).filter(
            SpotifyArtist.spotify_id == artist_data["id"]
        ).first()

        if not artist:
            artist = SpotifyArtist(
                spotify_id=artist_data["id"],
                name=artist_data["name"],
                genres=artist_data.get("genres", []),
                popularity=artist_data.get("popularity"),
                image_url=artist_data.get("image_url"),
                url=artist_data["url"],
            )
            db.add(artist)
        else:
            # Update existing artist
            artist.popularity = artist_data.get("popularity")
            artist.genres = artist_data.get("genres", [])

    db.commit()
    logger.debug("Artists stored")


def _store_listening_sessions(db: Session, user: User, sessions: list):
    """Store listening sessions and tracks."""
    for session_data in sessions:
        # Find or create track
        track = db.query(SpotifyTrack).filter(
            SpotifyTrack.user_id == user.id,
            SpotifyTrack.spotify_id == session_data["id"],
        ).first()

        if not track:
            try:
                played_at = datetime.fromisoformat(
                    session_data["played_at"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError, KeyError):
                logger.warning(f"Invalid played_at date: {session_data.get('played_at')}")
                played_at = datetime.utcnow()

            track = SpotifyTrack(
                user_id=user.id,
                spotify_id=session_data["id"],
                name=session_data["name"],
                album_name=session_data.get("album"),
                duration_ms=session_data.get("duration_ms", 0),
                popularity=session_data.get("popularity"),
                explicit=session_data.get("explicit", False),
                url=session_data["url"],
                image_url=session_data.get("image_url"),
                first_heard_at=played_at,
                last_heard_at=played_at,
                play_count=1,
                total_duration_ms=session_data.get("duration_ms", 0),
            )
            db.add(track)
            db.flush()  # Get the track ID

            # Add listening session
            listening_session = ListeningSession(
                user_id=user.id,
                track_id=track.id,
                played_at=played_at,
                progress_ms=session_data.get("progress_ms"),
            )
            db.add(listening_session)
        else:
            # Update existing track
            try:
                played_at = datetime.fromisoformat(
                    session_data["played_at"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError, KeyError):
                played_at = datetime.utcnow()

            track.play_count += 1
            track.last_heard_at = played_at
            track.total_duration_ms += session_data.get("duration_ms", 0)

            # Add listening session if not duplicate
            existing_session = db.query(ListeningSession).filter(
                ListeningSession.track_id == track.id,
                ListeningSession.played_at == played_at,
            ).first()

            if not existing_session:
                listening_session = ListeningSession(
                    user_id=user.id,
                    track_id=track.id,
                    played_at=played_at,
                    progress_ms=session_data.get("progress_ms"),
                )
                db.add(listening_session)

    db.commit()
    logger.debug("Listening sessions stored")


def _store_top_tracks(db: Session, user: User, tracks: list):
    """Store top tracks in the database."""
    for track_data in tracks:
        track = db.query(SpotifyTrack).filter(
            SpotifyTrack.user_id == user.id,
            SpotifyTrack.spotify_id == track_data["id"],
        ).first()

        if not track:
            track = SpotifyTrack(
                user_id=user.id,
                spotify_id=track_data["id"],
                name=track_data["name"],
                album_name=track_data.get("album"),
                duration_ms=track_data.get("duration_ms", 0),
                popularity=track_data.get("popularity"),
                explicit=track_data.get("explicit", False),
                url=track_data["url"],
                image_url=track_data.get("image_url"),
                first_heard_at=datetime.utcnow(),
                last_heard_at=datetime.utcnow(),
                play_count=0,
                total_duration_ms=0,
            )
            db.add(track)
        else:
            track.popularity = track_data.get("popularity")

    db.commit()
    logger.debug("Top tracks stored")
