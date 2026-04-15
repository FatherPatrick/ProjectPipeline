"""
SQLAlchemy ORM models for the Personal Data Analytics Dashboard.
Defines the database schema for GitHub, Spotify, and aggregated data.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, ForeignKey,
    Boolean, JSON, Index, UniqueConstraint, Date, BigInteger
)
from sqlalchemy.orm import relationship

from pipeline.database import Base


class User(Base):
    """User profile and metadata."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    github_username = Column(String(255), nullable=True)
    spotify_username = Column(String(255), nullable=True)
    steam_id = Column(String(255), nullable=True)
    
    # OAuth tokens (encrypted in production)
    github_token = Column(Text, nullable=True)
    spotify_access_token = Column(Text, nullable=True)
    spotify_refresh_token = Column(Text, nullable=True)
    spotify_token_expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    github_repos = relationship("GitHubRepository", back_populates="user", cascade="all, delete-orphan")
    github_commits = relationship("GitHubCommit", back_populates="user", cascade="all, delete-orphan")
    github_contributions = relationship("GitHubContribution", back_populates="user", cascade="all, delete-orphan")
    spotify_tracks = relationship("SpotifyTrack", back_populates="user", cascade="all, delete-orphan")
    listening_sessions = relationship("ListeningSession", back_populates="user", cascade="all, delete-orphan")
    daily_aggregations = relationship("DailyAggregation", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


# ============================================================================
# GitHub Models
# ============================================================================

class GitHubRepository(Base):
    """GitHub repository metadata."""
    __tablename__ = "github_repositories"
    __table_args__ = (
        UniqueConstraint("user_id", "repo_name", name="uq_user_repo"),
        Index("ix_repo_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    repo_id = Column(Integer, unique=True, nullable=False)
    repo_name = Column(String(255), nullable=False)
    full_name = Column(String(511), nullable=False)  # owner/repo
    description = Column(Text, nullable=True)
    language = Column(String(255), nullable=True)
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    is_fork = Column(Boolean, default=False)
    is_private = Column(Boolean, default=False)
    url = Column(String(511), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="github_repos")
    commits = relationship("GitHubCommit", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GitHubRepository(id={self.id}, repo_name={self.repo_name})>"


class GitHubCommit(Base):
    """Individual GitHub commits."""
    __tablename__ = "github_commits"
    __table_args__ = (
        UniqueConstraint("user_id", "commit_sha", name="uq_user_commit"),
        Index("ix_commit_user_date", "user_id", "commit_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    repository_id = Column(Integer, ForeignKey("github_repositories.id"), nullable=False)
    commit_sha = Column(String(40), unique=True, nullable=False)
    message = Column(Text, nullable=False)
    author_name = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    commit_date = Column(DateTime, nullable=False, index=True)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    files_changed = Column(Integer, default=0)
    url = Column(String(511), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="github_commits")
    repository = relationship("GitHubRepository", back_populates="commits")

    def __repr__(self):
        return f"<GitHubCommit(sha={self.commit_sha})>"


class GitHubContribution(Base):
    """Daily GitHub contribution aggregates."""
    __tablename__ = "github_contributions"
    __table_args__ = (
        UniqueConstraint("user_id", "contribution_date", name="uq_user_date"),
        Index("ix_contribution_user_date", "user_id", "contribution_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contribution_date = Column(Date, nullable=False)
    commit_count = Column(Integer, default=0)
    total_additions = Column(Integer, default=0)
    total_deletions = Column(Integer, default=0)
    repos_contributed = Column(Integer, default=0)
    languages = Column(JSON, default={})  # {language: commit_count}
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="github_contributions")

    def __repr__(self):
        return f"<GitHubContribution(user_id={self.user_id}, date={self.contribution_date})>"


# ============================================================================
# Spotify Models
# ============================================================================

class SpotifyArtist(Base):
    """Spotify artist information."""
    __tablename__ = "spotify_artists"
    __table_args__ = (
        Index("ix_artist_spotify_id", "spotify_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    spotify_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    popularity = Column(Integer, nullable=True)
    genres = Column(JSON, default=[])
    image_url = Column(String(511), nullable=True)
    url = Column(String(511), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tracks = relationship("SpotifyTrack", back_populates="artists", secondary="spotify_track_artists")

    def __repr__(self):
        return f"<SpotifyArtist(name={self.name})>"


class SpotifyTrack(Base):
    """Spotify track metadata and listening stats."""
    __tablename__ = "spotify_tracks"
    __table_args__ = (
        UniqueConstraint("user_id", "spotify_id", name="uq_user_track"),
        Index("ix_track_user_date", "user_id", "first_heard_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    spotify_id = Column(String(255), nullable=False)
    name = Column(String(511), nullable=False)
    album_name = Column(String(511), nullable=True)
    duration_ms = Column(Integer, nullable=False)
    popularity = Column(Integer, nullable=True)
    explicit = Column(Boolean, default=False)
    url = Column(String(511), nullable=False)
    image_url = Column(String(511), nullable=True)
    
    # Listening stats
    play_count = Column(Integer, default=1)
    first_heard_at = Column(DateTime, nullable=False, index=True)
    last_heard_at = Column(DateTime, nullable=False)
    total_duration_ms = Column(BigInteger, default=0)  # Total time spent listening
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="spotify_tracks")
    listening_sessions = relationship("ListeningSession", back_populates="track", cascade="all, delete-orphan")
    artists = relationship("SpotifyArtist", back_populates="tracks", secondary="spotify_track_artists")

    def __repr__(self):
        return f"<SpotifyTrack(name={self.name}, play_count={self.play_count})>"


class ListeningSession(Base):
    """Individual Spotify listening sessions."""
    __tablename__ = "listening_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", "track_id", "played_at", name="uq_listening_session"),
        Index("ix_session_user_date", "user_id", "played_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("spotify_tracks.id"), nullable=False)
    played_at = Column(DateTime, nullable=False, index=True)
    progress_ms = Column(Integer, nullable=True)
    is_playing = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="listening_sessions")
    track = relationship("SpotifyTrack", back_populates="listening_sessions")

    def __repr__(self):
        return f"<ListeningSession(user_id={self.user_id}, played_at={self.played_at})>"


# ============================================================================
# Association Table for Many-to-Many relationships
# ============================================================================

from sqlalchemy import Table

spotify_track_artists = Table(
    "spotify_track_artists",
    Base.metadata,
    Column("track_id", Integer, ForeignKey("spotify_tracks.id"), primary_key=True),
    Column("artist_id", Integer, ForeignKey("spotify_artists.id"), primary_key=True),
)


# ============================================================================
# Aggregation Models
# ============================================================================

class DailyAggregation(Base):
    """Daily aggregated metrics from all data sources."""
    __tablename__ = "daily_aggregations"
    __table_args__ = (
        UniqueConstraint("user_id", "aggregation_date", name="uq_user_date_agg"),
        Index("ix_agg_user_date", "user_id", "aggregation_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    aggregation_date = Column(Date, nullable=False)
    
    # GitHub metrics
    github_commits = Column(Integer, default=0)
    github_additions = Column(Integer, default=0)
    github_deletions = Column(Integer, default=0)
    github_repos_touched = Column(Integer, default=0)
    
    # Spotify metrics
    spotify_tracks_played = Column(Integer, default=0)
    spotify_listening_minutes = Column(Integer, default=0)
    spotify_unique_artists = Column(Integer, default=0)
    
    # Combined metrics
    productive_score = Column(Float, default=0.0)  # Custom metric combining both
    
    extra_data = Column(JSON, default={})  # Additional data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="daily_aggregations")

    def __repr__(self):
        return f"<DailyAggregation(user_id={self.user_id}, date={self.aggregation_date})>"
