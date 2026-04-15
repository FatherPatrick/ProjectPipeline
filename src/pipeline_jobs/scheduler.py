"""
APScheduler setup and job scheduling.
Manages scheduled execution of data collection and aggregation jobs.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
import signal
import sys

from pipeline.config import get_settings
from pipeline_jobs.github_job import run_github_job
from pipeline_jobs.spotify_job import run_spotify_job
from pipeline_jobs.aggregation_job import run_aggregation_job


class PipelineScheduler:
    """Manages scheduled pipeline jobs."""

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BackgroundScheduler()
        self.settings = get_settings()

    def start(self):
        """Start the scheduler and add all jobs."""
        if not self.settings.scheduler_enabled:
            logger.warning("Scheduler is disabled. No jobs will run.")
            return

        logger.info("=" * 60)
        logger.info("Pipeline Scheduler Starting")
        logger.info("=" * 60)
        logger.info(f"Refresh Interval: Every {self.settings.data_refresh_interval_hours} hours")
        logger.info(f"Timezone: {self.settings.scheduler_timezone}\n")

        # Add GitHub job
        self.scheduler.add_job(
            func=run_github_job,
            trigger=CronTrigger(hour="*/6"),  # Every 6 hours
            id="github_collection",
            name="GitHub Data Collection",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=0,
        )
        logger.info("✓ Scheduled GitHub job - every 6 hours")

        # Add Spotify job
        self.scheduler.add_job(
            func=run_spotify_job,
            trigger=CronTrigger(hour="*/6"),  # Every 6 hours
            id="spotify_collection",
            name="Spotify Data Collection",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=0,
        )
        logger.info("✓ Scheduled Spotify job - every 6 hours")

        # Add aggregation job - runs daily at 2 AM
        self.scheduler.add_job(
            func=run_aggregation_job,
            trigger=CronTrigger(hour=2, minute=0),
            id="daily_aggregation",
            name="Daily Aggregation",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=0,
        )
        logger.info("✓ Scheduled Aggregation job - daily at 2:00 AM")

        # Start scheduler
        self.scheduler.start()
        logger.info("\n" + "=" * 60)
        logger.info("✓ Pipeline Scheduler Started Successfully")
        logger.info("=" * 60)
        logger.info("\nEventually press Ctrl+C to stop the scheduler")

    def stop(self):
        """Stop the scheduler gracefully."""
        logger.info("\nShutting down scheduler...")
        self.scheduler.shutdown()
        logger.info("✓ Scheduler stopped")

    def run_now(self, job_id: str):
        """Manually trigger a job."""
        job = self.scheduler.get_job(job_id)
        if job:
            logger.info(f"Manually triggering job: {job.name}")
            job.func()
        else:
            logger.error(f"Job not found: {job_id}")

    def list_jobs(self):
        """List all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        logger.info("\nScheduled Jobs:")
        for job in jobs:
            logger.info(f"  • {job.name} (ID: {job.id})")
            logger.info(f"    Next run: {job.next_run_time}")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def setup_signal_handlers(scheduler: PipelineScheduler):
    """Set up signal handlers for graceful shutdown."""

    def handle_signal(signum, frame):
        logger.info(f"\nReceived signal {signum}. Shutting down gracefully...")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


def main():
    """Main entry point for the scheduler."""
    settings = get_settings()

    logger.add(
        settings.log_file,
        rotation="00:00",  # Rotate at midnight
        retention="30 days",
        level=settings.log_level,
    )

    logger.info(f"Starting Pipeline Scheduler in {settings.environment} mode")

    scheduler = PipelineScheduler()
    setup_signal_handlers(scheduler)

    try:
        scheduler.start()
        scheduler.list_jobs()

        # Keep the scheduler running
        import time
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\nKeyboard interrupt received")
        scheduler.stop()
        sys.exit(0)

    except Exception as e:
        logger.error(f"Scheduler error: {str(e)}", exc_info=True)
        scheduler.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
