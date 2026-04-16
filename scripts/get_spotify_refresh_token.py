"""
Generate a Spotify refresh token for local development.

Usage:
    poetry run python scripts/get_spotify_refresh_token.py
"""
import base64
import secrets
import sys
import urllib.parse
from pathlib import Path

import requests

# Add src directory to path for imports when running from source checkout
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.config import get_settings


AUTH_BASE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
SCOPES = "user-read-private user-read-email user-read-recently-played user-top-read"


def _build_authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
        "show_dialog": "true",
    }
    return f"{AUTH_BASE_URL}?{urllib.parse.urlencode(params)}"


def _extract_code_from_url(url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(url.strip())
    query = urllib.parse.parse_qs(parsed.query)
    code = query.get("code", [""])[0]
    state = query.get("state", [""])[0]
    if not code:
        raise ValueError("No authorization code found in URL")
    return code, state


def _exchange_code_for_tokens(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    response = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> int:
    settings = get_settings()

    if not settings.spotify_client_id or not settings.spotify_client_secret:
        print("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env first.")
        return 1

    state = secrets.token_urlsafe(16)
    authorize_url = _build_authorize_url(
        client_id=settings.spotify_client_id,
        redirect_uri=settings.spotify_redirect_uri,
        state=state,
    )

    print("=" * 60)
    print("Spotify Refresh Token Setup")
    print("=" * 60)
    print("1) In Spotify Dashboard, add this exact Redirect URI:")
    print(f"   {settings.spotify_redirect_uri}")
    print("2) Open this URL in your browser and approve access:")
    print(authorize_url)
    print("3) After redirect, copy the full URL from your browser and paste it below.")

    redirected_url = input("\nPaste redirected URL: ").strip()

    try:
        code, returned_state = _extract_code_from_url(redirected_url)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    if returned_state != state:
        print("Error: state mismatch. Retry to prevent using a stale authorization response.")
        return 1

    try:
        token_data = _exchange_code_for_tokens(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            code=code,
            redirect_uri=settings.spotify_redirect_uri,
        )
    except Exception as exc:
        print(f"Token exchange failed: {exc}")
        return 1

    refresh_token = token_data.get("refresh_token")
    access_token = token_data.get("access_token")

    print("\nSuccess.")
    print("Add this to your .env:")
    if refresh_token:
        print(f"SPOTIFY_REFRESH_TOKEN={refresh_token}")
    else:
        print("SPOTIFY_REFRESH_TOKEN=<missing; ensure you approved with show_dialog=true>")

    if access_token:
        print(f"SPOTIFY_ACCESS_TOKEN={access_token}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())