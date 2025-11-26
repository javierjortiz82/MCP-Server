"""Automated background tasks for system cleanup and maintenance.

Tasks:
- cleanup_expired_sessions: Remove sessions that have exceeded their TTL/idle timeout

Note: OTP codes are stored in cache/memory and are automatically expired by the cache layer.
Database cleanup is not required for OTP codes at this time.

These tasks should be scheduled to run periodically (e.g., hourly via APScheduler or Celery).

Author: Lab01-MCP Team
Created: 2025-11-18
Version: 1.0.0
"""

import logging
from datetime import datetime, timezone

from demo_agent.config.settings import config
from demo_agent.db.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup logger
logger = logging.getLogger(__name__)


class CleanupTask:
    """Background cleanup tasks for database maintenance."""

    def __init__(self):
        """Initialize cleanup task with database connection."""
        self.engine = create_engine(config.DATABASE_URL, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.schema = config.SCHEMA_NAME

    def cleanup_expired_otp_codes(self) -> int:
        """Delete OTP codes that have expired.

        Note: OTP codes are currently stored in cache/memory, not in database.
        This method is a placeholder for future database-backed OTP storage.

        Returns:
            int: Number of expired OTP codes deleted (currently 0)
        """
        # OTP codes are not currently stored in database
        # Cleanup is handled by cache expiration
        return 0

    def cleanup_expired_sessions(self) -> int:
        """Delete sessions that have exceeded their timeout.

        Sessions expire based on:
        1. Idle timeout: No activity for SESSION_IDLE_TIMEOUT_MINUTES
        2. TTL: Total duration exceeds SESSION_TTL_MINUTES
        3. Absolute timeout: Total duration exceeds SESSION_ABSOLUTE_TIMEOUT_MINUTES

        This task should run periodically to clean up old session records.

        Returns:
            int: Number of expired sessions deleted
        """
        db = self.SessionLocal()
        try:
            from demo_agent.db.models import DemoSession

            now = datetime.now(timezone.utc)
            deleted_count = 0

            # Get all sessions and check each one for expiration
            all_sessions = db.query(DemoSession).all()

            for session in all_sessions:
                is_expired = False

                # Check idle timeout
                if session.last_activity_at:
                    idle_seconds = (now - session.last_activity_at).total_seconds()
                    if idle_seconds >= (config.SESSION_IDLE_TIMEOUT_MINUTES * 60):
                        is_expired = True

                # Check TTL
                if not is_expired and session.created_at:
                    ttl_seconds = (now - session.created_at).total_seconds()
                    if ttl_seconds >= (config.SESSION_TTL_MINUTES * 60):
                        is_expired = True

                # Check absolute timeout
                if not is_expired and session.created_at:
                    absolute_seconds = (now - session.created_at).total_seconds()
                    if absolute_seconds >= (config.SESSION_ABSOLUTE_TIMEOUT_MINUTES * 60):
                        is_expired = True

                # Delete expired session
                if is_expired:
                    db.delete(session)
                    deleted_count += 1

            db.commit()

            if deleted_count > 0:
                logger.info(f"Cleanup: Deleted {deleted_count} expired sessions")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            db.rollback()
            return 0

        finally:
            db.close()

    def cleanup_all(self) -> dict:
        """Run all cleanup tasks.

        Returns:
            dict: Summary of cleanup operations
        """
        logger.info("Starting cleanup tasks...")

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "expired_otp_codes": self.cleanup_expired_otp_codes(),
            "expired_sessions": self.cleanup_expired_sessions(),
        }

        logger.info(f"Cleanup complete: {result}")
        return result


def run_cleanup_tasks():
    """Entry point for running cleanup tasks.

    Can be scheduled to run periodically via:
    - APScheduler: https://apscheduler.readthedocs.io/
    - Celery: https://docs.celeryproject.io/
    - Cron: Unix cron jobs
    - Kubernetes CronJob: https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/

    Example with APScheduler:
    ```python
    from apscheduler.schedulers.background import BackgroundScheduler
    from demo_agent.tasks.cleanup_task import run_cleanup_tasks

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_cleanup_tasks, 'interval', hours=1)
    scheduler.start()
    ```
    """
    cleanup = CleanupTask()
    return cleanup.cleanup_all()


if __name__ == "__main__":
    # Can be run directly from command line:
    # python -m demo_agent.tasks.cleanup_task
    logging.basicConfig(level=logging.INFO)
    result = run_cleanup_tasks()
    print(f"Cleanup result: {result}")
