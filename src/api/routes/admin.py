"""Admin API routes for operational tasks."""
import threading
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, status
from loguru import logger
from sqlalchemy import text

from pipeline.config import get_settings
from pipeline.database import SessionLocal
from pipeline_jobs.aggregation_job import run_aggregation_job
from pipeline_jobs.github_job import run_github_job
from pipeline_jobs.spotify_job import run_spotify_job


router = APIRouter(prefix="/api/admin", tags=["Admin"])
settings = get_settings()

_backfill_lock = threading.Lock()
_BACKFILL_ADVISORY_LOCK_ID = 891337511


def _acquire_cross_worker_lock():
    """Acquire DB-level lock when running on PostgreSQL."""
    if not settings.database_url.startswith("postgres"):
        return None

    db = SessionLocal()
    try:
        acquired = db.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": _BACKFILL_ADVISORY_LOCK_ID},
        ).scalar()
        if not acquired:
            db.close()
            return None
        return db
    except Exception:
        db.close()
        raise


def _release_cross_worker_lock(db_session) -> None:
    """Release DB-level lock when used."""
    if db_session is None:
        return

    try:
        db_session.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": _BACKFILL_ADVISORY_LOCK_ID},
        )
    finally:
        db_session.close()


def _run_backfill() -> None:
    """Run a full backfill cycle inside the API process."""
    started_at = datetime.utcnow()
    logger.info("Admin backfill started at {}", started_at.isoformat())
    db_lock_session = None

    try:
        db_lock_session = _acquire_cross_worker_lock()
        if settings.database_url.startswith("postgres") and db_lock_session is None:
            logger.warning("Admin backfill skipped: another worker already holds lock")
            return

        run_github_job()
        run_spotify_job()
        run_aggregation_job()
        logger.info("Admin backfill completed successfully")
    except Exception as exc:
        logger.exception("Admin backfill failed: {}", exc)
    finally:
        _release_cross_worker_lock(db_lock_session)
        _backfill_lock.release()


def _validate_admin_access(x_admin_token: str | None) -> None:
    """Validate endpoint enablement and token authentication."""
    if not settings.backfill_endpoint_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    if not settings.backfill_admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backfill token is not configured",
        )

    if x_admin_token != settings.backfill_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )


@router.post("/backfill", status_code=status.HTTP_202_ACCEPTED)
def trigger_backfill(x_admin_token: str | None = Header(default=None)):
    """Trigger one background backfill run via an authenticated endpoint."""
    _validate_admin_access(x_admin_token)

    if not _backfill_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Backfill already running",
        )

    worker = threading.Thread(target=_run_backfill, daemon=True)
    worker.start()

    return {
        "status": "accepted",
        "message": "Backfill started",
        "started_at": datetime.utcnow().isoformat() + "Z",
    }
