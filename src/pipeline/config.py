"""
Configuration management for the application.
Loads environment variables from .env file and provides typed settings.
"""
from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/personal_data_dashboard"
    database_pool_size: int = 20
    database_max_overflow: int = 40

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    # GitHub API
    github_token: str = ""
    github_username: str = ""

    # Spotify API
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://localhost:8000/auth/spotify/callback"

    # Steam API (Optional)
    steam_api_key: str = ""

    # Scheduler
    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"
    data_refresh_interval_hours: int = 168  # Weekly

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # Railway injects PORT env var — takes precedence over api_port
    port: Optional[int] = None

    @property
    def effective_port(self) -> int:
        """Return Railway PORT if set, otherwise api_port."""
        return self.port or self.api_port

    # Dashboard
    dashboard_port: int = 8050
    dashboard_host: str = "0.0.0.0"

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # Data Collection
    github_backfill_days: int = 730  # 2 years
    spotify_backfill_days: int = 730  # 2 years

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
