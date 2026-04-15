"""
Shared API client for fetching data from the FastAPI backend.
"""
from typing import Any, Dict, Optional
import requests
from loguru import logger

from pipeline.config import get_settings

settings = get_settings()
API_BASE = f"http://localhost:{settings.api_port}"


def _get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
    """Make a GET request to the API."""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        logger.warning(f"API not reachable at {API_BASE}")
        return None
    except Exception as e:
        logger.warning(f"API request failed [{endpoint}]: {str(e)}")
        return None


def get_github_stats(days: int = 30) -> Optional[Dict]:
    return _get("/api/github/stats", {"days": days})


def get_github_contributions(days: int = 30) -> Optional[Dict]:
    return _get("/api/github/contributions", {"days": days, "limit": days})


def get_github_repositories() -> Optional[Dict]:
    return _get("/api/github/repositories", {"limit": 100, "sort_by": "stars"})


def get_github_languages(days: int = 365) -> Optional[Dict]:
    return _get("/api/github/languages", {"days": days})


def get_spotify_stats(days: int = 30) -> Optional[Dict]:
    return _get("/api/spotify/stats", {"days": days})


def get_top_tracks(days: int = 30, limit: int = 20) -> Optional[list]:
    return _get("/api/spotify/top-tracks", {"days": days, "limit": limit})


def get_top_artists(limit: int = 20) -> Optional[list]:
    return _get("/api/spotify/top-artists", {"limit": limit})


def get_listening_by_hour(days: int = 30) -> Optional[Dict]:
    return _get("/api/spotify/listening-by-hour", {"days": days})


def get_dashboard_overview(days: int = 30) -> Optional[Dict]:
    return _get("/api/dashboard/overview", {"days": days})


def get_daily_aggregations(days: int = 30) -> Optional[list]:
    return _get("/api/dashboard/aggregations", {"days": days})
