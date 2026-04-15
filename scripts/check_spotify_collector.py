"""
Smoke-check script for the Spotify collector.
Run this to verify the Spotify client is working correctly.

Usage:
    poetry run python scripts/check_spotify_collector.py
"""
import sys
from pathlib import Path

# Add src directory to path for imports when running from source checkout
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.config import get_settings
from collectors.spotify_client import SpotifyClient
from loguru import logger


def main():
    """Smoke-check the Spotify collector."""
    settings = get_settings()

    print("=" * 60)
    print("Spotify Collector Test")
    print("=" * 60)

    # Check for required credentials
    if not settings.spotify_client_id:
        print("\n✗ Error: SPOTIFY_CLIENT_ID not set in .env file")
        print("  Get it from: https://developer.spotify.com/dashboard")
        sys.exit(1)

    if not settings.spotify_client_secret:
        print("\n✗ Error: SPOTIFY_CLIENT_SECRET not set in .env file")
        print("  Get it from: https://developer.spotify.com/dashboard")
        sys.exit(1)

    print(f"\nSpotify Client ID: ***{settings.spotify_client_id[-10:]}")
    print(f"Spotify Client Secret: ***{settings.spotify_client_secret[-10:]}")
    print()

    try:
        # Create client
        client = SpotifyClient(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            redirect_uri=settings.spotify_redirect_uri,
        )

        # Validate credentials
        print("Validating credentials...")
        client.validate()

        # Get user profile
        print("\nFetching user profile...")
        user = client.get_current_user()
        print(f"✓ Logged in as: {user.get('display_name', 'Unknown')}")

        # Collect data
        print("\nCollecting Spotify data...")
        data = client.collect()

        # Print results
        print("\n" + "=" * 60)
        print("Spotify Data Collection Results")
        print("=" * 60)

        print(f"\n✓ Recently Played: {len(data['listening_history'])} tracks")
        if data['listening_history']:
            print("  Latest 3 tracks played:")
            for track in data['listening_history'][:3]:
                artists = ", ".join(track['artists'])
                print(f"    - {track['name']} by {artists}")

        print(f"\n✓ Top Tracks: {len(data['top_tracks'])} tracks")
        if data['top_tracks']:
            print("  Top 3 tracks:")
            for track in data['top_tracks'][:3]:
                artists = ", ".join(track['artists'])
                popularity = track.get('popularity', 0)
                print(f"    - {track['name']} by {artists} (popularity: {popularity})")

        print(f"\n✓ Top Artists: {len(data['top_artists'])} artists")
        if data['top_artists']:
            print("  Top 3 artists:")
            for artist in data['top_artists'][:3]:
                genres = ", ".join(artist['genres'][:2]) if artist['genres'] else "Unknown"
                popularity = artist.get('popularity', 0)
                print(f"    - {artist['name']} ({genres}, popularity: {popularity})")

        print("\n" + "=" * 60)
        print("✓ Spotify collector test successful!")
        print("=" * 60)
        client.close()

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Check that your Spotify Client ID and Secret are correct")
        print("  2. Visit https://developer.spotify.com/dashboard to create an app")
        print("  3. Make sure you're using Client Credentials flow or Authorization Code flow")
        sys.exit(1)


if __name__ == "__main__":
    main()
