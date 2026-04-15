"""
Pydantic response models for type-safe API responses.
These models validate and serialize data from the database.
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


# ============================================================================
# GitHub Models
# ============================================================================

class GitHubRepositoryResponse(BaseModel):
    """GitHub repository response model."""
    id: int
    repo_id: int
    repo_name: str
    full_name: str
    description: Optional[str]
    language: Optional[str]
    stars: int
    forks: int
    is_fork: bool
    is_private: bool
    url: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GitHubCommitResponse(BaseModel):
    """GitHub commit response model."""
    id: int
    commit_sha: str
    message: str
    author_name: str
    author_email: str
    commit_date: datetime
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0
    url: str
    repository_id: int

    model_config = ConfigDict(from_attributes=True)


class GitHubContributionResponse(BaseModel):
    """GitHub daily contribution response model."""
    id: int
    contribution_date: date
    commit_count: int
    total_additions: int
    total_deletions: int
    repos_contributed: int
    languages: Dict[str, int]

    model_config = ConfigDict(from_attributes=True)


class GitHubStatsResponse(BaseModel):
    """Overall GitHub statistics response."""
    total_repositories: int
    total_commits: int
    total_additions: int
    total_deletions: int
    average_commits_per_day: float
    most_used_language: Optional[str]
    language_breakdown: Dict[str, int]
    contribution_days: int
    consecutive_days: int
    top_repositories: List[GitHubRepositoryResponse]


# ============================================================================
# Spotify Models
# ============================================================================

class SpotifyArtistResponse(BaseModel):
    """Spotify artist response model."""
    id: int
    spotify_id: str
    name: str
    genres: List[str]
    popularity: Optional[int]
    url: str
    image_url: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SpotifyTrackResponse(BaseModel):
    """Spotify track response model."""
    id: int
    spotify_id: str
    name: str
    album_name: Optional[str]
    duration_ms: int
    popularity: Optional[int]
    explicit: bool
    url: str
    image_url: Optional[str]
    play_count: int
    first_heard_at: datetime
    last_heard_at: datetime
    total_duration_ms: int

    model_config = ConfigDict(from_attributes=True)


class ListeningSessionResponse(BaseModel):
    """Spotify listening session response model."""
    id: int
    track_id: int
    played_at: datetime
    progress_ms: Optional[int]
    track: Optional[SpotifyTrackResponse] = None

    model_config = ConfigDict(from_attributes=True)


class SpotifyStatsResponse(BaseModel):
    """Overall Spotify statistics response."""
    total_tracks_played: int
    total_listening_minutes: int
    unique_artists: int
    unique_tracks: int
    average_daily_listening: float
    top_artists: List[SpotifyArtistResponse]
    top_tracks: List[SpotifyTrackResponse]
    listening_streak: int


# ============================================================================
# Aggregation Models
# ============================================================================

class DailyAggregationResponse(BaseModel):
    """Daily aggregation response model."""
    id: int
    aggregation_date: date
    github_commits: int
    github_additions: int
    github_deletions: int
    github_repos_touched: int
    spotify_tracks_played: int
    spotify_listening_minutes: int
    spotify_unique_artists: int
    productive_score: float

    model_config = ConfigDict(from_attributes=True)


class DashboardOverviewResponse(BaseModel):
    """Dashboard overview response combining all metrics."""
    date_range: Dict[str, str]  # {"start": "2024-01-01", "end": "2024-04-15"}
    
    # GitHub summary
    github_stats: GitHubStatsResponse
    github_recent_contributions: List[GitHubContributionResponse]
    
    # Spotify summary
    spotify_stats: SpotifyStatsResponse
    spotify_recent_sessions: List[ListeningSessionResponse]
    
    # Combined metrics
    daily_aggregations: List[DailyAggregationResponse]
    top_productive_days: List[DailyAggregationResponse]
    
    # Trends
    avg_daily_commits: float
    avg_daily_listening_minutes: float
    productivity_trend: str  # "up", "down", "stable"


# ============================================================================
# Pagination Models
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination parameters."""
    skip: int = 0
    limit: int = 50
    
    def validate(self):
        """Validate pagination parameters."""
        self.skip = max(0, self.skip)
        self.limit = max(1, min(self.limit, 1000))  # Cap at 1000
        return self


class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    total: int
    skip: int
    limit: int
    items: List[Any]
    has_more: bool

    @classmethod
    def create(cls, items: List[Any], total: int, skip: int, limit: int):
        """Create a paginated response."""
        return cls(
            total=total,
            skip=skip,
            limit=limit,
            items=items,
            has_more=(skip + limit) < total,
        )


# ============================================================================
# Error Models
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str
    status_code: int


# ============================================================================
# Health Check Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str = "0.1.0"
    environment: str
