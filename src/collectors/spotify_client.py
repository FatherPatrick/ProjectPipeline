"""
Spotify API client for collecting listening history and track data.
Uses Spotify Web API with OAuth2 authentication.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger
import requests
from collections import defaultdict

from collectors._base import BaseCollector, AuthenticationError, DataValidationError


class SpotifyClient(BaseCollector):
    """
    Spotify API client for collecting listening data.
    
    Collects:
    - Listening history
    - Top tracks and artists
    - Track metadata
    - Listening statistics
    """

    BASE_URL = "https://api.spotify.com/v1"
    AUTH_URL = "https://accounts.spotify.com/api/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        redirect_uri: str = "http://localhost:8000/auth/spotify/callback",
    ):
        """
        Initialize Spotify client.

        Args:
            client_id: Spotify application client ID
            client_secret: Spotify application client secret
            access_token: Optional existing access token
            refresh_token: Optional existing refresh token
            redirect_uri: OAuth redirect URI
        """
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.redirect_uri = redirect_uri
        self.token_expires_at = None

    def validate(self) -> bool:
        """
        Validate Spotify credentials.

        Returns:
            True if credentials are valid

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.client_id or not self.client_secret:
            raise AuthenticationError("Spotify client ID and secret are required")

        try:
            logger.info("Validating Spotify credentials...")
            
            # If we don't have an access token, get one
            if not self.access_token:
                self._authenticate()

            # Test API access
            response = self._request_with_retry(
                method="GET",
                url=f"{self.BASE_URL}/me",
                headers=self._get_headers(),
            )
            user_data = response.json()
            logger.info(f"✓ Spotify authentication successful for user: {user_data.get('display_name')}")
            return True

        except Exception as e:
            logger.error(f"Spotify authentication failed: {str(e)}")
            raise AuthenticationError(f"Failed to authenticate with Spotify: {str(e)}")

    def collect(self) -> Dict[str, Any]:
        """
        Collect all Spotify data.

        Returns:
            Dictionary with tracks, artists, and listening stats
        """
        logger.info("Starting Spotify data collection...")

        try:
            # Ensure we have a valid access token
            if not self.access_token:
                self._authenticate()

            # Refresh token if expired
            if self.token_expires_at and datetime.utcnow() >= self.token_expires_at:
                self._refresh_token()

            listening_history = self._get_recently_played()
            logger.info(f"Fetched {len(listening_history)} recent tracks")

            top_tracks = self._get_top_tracks()
            logger.info(f"Fetched {len(top_tracks)} top tracks")

            top_artists = self._get_top_artists()
            logger.info(f"Fetched {len(top_artists)} top artists")

            return {
                "listening_history": listening_history,
                "top_tracks": top_tracks,
                "top_artists": top_artists,
                "collected_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Spotify data collection failed: {str(e)}")
            raise

    def _authenticate(self):
        """
        Authenticate with Spotify using Client Credentials flow.
        For production, this should use Authorization Code flow for user data.
        """
        logger.debug("Authenticating with Spotify...")

        try:
            response = requests.post(
                self.AUTH_URL,
                auth=(self.client_id, self.client_secret),
                data={
                    "grant_type": "client_credentials",
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

            logger.debug("✓ Spotify authentication successful")

        except Exception as e:
            raise AuthenticationError(f"Spotify authentication failed: {str(e)}")

    def _refresh_token(self):
        """
        Refresh the access token using refresh token (if available).
        """
        if not self.refresh_token:
            logger.warning("No refresh token available, re-authenticating...")
            self._authenticate()
            return

        logger.debug("Refreshing Spotify access token...")

        try:
            response = requests.post(
                self.AUTH_URL,
                auth=(self.client_id, self.client_secret),
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])

            if "refresh_token" in data:
                self.refresh_token = data["refresh_token"]

            logger.debug("✓ Token refreshed successfully")

        except Exception as e:
            logger.warning(f"Token refresh failed, re-authenticating: {str(e)}")
            self._authenticate()

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _get_recently_played(
        self, limit: int = 50, days: int = 730
    ) -> List[Dict[str, Any]]:
        """
        Get recently played tracks.

        Args:
            limit: Number of tracks per request
            days: Number of days to look back

        Returns:
            List of track dictionaries with play info
        """
        logger.debug("Fetching recently played tracks...")
        tracks = []
        before_timestamp = int(datetime.utcnow().timestamp() * 1000)

        try:
            while len(tracks) < 500 and len(tracks) < limit * 10:  # Reasonable limit
                response = self._request_with_retry(
                    method="GET",
                    url=f"{self.BASE_URL}/me/player/recently_played",
                    headers=self._get_headers(),
                    params={
                        "limit": limit,
                        "before": before_timestamp,
                    },
                )

                data = response.json()
                items = data.get("items", [])

                if not items:
                    break

                for item in items:
                    try:
                        track = item["track"]
                        tracks.append({
                            "id": track["id"],
                            "name": track["name"],
                            "artists": [artist["name"] for artist in track["artists"]],
                            "album": track["album"]["name"],
                            "duration_ms": track["duration_ms"],
                            "popularity": track["popularity"],
                            "explicit": track["explicit"],
                            "url": track["external_urls"].get("spotify"),
                            "image_url": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
                            "played_at": item["played_at"],
                        })
                    except (KeyError, IndexError) as e:
                        logger.warning(f"Error processing track data: {e}")
                        continue

                # Check if we've gone back far enough
                oldest_time = datetime.fromisoformat(items[-1]["played_at"].replace("Z", "+00:00"))
                if (datetime.utcnow().astimezone() - oldest_time).days > days:
                    break

                before_timestamp = int(datetime.fromisoformat(
                    items[-1]["played_at"].replace("Z", "+00:00")
                ).timestamp() * 1000)

        except Exception as e:
            logger.error(f"Error fetching recently played tracks: {str(e)}")

        return tracks

    def _get_top_tracks(
        self, time_range: str = "medium_term", limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get user's top tracks.

        Args:
            time_range: 'short_term', 'medium_term', or 'long_term'
            limit: Number of tracks to fetch

        Returns:
            List of top tracks
        """
        logger.debug(f"Fetching top tracks ({time_range})...")
        tracks = []

        try:
            response = self._request_with_retry(
                method="GET",
                url=f"{self.BASE_URL}/me/top/tracks",
                headers=self._get_headers(),
                params={
                    "time_range": time_range,
                    "limit": limit,
                },
            )

            data = response.json()

            for item in data.get("items", []):
                try:
                    tracks.append({
                        "id": item["id"],
                        "name": item["name"],
                        "artists": [artist["name"] for artist in item["artists"]],
                        "album": item["album"]["name"],
                        "duration_ms": item["duration_ms"],
                        "popularity": item["popularity"],
                        "explicit": item["explicit"],
                        "url": item["external_urls"].get("spotify"),
                        "image_url": item["album"]["images"][0]["url"] if item["album"]["images"] else None,
                    })
                except (KeyError, IndexError) as e:
                    logger.warning(f"Error processing top track: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching top tracks: {str(e)}")

        return tracks

    def _get_top_artists(
        self, time_range: str = "medium_term", limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get user's top artists.

        Args:
            time_range: 'short_term', 'medium_term', or 'long_term'
            limit: Number of artists to fetch

        Returns:
            List of top artists
        """
        logger.debug(f"Fetching top artists ({time_range})...")
        artists = []

        try:
            response = self._request_with_retry(
                method="GET",
                url=f"{self.BASE_URL}/me/top/artists",
                headers=self._get_headers(),
                params={
                    "time_range": time_range,
                    "limit": limit,
                },
            )

            data = response.json()

            for item in data.get("items", []):
                try:
                    artists.append({
                        "id": item["id"],
                        "name": item["name"],
                        "genres": item.get("genres", []),
                        "popularity": item["popularity"],
                        "url": item["external_urls"].get("spotify"),
                        "image_url": item["images"][0]["url"] if item["images"] else None,
                    })
                except (KeyError, IndexError) as e:
                    logger.warning(f"Error processing top artist: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching top artists: {str(e)}")

        return artists

    def get_current_user(self) -> Dict[str, Any]:
        """
        Get current user profile information.

        Returns:
            User profile dictionary
        """
        try:
            response = self._request_with_retry(
                method="GET",
                url=f"{self.BASE_URL}/me",
                headers=self._get_headers(),
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            return {}
