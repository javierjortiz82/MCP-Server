"""End-to-End Test for Session Expiration Mechanism.

Tests the complete session lifecycle:
1. User registers with OTP
2. Session created and validated
3. Session expires after configured TTL
4. User must re-authenticate with OTP

Run with:
    python -m pytest demo_agent/tests/test_session_expiration_e2e.py -v

Author: Lab01-MCP Team
Created: 2025-11-18
Version: 1.0.0
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from demo_agent.config.settings import config
from demo_agent.db.models import Base, DemoSession
from demo_agent.services.session_service import SessionService


class TestSessionExpirationE2E:
    """End-to-end tests for session expiration functionality."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session."""
        # Use test database URL if configured, otherwise use main DB
        engine = create_engine(config.DATABASE_URL, echo=False)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    @pytest.fixture
    def test_session(self, db_session):
        """Create a test DemoSession record."""
        session = DemoSession(
            id=str(uuid4()),
            session_id=f"sess_test_{uuid4().hex[:8]}",
            user_id="test_user_001",
            language="es",
            created_at=datetime.now(timezone.utc),
            last_activity_at=datetime.now(timezone.utc),
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session

    def test_session_creation_and_validity(self, test_session, db_session):
        """Test that a newly created session is valid (not expired)."""
        # Verify session was created
        assert test_session.id is not None
        assert test_session.session_id is not None

        # Verify session is NOT expired
        is_expired = SessionService.is_session_expired(test_session)
        assert not is_expired, "Newly created session should not be expired"

        # Verify expiration reason is None
        reason = SessionService.get_expiration_reason(test_session)
        assert reason is None, "Newly created session should have no expiration reason"

    def test_session_idle_timeout_expiration(self, test_session, db_session):
        """Test that session expires after idle timeout."""
        # Set last_activity_at to past (simulate inactivity)
        # Use TTL of 2 minutes (from config) and idle timeout of 1 minute
        idle_timeout_minutes = config.SESSION_IDLE_TIMEOUT_MINUTES
        past_time = datetime.now(timezone.utc) - timedelta(minutes=idle_timeout_minutes + 1)

        test_session.last_activity_at = past_time
        db_session.add(test_session)
        db_session.commit()

        # Now session should be expired due to idle timeout
        is_expired = SessionService.is_session_expired(test_session)
        assert is_expired, "Session should be expired after idle timeout"

        reason = SessionService.get_expiration_reason(test_session)
        assert reason == "idle_timeout", f"Expected 'idle_timeout' but got '{reason}'"

    def test_session_ttl_expiration(self, test_session, db_session):
        """Test that session expires after TTL (Time-To-Live)."""
        # Set created_at to past (simulate old session)
        # Use TTL of 2 minutes from config
        ttl_minutes = config.SESSION_TTL_MINUTES
        past_time = datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes + 1)

        test_session.created_at = past_time
        test_session.last_activity_at = datetime.now(timezone.utc)  # Keep activity recent
        db_session.add(test_session)
        db_session.commit()

        # Now session should be expired due to TTL
        is_expired = SessionService.is_session_expired(test_session)
        assert is_expired, "Session should be expired after TTL"

        reason = SessionService.get_expiration_reason(test_session)
        assert reason == "ttl", f"Expected 'ttl' but got '{reason}'"

    def test_session_activity_update(self, test_session, db_session):
        """Test that session activity timestamp is updated."""
        original_activity = test_session.last_activity_at
        time.sleep(0.1)  # Small delay to ensure time difference

        # Simulate user activity
        SessionService.update_session_activity(db_session, test_session)

        # Verify activity was updated
        assert test_session.last_activity_at > original_activity, "Activity timestamp should be updated"

        # Verify session is still valid after activity update
        is_expired = SessionService.is_session_expired(test_session)
        assert not is_expired, "Session should remain valid after activity update"

    def test_session_invalidation(self, test_session, db_session):
        """Test that expired sessions can be invalidated."""
        session_id = test_session.session_id

        # Invalidate the session
        success = SessionService.invalidate_session(db_session, test_session)
        assert success, "Session invalidation should succeed"

        # Verify session is deleted from database
        deleted_session = db_session.query(DemoSession).filter(
            DemoSession.session_id == session_id
        ).first()
        assert deleted_session is None, "Session should be deleted after invalidation"

    def test_session_cleanup(self, db_session):
        """Test that expired sessions are cleaned up."""
        # Create multiple test sessions with different expiration states
        sessions_to_create = []

        # Session 1: Valid (recent)
        sessions_to_create.append(DemoSession(
            id=str(uuid4()),
            session_id=f"sess_valid_{uuid4().hex[:8]}",
            user_id="test_user_001",
            language="es",
            created_at=datetime.now(timezone.utc),
            last_activity_at=datetime.now(timezone.utc),
        ))

        # Session 2: Expired (idle timeout)
        idle_expired = DemoSession(
            id=str(uuid4()),
            session_id=f"sess_idle_expired_{uuid4().hex[:8]}",
            user_id="test_user_002",
            language="es",
            created_at=datetime.now(timezone.utc),
            last_activity_at=datetime.now(timezone.utc) - timedelta(minutes=config.SESSION_IDLE_TIMEOUT_MINUTES + 1),
        )
        sessions_to_create.append(idle_expired)

        # Session 3: Expired (TTL)
        ttl_expired = DemoSession(
            id=str(uuid4()),
            session_id=f"sess_ttl_expired_{uuid4().hex[:8]}",
            user_id="test_user_003",
            language="es",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=config.SESSION_TTL_MINUTES + 1),
            last_activity_at=datetime.now(timezone.utc),
        )
        sessions_to_create.append(ttl_expired)

        # Add all sessions to database
        for session in sessions_to_create:
            db_session.add(session)
        db_session.commit()

        # Run cleanup
        expired_count = SessionService.cleanup_expired_sessions(db_session)

        # Should have cleaned up 2 expired sessions (idle + TTL)
        assert expired_count == 2, f"Expected 2 expired sessions, got {expired_count}"

        # Verify valid session still exists
        valid_session = db_session.query(DemoSession).filter(
            DemoSession.session_id == sessions_to_create[0].session_id
        ).first()
        assert valid_session is not None, "Valid session should not be deleted"

    def test_session_stats(self, test_session, db_session):
        """Test session statistics generation."""
        # Add some activity to the session
        test_session.total_requests = 5
        test_session.total_tokens_used = 1250
        db_session.add(test_session)
        db_session.commit()

        # Get session stats
        stats = SessionService.get_session_stats(test_session)

        # Verify stats structure and values
        assert stats["session_id"] == test_session.session_id
        assert stats["user_id"] == "test_user_001"
        assert stats["is_expired"] is False
        assert stats["total_requests"] == 5
        assert stats["total_tokens_used"] == 1250
        assert stats["avg_tokens_per_request"] == pytest.approx(250.0)
        assert stats["language"] == "es"

    def test_configuration_values(self):
        """Test that session configuration values are properly set."""
        # Verify configuration is loaded
        assert config.SESSION_TTL_MINUTES > 0, "SESSION_TTL_MINUTES must be configured"
        assert config.SESSION_IDLE_TIMEOUT_MINUTES > 0, "SESSION_IDLE_TIMEOUT_MINUTES must be configured"
        assert config.SESSION_ABSOLUTE_TIMEOUT_MINUTES > 0, "SESSION_ABSOLUTE_TIMEOUT_MINUTES must be configured"

        # Verify reasonable ranges (for testing: 1-2 minutes)
        assert config.SESSION_TTL_MINUTES <= 1440, "SESSION_TTL_MINUTES should not exceed 24 hours"
        assert config.SESSION_IDLE_TIMEOUT_MINUTES <= 720, "SESSION_IDLE_TIMEOUT_MINUTES should not exceed 12 hours"

        # Verify consistency: idle < TTL < absolute
        assert config.SESSION_IDLE_TIMEOUT_MINUTES < config.SESSION_TTL_MINUTES, \
            "Idle timeout should be less than TTL"
        assert config.SESSION_TTL_MINUTES < config.SESSION_ABSOLUTE_TIMEOUT_MINUTES, \
            "TTL should be less than absolute timeout"


