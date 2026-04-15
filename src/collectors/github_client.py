"""
GitHub API client for collecting repository, commit, and contribution data.
Uses GitHub REST API v3 with OAuth2 authentication.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from loguru import logger
from collections import defaultdict

from collectors._base import BaseCollector, AuthenticationError, DataValidationError


class GitHubClient(BaseCollector):
    """
    GitHub API client for collecting data.
    
    Collects:
    - Repository list and metadata
    - Commit history
    - Contribution statistics
    - Language breakdown
    """

    BASE_URL = "https://api.github.com"
    ENDPOINTS = {
        "user": "/user",
        "repos": "/user/repos",
        "repo_commits": "/repos/{owner}/{repo}/commits",
        "repo_stats": "/repos/{owner}/{repo}",
    }

    def __init__(self, github_token: str, github_username: str):
        """
        Initialize GitHub client.

        Args:
            github_token: GitHub personal access token
            github_username: GitHub username
        """
        super().__init__()
        self.github_token = github_token
        self.github_username = github_username
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def validate(self) -> bool:
        """
        Validate GitHub credentials by testing API access.

        Returns:
            True if credentials are valid

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.github_token or not self.github_username:
            raise AuthenticationError("GitHub token and username are required")

        try:
            logger.info("Validating GitHub credentials...")
            response = self._request_with_retry(
                method="GET",
                url=f"{self.BASE_URL}{self.ENDPOINTS['user']}",
                headers=self.headers,
            )
            user_data = response.json()
            logger.info(f"✓ GitHub authentication successful for user: {user_data.get('login')}")
            return True
        except Exception as e:
            logger.error(f"GitHub authentication failed: {str(e)}")
            raise AuthenticationError(f"Failed to authenticate with GitHub: {str(e)}")

    def collect(self) -> Dict[str, Any]:
        """
        Collect all GitHub data.

        Returns:
            Dictionary with repositories, commits, and contribution stats
        """
        logger.info("Starting GitHub data collection...")

        try:
            repositories = self._get_repositories()
            logger.info(f"Found {len(repositories)} repositories")

            commits = self._get_commits(repositories)
            logger.info(f"Fetched {len(commits)} commits")

            contributions = self._calculate_contributions(commits)
            logger.info(f"Calculated contributions for {len(contributions)} days")

            return {
                "repositories": repositories,
                "commits": commits,
                "contributions": contributions,
                "collected_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"GitHub data collection failed: {str(e)}")
            raise

    def _get_repositories(self) -> List[Dict[str, Any]]:
        """
        Fetch all repositories for the authenticated user.

        Returns:
            List of repository dictionaries
        """
        logger.debug("Fetching repositories...")
        repositories = []
        page = 1
        per_page = 100

        while True:
            try:
                response = self._request_with_retry(
                    method="GET",
                    url=f"{self.BASE_URL}{self.ENDPOINTS['repos']}",
                    headers=self.headers,
                    params={
                        "type": "owner",
                        "sort": "updated",
                        "per_page": per_page,
                        "page": page,
                    },
                )

                data = response.json()
                if not data:
                    break

                for repo in data:
                    repositories.append({
                        "id": repo["id"],
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "description": repo["description"],
                        "language": repo["language"],
                        "stars": repo["stargazers_count"],
                        "forks": repo["forks_count"],
                        "is_fork": repo["fork"],
                        "is_private": repo["private"],
                        "url": repo["html_url"],
                        "created_at": repo["created_at"],
                        "updated_at": repo["updated_at"],
                    })

                page += 1

            except Exception as e:
                logger.error(f"Error fetching repositories page {page}: {str(e)}")
                break

        return repositories

    def _get_commits(self, repositories: List[Dict[str, Any]], days: int = 730) -> List[Dict[str, Any]]:
        """
        Fetch commits from all repositories.

        Args:
            repositories: List of repository dictionaries
            days: Number of days to look back (default 2 years)

        Returns:
            List of commit dictionaries
        """
        logger.debug(f"Fetching commits from last {days} days...")
        commits = []
        since_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        for repo in repositories:
            repo_owner = repo["full_name"].split("/")[0]
            repo_name = repo["name"]
            page = 1

            try:
                while True:
                    response = self._request_with_retry(
                        method="GET",
                        url=f"{self.BASE_URL}/repos/{repo_owner}/{repo_name}/commits",
                        headers=self.headers,
                        params={
                            "since": since_date,
                            "per_page": 100,
                            "page": page,
                        },
                    )

                    data = response.json()
                    if not data:
                        break

                    for commit in data:
                        try:
                            commits.append({
                                "sha": commit["sha"],
                                "message": commit["commit"]["message"],
                                "author": commit["commit"]["author"]["name"],
                                "author_email": commit["commit"]["author"]["email"],
                                "date": commit["commit"]["author"]["date"],
                                "repo_name": repo_name,
                                "repo_full_name": repo["full_name"],
                                "url": commit["html_url"],
                            })
                        except KeyError as e:
                            logger.warning(f"Missing expected commit data field: {e}")
                            continue

                    page += 1

            except Exception as e:
                logger.warning(f"Error fetching commits for {repo['full_name']}: {str(e)}")
                continue

        return commits

    def _get_commit_details(self, owner: str, repo: str, sha: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a single commit.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA

        Returns:
            Commit detail dictionary with additions and deletions
        """
        try:
            response = self._request_with_retry(
                method="GET",
                url=f"{self.BASE_URL}/repos/{owner}/{repo}/commits/{sha}",
                headers=self.headers,
            )
            data = response.json()

            return {
                "additions": data["stats"]["additions"],
                "deletions": data["stats"]["deletions"],
                "files_changed": len(data["files"]),
            }
        except Exception as e:
            logger.warning(f"Could not fetch commit details for {sha}: {str(e)}")
            return {"additions": 0, "deletions": 0, "files_changed": 0}

    def _calculate_contributions(self, commits: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate daily contribution statistics from commits.

        Args:
            commits: List of commit dictionaries

        Returns:
            Dictionary with dates as keys and contribution stats as values
        """
        contributions = defaultdict(lambda: {
            "commit_count": 0,
            "additions": 0,
            "deletions": 0,
            "repos": set(),
            "languages": defaultdict(int),
        })

        for commit in commits:
            try:
                commit_date = datetime.fromisoformat(
                    commit["date"].replace("Z", "+00:00")
                ).date().isoformat()

                contributions[commit_date]["commit_count"] += 1
                contributions[commit_date]["repos"].add(commit["repo_name"])

            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing commit: {str(e)}")
                continue

        # Convert to regular dicts and repos/languages to counts
        result = {}
        for date, stats in contributions.items():
            result[date] = {
                "commit_count": stats["commit_count"],
                "additions": stats["additions"],
                "deletions": stats["deletions"],
                "repos_contributed": len(stats["repos"]),
                "languages": dict(stats["languages"]),
            }

        return result

    def get_language_stats(self, repositories: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Calculate language breakdown from repositories.

        Args:
            repositories: List of repository dictionaries

        Returns:
            Dictionary with language names and commit counts
        """
        language_stats = defaultdict(int)

        for repo in repositories:
            if repo.get("language"):
                language_stats[repo["language"]] += 1

        return dict(language_stats)
