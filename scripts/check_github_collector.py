"""
Smoke-check script for the GitHub collector.
Run this to verify the GitHub client is working correctly.

Usage:
    poetry run python scripts/check_github_collector.py
"""
import sys
from pathlib import Path

# Add src directory to path for imports when running from source checkout
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.config import get_settings
from collectors.github_client import GitHubClient
from loguru import logger


def main():
    """Smoke-check the GitHub collector."""
    settings = get_settings()

    print("=" * 60)
    print("GitHub Collector Test")
    print("=" * 60)

    # Check for required credentials
    if not settings.github_token:
        print("\n✗ Error: GITHUB_TOKEN not set in .env file")
        print("  Please add your GitHub personal access token to .env")
        sys.exit(1)

    if not settings.github_username:
        print("\n✗ Error: GITHUB_USERNAME not set in .env file")
        print("  Please add your GitHub username to .env")
        sys.exit(1)

    print(f"\nGitHub Username: {settings.github_username}")
    print(f"GitHub Token: ***{settings.github_token[-10:] if len(settings.github_token) > 10 else '***'}")
    print()

    try:
        # Create client
        client = GitHubClient(
            github_token=settings.github_token,
            github_username=settings.github_username,
        )

        # Validate credentials
        print("Validating credentials...")
        client.validate()

        # Collect data
        print("\nCollecting GitHub data...")
        data = client.collect()

        # Print results
        print("\n" + "=" * 60)
        print("GitHub Data Collection Results")
        print("=" * 60)

        print(f"\n✓ Repositories: {len(data['repositories'])}")
        if data['repositories']:
            print("  Top 3 repositories:")
            for repo in data['repositories'][:3]:
                stars = repo.get('stars', 0)
                lang = repo.get('language', 'Unknown')
                print(f"    - {repo['full_name']} ({lang}, {stars} stars)")

        print(f"\n✓ Commits: {len(data['commits'])}")
        if data['commits']:
            print("  Latest 3 commits:")
            for commit in data['commits'][:3]:
                # Truncate long messages
                msg = commit['message'][:50] + "..." if len(commit['message']) > 50 else commit['message']
                print(f"    - {commit['sha'][:8]}: {msg}")

        print(f"\n✓ Contribution Days: {len(data['contributions'])}")
        if data['contributions']:
            print("  Recent days with activity:")
            for date in sorted(data['contributions'].keys())[-3:]:
                stats = data['contributions'][date]
                print(f"    - {date}: {stats['commit_count']} commits, "
                      f"{stats['repos_contributed']} repos touched")

        print("\n" + "=" * 60)
        print("✓ GitHub collector test successful!")
        print("=" * 60)
        client.close()

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Check that your GitHub token is valid")
        print("  2. Verify the token has 'repo' and 'user' scopes")
        print("  3. Ensure you have at least one repository")
        sys.exit(1)


if __name__ == "__main__":
    main()
