"""
GitHub data collection and storage job.
Fetches GitHub data and persists it to the database.
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from loguru import logger

from pipeline.database import SessionLocal
from pipeline.config import get_settings
from pipeline.models import User, GitHubRepository, GitHubCommit, GitHubContribution
from collectors.github_client import GitHubClient


def run_github_job():
    """
    Main GitHub data collection job.
    Fetches data from GitHub API and stores it in the database.
    """
    settings = get_settings()
    
    logger.info("=" * 60)
    logger.info("GitHub Data Collection Job Started")
    logger.info("=" * 60)

    if not settings.github_token or not settings.github_username:
        logger.error("GitHub credentials not configured. Skipping job.")
        return

    db = SessionLocal()

    try:
        # Create or get user
        user = db.query(User).filter(User.github_username == settings.github_username).first()
        if not user:
            user = User(
                username=settings.github_username,
                github_username=settings.github_username,
                github_token=settings.github_token,
            )
            db.add(user)
            db.commit()
            logger.info(f"Created new user: {settings.github_username}")
        else:
            user.github_token = settings.github_token
            db.commit()
            logger.info(f"Updated existing user: {settings.github_username}")

        # Initialize GitHub client
        client = GitHubClient(
            github_token=settings.github_token,
            github_username=settings.github_username,
        )

        # Validate credentials
        logger.info("Validating GitHub credentials...")
        client.validate()

        # Collect data
        logger.info("Collecting GitHub data...")
        data = client.collect()

        # Store repositories
        logger.info(f"Storing {len(data['repositories'])} repositories...")
        _store_repositories(db, user, data['repositories'])

        # Store commits
        logger.info(f"Storing {len(data['commits'])} commits...")
        _store_commits(db, user, data['commits'])

        # Store contributions
        logger.info(f"Storing {len(data['contributions'])} contribution days...")
        _store_contributions(db, user, data['contributions'])

        logger.info("✓ GitHub job completed successfully")

    except Exception as e:
        logger.error(f"GitHub job failed: {str(e)}")
        db.rollback()
        raise

    finally:
        db.close()


def _store_repositories(db: Session, user: User, repositories: list):
    """Store repositories in the database."""
    for repo_data in repositories:
        repo = db.query(GitHubRepository).filter(
            GitHubRepository.user_id == user.id,
            GitHubRepository.repo_id == repo_data["id"],
        ).first()

        if not repo:
            repo = GitHubRepository(
                user_id=user.id,
                repo_id=repo_data["id"],
                repo_name=repo_data["name"],
                full_name=repo_data["full_name"],
                description=repo_data.get("description"),
                language=repo_data.get("language"),
                stars=repo_data.get("stars", 0),
                forks=repo_data.get("forks", 0),
                is_fork=repo_data.get("is_fork", False),
                is_private=repo_data.get("is_private", False),
                url=repo_data["url"],
                created_at=repo_data["created_at"],
                updated_at=repo_data.get("updated_at", datetime.utcnow()),
            )
            db.add(repo)
        else:
            # Update existing repo
            repo.stars = repo_data.get("stars", 0)
            repo.forks = repo_data.get("forks", 0)
            repo.description = repo_data.get("description")
            repo.language = repo_data.get("language")
            repo.updated_at = repo_data.get("updated_at", datetime.utcnow())
            repo.last_synced = datetime.utcnow()

    db.commit()
    logger.debug("Repositories stored")


def _store_commits(db: Session, user: User, commits: list):
    """Store commits in the database."""
    for commit_data in commits:
        # Check if commit already exists
        existing = db.query(GitHubCommit).filter(
            GitHubCommit.commit_sha == commit_data["sha"]
        ).first()

        if existing:
            continue  # Skip if already stored

        # Get repository
        repo = db.query(GitHubRepository).filter(
            GitHubRepository.user_id == user.id,
            GitHubRepository.full_name == commit_data["repo_full_name"],
        ).first()

        if not repo:
            logger.warning(f"Repository not found: {commit_data['repo_full_name']}")
            continue

        # Parse commit date
        try:
            commit_date = datetime.fromisoformat(
                commit_data["date"].replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            logger.warning(f"Invalid commit date: {commit_data['date']}")
            continue

        commit = GitHubCommit(
            user_id=user.id,
            repository_id=repo.id,
            commit_sha=commit_data["sha"],
            message=commit_data.get("message", "")[:500],  # Truncate long messages
            author_name=commit_data.get("author", "Unknown"),
            author_email=commit_data.get("author_email", ""),
            commit_date=commit_date,
            url=commit_data["url"],
        )
        db.add(commit)

    db.commit()
    logger.debug("Commits stored")


def _store_contributions(db: Session, user: User, contributions: dict):
    """Store daily contributions in the database."""
    from datetime import date
    
    for date_str, stats in contributions.items():
        try:
            contribution_date = datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            logger.warning(f"Invalid contribution date: {date_str}")
            continue

        # Check if already exists
        existing = db.query(GitHubContribution).filter(
            GitHubContribution.user_id == user.id,
            GitHubContribution.contribution_date == contribution_date,
        ).first()

        if existing:
            # Update existing contribution
            existing.commit_count = stats.get("commit_count", 0)
            existing.total_additions = stats.get("additions", 0)
            existing.total_deletions = stats.get("deletions", 0)
            existing.repos_contributed = stats.get("repos_contributed", 0)
            existing.languages = stats.get("languages", {})
        else:
            contribution = GitHubContribution(
                user_id=user.id,
                contribution_date=contribution_date,
                commit_count=stats.get("commit_count", 0),
                total_additions=stats.get("additions", 0),
                total_deletions=stats.get("deletions", 0),
                repos_contributed=stats.get("repos_contributed", 0),
                languages=stats.get("languages", {}),
            )
            db.add(contribution)

    db.commit()
    logger.debug("Contributions stored")
