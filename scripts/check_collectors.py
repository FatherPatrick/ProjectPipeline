"""
Combined smoke-check script for all collectors.
Validates that GitHub and Spotify clients are working correctly.

Usage:
    poetry run python scripts/check_collectors.py
"""
import sys
from pathlib import Path

# Add src directory to path for imports when running from source checkout
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.config import get_settings
from collectors.github_client import GitHubClient
from collectors.spotify_client import SpotifyClient
from loguru import logger


def test_github(settings) -> bool:
    """Smoke-check the GitHub collector."""
    print("\n" + "=" * 60)
    print("Testing GitHub Collector")
    print("=" * 60)

    if not settings.github_token or not settings.github_username:
        print("⚠ SKIPPED: GitHub credentials not configured")
        print("  Add GITHUB_TOKEN and GITHUB_USERNAME to .env")
        return None

    try:
        client = GitHubClient(
            github_token=settings.github_token,
            github_username=settings.github_username,
        )

        print(f"Username: {settings.github_username}")
        print("Validating...", end=" ", flush=True)
        client.validate()
        print("✓")

        print("Collecting data...", end=" ", flush=True)
        data = client.collect()
        print("✓")

        print(f"\nResults:")
        print(f"  • Repositories: {len(data['repositories'])}")
        print(f"  • Commits: {len(data['commits'])}")
        print(f"  • Contribution Days: {len(data['contributions'])}")

        client.close()
        return True

    except Exception as e:
        print(f"\n✗ Failed: {str(e)}")
        return False


def test_spotify(settings) -> bool:
    """Smoke-check the Spotify collector."""
    print("\n" + "=" * 60)
    print("Testing Spotify Collector")
    print("=" * 60)

    if not settings.spotify_client_id or not settings.spotify_client_secret:
        print("⚠ SKIPPED: Spotify credentials not configured")
        print("  Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to .env")
        return None

    try:
        client = SpotifyClient(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            access_token=settings.spotify_access_token or None,
            refresh_token=settings.spotify_refresh_token or None,
            redirect_uri=settings.spotify_redirect_uri,
        )

        print("Validating...", end=" ", flush=True)
        client.validate()
        print("✓")

        print("Fetching user profile...", end=" ", flush=True)
        user = client.get_current_user()
        print("✓")

        print("Collecting data...", end=" ", flush=True)
        data = client.collect()
        print("✓")

        print(f"\nResults:")
        print(f"  • Recently Played: {len(data['listening_history'])}")
        print(f"  • Top Tracks: {len(data['top_tracks'])}")
        print(f"  • Top Artists: {len(data['top_artists'])}")

        client.close()
        return True

    except Exception as e:
        print(f"\n✗ Failed: {str(e)}")
        return False


def main():
    """Run all collector smoke checks."""
    settings = get_settings()

    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "Data Collectors Test Suite" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")

    results = {
        "GitHub": test_github(settings),
        "Spotify": test_spotify(settings),
    }

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for r in results.values() if r is True)
    skipped = sum(1 for r in results.values() if r is None)
    failed = sum(1 for r in results.values() if r is False)

    for name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is None:
            status = "⊘ SKIP"
        else:
            status = "✗ FAIL"
        print(f"{name:20} {status}")

    print("=" * 60)
    summary = f"Passed: {passed} | Skipped: {skipped} | Failed: {failed}"
    print(summary)

    if failed > 0:
        print("\n⚠ Some tests failed. Check the errors above.")
        sys.exit(1)
    elif passed == 0:
        print("\n⚠ No tests were run. Configure your API credentials in .env")
        sys.exit(1)
    else:
        print("\n✓ All configured collectors are working!")


if __name__ == "__main__":
    main()
