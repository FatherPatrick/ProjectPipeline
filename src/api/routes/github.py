"""
GitHub API routes.
Endpoints for querying GitHub data.
"""
from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from pipeline.database import get_db
from pipeline.models import (
    GitHubRepository,
    GitHubCommit,
    GitHubContribution,
    User,
)
from api.schemas import (
    GitHubRepositoryResponse,
    GitHubCommitResponse,
    GitHubContributionResponse,
    GitHubStatsResponse,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/github", tags=["GitHub"])


@router.get("/stats", response_model=GitHubStatsResponse)
def get_github_stats(
    days: int = Query(30, ge=1, le=730),
    db: Session = Depends(get_db),
):
    """
    Get overall GitHub statistics.
    
    Args:
        days: Number of days to look back (default: 30)
    
    Returns:
        GitHub statistics including commits, additions, languages, etc.
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        since_date = date.today() - timedelta(days=days)

        # Get repositories
        repos = db.query(GitHubRepository).filter(
            GitHubRepository.user_id == user.id
        ).all()

        # Get commits in date range
        commits = db.query(GitHubCommit).filter(
            GitHubCommit.user_id == user.id,
            func.date(GitHubCommit.commit_date) >= since_date,
        ).all()

        # Get contributions
        contributions = db.query(GitHubContribution).filter(
            GitHubContribution.user_id == user.id,
            GitHubContribution.contribution_date >= since_date,
        ).all()

        # Calculate statistics
        total_repositories = len(repos)
        total_commits = len(commits)
        total_additions = sum(c.additions for c in commits)
        total_deletions = sum(c.deletions for c in commits)
        
        avg_commits_per_day = (
            total_commits / days if days > 0 else 0
        )

        # Language breakdown
        language_breakdown = {}
        for repo in repos:
            if repo.language:
                language_breakdown[repo.language] = language_breakdown.get(repo.language, 0) + 1

        most_used_language = max(
            language_breakdown, 
            key=language_breakdown.get
        ) if language_breakdown else None

        # Contribution metrics
        contribution_days = len(contributions)
        
        # Calculate consecutive days
        consecutive_days = 0
        if contributions:
            sorted_contribs = sorted(contributions, key=lambda x: x.contribution_date, reverse=True)
            current_date = date.today()
            for contrib in sorted_contribs:
                if (current_date - contrib.contribution_date).days == consecutive_days:
                    consecutive_days += 1
                else:
                    break

        # Top repositories by stars
        top_repos = sorted(repos, key=lambda x: x.stars, reverse=True)[:5]

        return GitHubStatsResponse(
            total_repositories=total_repositories,
            total_commits=total_commits,
            total_additions=total_additions,
            total_deletions=total_deletions,
            average_commits_per_day=round(avg_commits_per_day, 2),
            most_used_language=most_used_language,
            language_breakdown=language_breakdown,
            contribution_days=contribution_days,
            consecutive_days=consecutive_days,
            top_repositories=[GitHubRepositoryResponse.model_validate(r) for r in top_repos],
        )

    except Exception as e:
        logger.error(f"Error getting GitHub stats: {str(e)}")
        raise


@router.get("/repositories", response_model=PaginatedResponse)
def get_repositories(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    sort_by: str = Query("stars", regex="^(stars|updated_at|name)$"),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of repositories.
    
    Args:
        skip: Number of items to skip
        limit: Number of items to return
        sort_by: Field to sort by (stars, updated_at, name)
    
    Returns:
        Paginated list of repositories
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        query = db.query(GitHubRepository).filter(
            GitHubRepository.user_id == user.id
        )

        # Apply sorting
        if sort_by == "stars":
            query = query.order_by(GitHubRepository.stars.desc())
        elif sort_by == "updated_at":
            query = query.order_by(GitHubRepository.updated_at.desc())
        else:
            query = query.order_by(GitHubRepository.repo_name)

        total = query.count()
        repos = query.offset(skip).limit(limit).all()

        return PaginatedResponse.create(
            items=[GitHubRepositoryResponse.model_validate(r) for r in repos],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Error getting repositories: {str(e)}")
        raise


@router.get("/contributions", response_model=list[GitHubContributionResponse])
def get_contributions(
    days: int = Query(30, ge=1, le=730),
    limit: int = Query(50, ge=1, le=730),
    db: Session = Depends(get_db),
):
    """
    Get daily contributions.
    
    Args:
        days: Number of days to look back
        limit: Maximum number of days to return
    
    Returns:
        List of daily contributions
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        since_date = date.today() - timedelta(days=min(days, limit))

        contributions = db.query(GitHubContribution).filter(
            GitHubContribution.user_id == user.id,
            GitHubContribution.contribution_date >= since_date,
        ).order_by(GitHubContribution.contribution_date.desc()).all()

        return [GitHubContributionResponse.model_validate(c) for c in contributions]

    except Exception as e:
        logger.error(f"Error getting contributions: {str(e)}")
        raise


@router.get("/commits", response_model=PaginatedResponse)
def get_commits(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    days: int = Query(30, ge=1, le=730),
    db: Session = Depends(get_db),
):
    """
    Get paginated list of commits.
    
    Args:
        skip: Number of items to skip
        limit: Number of items to return
        days: Number of days to look back
    
    Returns:
        Paginated list of commits
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        since_date = datetime.utcnow() - timedelta(days=days)

        query = db.query(GitHubCommit).filter(
            GitHubCommit.user_id == user.id,
            GitHubCommit.commit_date >= since_date,
        ).order_by(GitHubCommit.commit_date.desc())

        total = query.count()
        commits = query.offset(skip).limit(limit).all()

        return PaginatedResponse.create(
            items=[GitHubCommitResponse.model_validate(c) for c in commits],
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Error getting commits: {str(e)}")
        raise


@router.get("/languages", response_model=dict)
def get_language_breakdown(
    days: int = Query(30, ge=1, le=730),
    db: Session = Depends(get_db),
):
    """
    Get language breakdown of commits.
    
    Args:
        days: Number of days to look back
    
    Returns:
        Dictionary of languages and commit counts
    """
    try:
        user = db.query(User).first()
        if not user:
            raise ValueError("No user found in database")

        since_date = date.today() - timedelta(days=days)

        contributions = db.query(GitHubContribution).filter(
            GitHubContribution.user_id == user.id,
            GitHubContribution.contribution_date >= since_date,
        ).all()

        # Aggregate languages across all contributions
        language_stats = {}
        for contrib in contributions:
            for lang, count in contrib.languages.items():
                language_stats[lang] = language_stats.get(lang, 0) + count

        # Sort by count
        sorted_languages = dict(
            sorted(language_stats.items(), key=lambda x: x[1], reverse=True)
        )

        return sorted_languages

    except Exception as e:
        logger.error(f"Error getting languages: {str(e)}")
        raise
