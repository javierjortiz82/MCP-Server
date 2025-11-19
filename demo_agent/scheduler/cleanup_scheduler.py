"""Cleanup Task Scheduler using APScheduler.

Configures and manages periodic cleanup tasks for:
- Expired OTP codes
- Expired sessions

Tasks run on a background schedule without blocking the application.

Author: Lab01-MCP Team
Created: 2025-11-18
Version: 1.0.0
"""

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from demo_agent.config.settings import config
from demo_agent.tasks.cleanup_task import CleanupTask

logger = logging.getLogger(__name__)


class CleanupScheduler:
    """Manages periodic cleanup tasks using APScheduler."""

    _instance: Optional[BackgroundScheduler] = None
    _is_running: bool = False

    @classmethod
    def initialize(cls, cleanup_interval_hours: int = 1) -> BackgroundScheduler:
        """Initialize and start the cleanup scheduler.

        Args:
            cleanup_interval_hours: Run cleanup tasks every N hours (default: 1)

        Returns:
            BackgroundScheduler: Initialized and started scheduler

        Raises:
            RuntimeError: If scheduler is already initialized
        """
        if cls._instance is not None and cls._is_running:
            logger.warning("Cleanup scheduler is already running")
            return cls._instance

        try:
            # Create scheduler instance
            scheduler = BackgroundScheduler()

            # Configure timezone
            scheduler.configure(timezone="UTC")

            # Add cleanup job
            job = scheduler.add_job(
                func=CleanupTask().cleanup_all,
                trigger=IntervalTrigger(hours=cleanup_interval_hours),
                id="cleanup_expired_records",
                name="Cleanup expired OTP codes and sessions",
                replace_existing=True,
                max_instances=1,  # Prevent concurrent executions
            )

            logger.info(
                f"✅ Cleanup scheduler configured: "
                f"runs every {cleanup_interval_hours} hour(s)"
            )
            logger.info(f"   Job ID: {job.id}")
            logger.info(f"   Next run: {job.next_run_time}")

            # Start scheduler
            scheduler.start()
            cls._instance = scheduler
            cls._is_running = True

            logger.info("✅ Cleanup scheduler started")

            return scheduler

        except Exception as e:
            logger.error(f"Failed to initialize cleanup scheduler: {str(e)}")
            raise RuntimeError(f"Cleanup scheduler initialization failed: {e}") from e

    @classmethod
    def shutdown(cls) -> None:
        """Shutdown the cleanup scheduler gracefully.

        Waits for running jobs to complete before stopping.
        """
        if cls._instance is None or not cls._is_running:
            logger.debug("Cleanup scheduler is not running")
            return

        try:
            logger.info("Shutting down cleanup scheduler...")
            cls._instance.shutdown(wait=True)
            cls._is_running = False
            logger.info("✅ Cleanup scheduler stopped")

        except Exception as e:
            logger.error(f"Error shutting down cleanup scheduler: {str(e)}")

    @classmethod
    def get_scheduler(cls) -> Optional[BackgroundScheduler]:
        """Get the current scheduler instance.

        Returns:
            BackgroundScheduler | None: Scheduler if initialized, None otherwise
        """
        return cls._instance

    @classmethod
    def is_running(cls) -> bool:
        """Check if scheduler is currently running.

        Returns:
            bool: True if scheduler is running, False otherwise
        """
        return cls._is_running and cls._instance is not None

    @classmethod
    def get_jobs(cls) -> list:
        """Get list of scheduled jobs.

        Returns:
            list: List of APScheduler Job objects
        """
        if cls._instance is None:
            return []

        return cls._instance.get_jobs()

    @classmethod
    def pause_job(cls, job_id: str) -> bool:
        """Pause a scheduled job.

        Args:
            job_id: ID of the job to pause

        Returns:
            bool: True if successful, False otherwise
        """
        if cls._instance is None:
            logger.warning("Scheduler not initialized")
            return False

        try:
            cls._instance.pause_job(job_id)
            logger.info(f"Job paused: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error pausing job {job_id}: {str(e)}")
            return False

    @classmethod
    def resume_job(cls, job_id: str) -> bool:
        """Resume a paused job.

        Args:
            job_id: ID of the job to resume

        Returns:
            bool: True if successful, False otherwise
        """
        if cls._instance is None:
            logger.warning("Scheduler not initialized")
            return False

        try:
            cls._instance.resume_job(job_id)
            logger.info(f"Job resumed: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error resuming job {job_id}: {str(e)}")
            return False

    @classmethod
    def reschedule_job(cls, job_id: str, trigger: IntervalTrigger) -> bool:
        """Reschedule a job with new trigger parameters.

        Args:
            job_id: ID of the job to reschedule
            trigger: New trigger configuration

        Returns:
            bool: True if successful, False otherwise
        """
        if cls._instance is None:
            logger.warning("Scheduler not initialized")
            return False

        try:
            cls._instance.reschedule_job(job_id, trigger=trigger)
            logger.info(f"Job rescheduled: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error rescheduling job {job_id}: {str(e)}")
            return False


def init_cleanup_scheduler(app=None) -> None:
    """Initialize cleanup scheduler and attach to FastAPI app lifecycle.

    Args:
        app: FastAPI application instance (optional, for lifespan registration)

    This function should be called during app startup.
    """
    try:
        # Initialize scheduler with configurable interval (default: hourly)
        scheduler = CleanupScheduler.initialize(cleanup_interval_hours=1)

        logger.info(
            f"🕐 Cleanup scheduler initialized with interval: 1 hour"
        )
        logger.info(f"   Configuration:")
        logger.info(f"   - SESSION_TTL_MINUTES: {config.SESSION_TTL_MINUTES}")
        logger.info(f"   - SESSION_IDLE_TIMEOUT_MINUTES: {config.SESSION_IDLE_TIMEOUT_MINUTES}")
        logger.info(f"   - SESSION_ABSOLUTE_TIMEOUT_MINUTES: {config.SESSION_ABSOLUTE_TIMEOUT_MINUTES}")
        logger.info(f"   - OTP_EXPIRATION_MINUTES: {config.OTP_EXPIRATION_MINUTES}")

        # If app is provided, register shutdown handler
        if app:
            @app.on_event("shutdown")
            async def shutdown_cleanup_scheduler():
                """Shutdown scheduler on app shutdown."""
                CleanupScheduler.shutdown()

            logger.info("✅ Cleanup scheduler shutdown handler registered")

    except Exception as e:
        logger.error(f"Failed to initialize cleanup scheduler: {str(e)}")
        raise