"""Session management service with expiration handling.

Provides methods for:
- Session validation and expiration checking
- Activity tracking updates
- Session cleanup for expired sessions

Author: Lab01-MCP Team
Created: 2025-11-18
Version: 1.0.0
"""

import logging

from sqlalchemy.orm import Session as DbSession

from demo_agent.config.settings import config
from demo_agent.db.models import DemoSession

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing user sessions with expiration logic."""

    @staticmethod
    def is_session_expired(session: DemoSession) -> bool:
        """Check if a session has expired based on configured timeouts.

        Args:
            session: DemoSession instance to check

        Returns:
            bool: True if session has expired, False otherwise
        """
        if not session:
            return True

        return session.is_expired(
            ttl_minutes=config.SESSION_TTL_MINUTES,
            idle_timeout_minutes=config.SESSION_IDLE_TIMEOUT_MINUTES,
            absolute_timeout_minutes=config.SESSION_ABSOLUTE_TIMEOUT_MINUTES,
        )

    @staticmethod
    def get_expiration_reason(session: DemoSession) -> str | None:
        """Get human-readable reason for session expiration.

        Args:
            session: DemoSession instance to check

        Returns:
            str: Expiration reason ('idle_timeout', 'ttl', 'absolute_timeout') or None
        """
        if not session:
            return "session_not_found"

        return session.get_expiration_reason(
            ttl_minutes=config.SESSION_TTL_MINUTES,
            idle_timeout_minutes=config.SESSION_IDLE_TIMEOUT_MINUTES,
            absolute_timeout_minutes=config.SESSION_ABSOLUTE_TIMEOUT_MINUTES,
        )

    @staticmethod
    def update_session_activity(
        db: DbSession,
        session: DemoSession,
        tokens_used: int = 0,
    ) -> DemoSession:
        """Update session's activity timestamp and token usage.

        Called on each request to:
        1. Reset idle timeout counter
        2. Increment request count
        3. Update token consumption

        Args:
            db: Database session
            session: DemoSession instance to update
            tokens_used: Tokens consumed in this request

        Returns:
            DemoSession: Updated session instance
        """
        if not session:
            return None

        session.update_activity()
        session.total_requests += 1
        if tokens_used > 0:
            session.total_tokens_used += tokens_used

        try:
            db.add(session)
            db.commit()
            db.refresh(session)
            return session
        except Exception as e:
            logger.error(f"Error updating session activity: {str(e)}")
            db.rollback()
            return session

    @staticmethod
    def invalidate_session(db: DbSession, session: DemoSession) -> bool:
        """Invalidate/delete an expired session.

        Args:
            db: Database session
            session: DemoSession instance to invalidate

        Returns:
            bool: True if invalidation successful, False otherwise
        """
        if not session:
            return False

        try:
            db.delete(session)
            db.commit()
            logger.info(f"Session invalidated: {session.session_id}")
            return True
        except Exception as e:
            logger.error(f"Error invalidating session: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def cleanup_expired_sessions(db: DbSession) -> int:
        """Delete all expired sessions from database.

        This should be called periodically (e.g., hourly) to clean up
        old session records.

        Args:
            db: Database session

        Returns:
            int: Number of sessions deleted
        """
        try:
            # Get all sessions
            all_sessions = db.query(DemoSession).all()
            expired_count = 0

            for session in all_sessions:
                if SessionService.is_session_expired(session):
                    db.delete(session)
                    expired_count += 1

            db.commit()
            logger.info(f"Cleanup: Deleted {expired_count} expired sessions")
            return expired_count

        except Exception as e:
            logger.error(f"Error during session cleanup: {str(e)}")
            db.rollback()
            return 0

    @staticmethod
    def get_session_stats(session: DemoSession) -> dict:
        """Get detailed stats about a session.

        Args:
            session: DemoSession instance

        Returns:
            dict: Session statistics and status
        """
        if not session:
            return {}

        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "is_expired": SessionService.is_session_expired(session),
            "expiration_reason": SessionService.get_expiration_reason(session),
            "duration_seconds": session.session_duration,
            "total_requests": session.total_requests,
            "total_tokens_used": session.total_tokens_used,
            "avg_tokens_per_request": session.avg_tokens_per_request(),
            "created_at": session.created_at,
            "last_activity_at": session.last_activity_at,
            "language": session.language,
        }