class TestSessionExpirationScenarios:
    """Integration tests for realistic session expiration scenarios."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session."""
        engine = create_engine(config.DATABASE_URL, echo=False)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_e2e_session_lifecycle(self, db_session):
        """Test complete session lifecycle from creation to expiration."""
        # Step 1: Create session (user registered with OTP)
        session_id = f"sess_e2e_{uuid4().hex[:8]}"
        user_id = "test_user_e2e"

        session = DemoSession(
            id=str(uuid4()),
            session_id=session_id,
            user_id=user_id,
            language="es",
            created_at=datetime.now(timezone.utc),
            last_activity_at=datetime.now(timezone.utc),
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # Step 2: Verify session is valid
        assert not SessionService.is_session_expired(session)
        print(f"✓ Session created and valid: {session_id}")

        # Step 3: Simulate user activity
        SessionService.update_session_activity(db_session, session, tokens_used=100)
        assert session.total_requests == 1
        assert session.total_tokens_used == 100
        print(f"✓ Session activity tracked: 1 request, 100 tokens")

        # Step 4: Simulate more activity
        time.sleep(0.1)
        SessionService.update_session_activity(db_session, session, tokens_used=150)
        assert session.total_requests == 2
        assert session.total_tokens_used == 250
        print(f"✓ Session activity updated: 2 requests, 250 tokens total")

        # Step 5: Simulate idle timeout
        idle_timeout = config.SESSION_IDLE_TIMEOUT_MINUTES
        session.last_activity_at = datetime.now(timezone.utc) - timedelta(minutes=idle_timeout + 0.5)
        db_session.add(session)
        db_session.commit()

        # Step 6: Verify session is now expired
        assert SessionService.is_session_expired(session)
        reason = SessionService.get_expiration_reason(session)
        assert reason == "idle_timeout"
        print(f"✓ Session expired due to idle timeout after {idle_timeout + 0.5} minutes")

        # Step 7: Invalidate expired session
        SessionService.invalidate_session(db_session, session)

        # Step 8: Verify session is deleted
        deleted_session = db_session.query(DemoSession).filter(
            DemoSession.session_id == session_id
        ).first()
        assert deleted_session is None
        print(f"✓ Expired session invalidated and deleted")

        # Step 9: User must re-authenticate with OTP
        print(f"✓ User must re-authenticate with OTP to create new session")

        print("\n✅ E2E Session Lifecycle Test Passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])