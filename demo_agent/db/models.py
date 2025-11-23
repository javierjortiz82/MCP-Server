"""SQLAlchemy ORM models for Demo Agent database tables.

Defines models for:
- DemoUsage: Token-bucket rate limiting state per user
- DemoAuditLog: Immutable audit trail for security analysis
- DemoSession: Session metadata and engagement tracking

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.ext.declarative import declarative_base

# Create base class for all ORM models
Base = declarative_base()


class DemoUsage(Base):
    """Token-bucket rate limiting state per user.

    Tracks token consumption, quota, and blocking state for each user.
    Updated atomically to prevent race conditions.

    Attributes:
        id: Primary key (auto-incrementing)
        user_key: Unique identifier (user_id | session_id | fingerprint)
        tokens_consumed: Cumulative tokens used in current day
        requests_count: Number of API requests in current day
        last_reset: When daily quota was last reset (UTC midnight)
        is_blocked: Whether user is currently blocked
        blocked_until: When the block expires (or None)
        created_at: Record creation timestamp
        updated_at: Last record update timestamp
    """

    __tablename__ = "demo_usage"
    __table_args__ = {"schema": None}  # Schema set dynamically via config

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_key = Column(String(255), unique=True, nullable=False, index=True)
    tokens_consumed = Column(Integer, nullable=False, default=0)
    requests_count = Column(Integer, nullable=False, default=0)
    last_reset = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    is_blocked = Column(Boolean, nullable=False, default=False)
    blocked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        """String representation of DemoUsage record."""
        return (
            f"<DemoUsage(user_key={self.user_key!r}, "
            f"tokens_consumed={self.tokens_consumed}, "
            f"is_blocked={self.is_blocked})>"
        )

    def is_quota_exhausted(self, max_tokens: int) -> bool:
        """Check if user has exhausted daily quota.

        Args:
            max_tokens: Maximum tokens allowed per day

        Returns:
            bool: True if tokens_consumed >= max_tokens
        """
        return self.tokens_consumed >= max_tokens

    def is_block_expired(self) -> bool:
        """Check if user's block has expired.

        Returns:
            bool: True if blocked_until is in the past (block expired)
        """
        if not self.is_blocked or not self.blocked_until:
            return False
        return self.blocked_until <= datetime.now(timezone.utc)

    def needs_reset(self) -> bool:
        """Check if daily quota needs reset (past UTC midnight).

        Returns:
            bool: True if last_reset is before current UTC day
        """
        now = datetime.now(timezone.utc)
        # Reset if last_reset was yesterday or earlier
        return self.last_reset.date() < now.date()


class DemoAuditLog(Base):
    """Immutable audit trail for security analysis and debugging.

    Records all demo API requests for auditing, abuse detection,
    and troubleshooting rate-limiting issues.

    Attributes:
        id: Primary key (auto-incrementing)
        user_key: User identifier (or None for unauthenticated)
        ip_address: Client IP address (IPv4 or IPv6)
        client_fingerprint: Device fingerprint hash
        request_input: User's query (first 1000 chars, truncated)
        response_length: Length of response in characters
        tokens_used: Tokens consumed by this request
        is_blocked: Whether request was rejected
        block_reason: Why request was blocked (if applicable)
        abuse_score: Abuse likelihood (0.0-1.0)
        action_taken: System action taken (allowed, blocked, etc.)
        user_agent: HTTP User-Agent header
        created_at: Request timestamp (UTC)
    """

    __tablename__ = "demo_audit_log"
    __table_args__ = {"schema": None}  # Schema set dynamically via config

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_key = Column(String(255), nullable=True, index=True)
    ip_address = Column(INET, nullable=True, index=True)
    client_fingerprint = Column(String(255), nullable=True, index=True)
    request_input = Column(Text, nullable=True)
    response_length = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    is_blocked = Column(Boolean, nullable=False, default=False)
    block_reason = Column(String(255), nullable=True)
    abuse_score = Column(Float, nullable=False, default=0.0)
    action_taken = Column(String(50), nullable=False, default="allowed")
    user_agent = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def __repr__(self) -> str:
        """String representation of DemoAuditLog record."""
        return (
            f"<DemoAuditLog(user_key={self.user_key!r}, "
            f"ip_address={self.ip_address}, "
            f"abuse_score={self.abuse_score}, "
            f"action_taken={self.action_taken!r})>"
        )

    @property
    def is_suspicious(self, threshold: float = 0.7) -> bool:
        """Check if request is flagged as suspicious.

        Args:
            threshold: Abuse score threshold (default 0.7)

        Returns:
            bool: True if abuse_score >= threshold
        """
        return self.abuse_score >= threshold

    @property
    def blocked_reason_readable(self) -> str | None:
        """Get human-readable block reason.

        Returns:
            Friendly description of block reason or None
        """
        reasons = {
            "quota_exceeded": "Demo daily token limit exceeded",
            "rate_limit_ip": "IP rate limit exceeded",
            "rate_limit_user": "User rate limit exceeded",
            "suspicious_behavior": "Suspicious behavior detected",
            "captcha_required": "CAPTCHA verification required",
        }
        return reasons.get(self.block_reason) if self.block_reason else None


class DemoSession(Base):
    """Session metadata and engagement tracking.

    Stores session information for resuming sessions and analytics.
    Allows tracking user engagement and language preferences.

    Attributes:
        id: Primary key (UUID)
        user_id: Authenticated user ID (or None for anonymous)
        session_id: Session token (generated by client)
        ip_address: Client IP at session creation
        user_agent: HTTP User-Agent at session creation
        language: Language preference (es | en)
        total_tokens_used: Cumulative tokens in this session
        total_requests: Number of requests in this session
        created_at: Session start timestamp
        last_activity_at: Last request timestamp (for session timeout)
    """

    __tablename__ = "demo_sessions"
    __table_args__ = {"schema": None}  # Schema set dynamically via config

    id = Column(String(36), primary_key=True)  # UUID as string
    user_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, unique=True, index=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    language = Column(String(10), nullable=False, default="es")
    total_tokens_used = Column(Integer, nullable=False, default=0)
    total_requests = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    last_activity_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        """String representation of DemoSession record."""
        return (
            f"<DemoSession(session_id={self.session_id!r}, "
            f"language={self.language}, "
            f"total_tokens_used={self.total_tokens_used})>"
        )

    @property
    def session_duration(self) -> int | None:
        """Calculate session duration in seconds.

        Returns:
            Seconds since session creation (or None)
        """
        if not self.created_at:
            return None
        now = datetime.now(timezone.utc)
        delta = now - self.created_at
        return int(delta.total_seconds())

    @property
    def is_active(self, timeout_minutes: int = 30) -> bool:
        """Check if session is still active (within timeout window).

        Args:
            timeout_minutes: Session timeout in minutes (default 30)

        Returns:
            bool: True if last activity is within timeout window
        """
        now = datetime.now(timezone.utc)
        if not self.last_activity_at:
            return False
        elapsed_seconds = (now - self.last_activity_at).total_seconds()
        return elapsed_seconds < (timeout_minutes * 60)

    def is_expired(self, ttl_minutes: int, idle_timeout_minutes: int, absolute_timeout_minutes: int) -> bool:
        """Check if session has expired based on multiple timeout criteria.

        Implements three-tier expiration logic (OWASP standard):
        1. Idle timeout: Expires if inactive for idle_timeout_minutes
        2. TTL (Time-To-Live): Expires if active for ttl_minutes total
        3. Absolute timeout: Expires regardless of activity after absolute_timeout_minutes

        Args:
            ttl_minutes: Total session lifetime in minutes
            idle_timeout_minutes: Inactivity timeout in minutes
            absolute_timeout_minutes: Absolute max lifetime in minutes

        Returns:
            bool: True if any expiration criterion is met
        """
        now = datetime.now(timezone.utc)

        # Check idle timeout (inactivity)
        if self.last_activity_at:
            idle_seconds = (now - self.last_activity_at).total_seconds()
            if idle_seconds >= (idle_timeout_minutes * 60):
                return True  # Expired due to inactivity

        # Check TTL (time since creation, with activity reset)
        if self.created_at:
            ttl_seconds = (now - self.created_at).total_seconds()
            if ttl_seconds >= (ttl_minutes * 60):
                return True  # Expired due to TTL

        # Check absolute timeout (never expires before this, regardless of activity)
        if self.created_at:
            absolute_seconds = (now - self.created_at).total_seconds()
            if absolute_seconds >= (absolute_timeout_minutes * 60):
                return True  # Expired due to absolute timeout

        return False

    def get_expiration_reason(self, ttl_minutes: int, idle_timeout_minutes: int, absolute_timeout_minutes: int) -> str | None:
        """Get human-readable reason for session expiration.

        Returns:
            str: Expiration reason ('idle_timeout', 'ttl', 'absolute_timeout') or None if not expired
        """
        now = datetime.now(timezone.utc)

        # Check idle timeout first (most common)
        if self.last_activity_at:
            idle_seconds = (now - self.last_activity_at).total_seconds()
            if idle_seconds >= (idle_timeout_minutes * 60):
                return "idle_timeout"

        # Check TTL
        if self.created_at:
            ttl_seconds = (now - self.created_at).total_seconds()
            if ttl_seconds >= (ttl_minutes * 60):
                return "ttl"

        # Check absolute timeout
        if self.created_at:
            absolute_seconds = (now - self.created_at).total_seconds()
            if absolute_seconds >= (absolute_timeout_minutes * 60):
                return "absolute_timeout"

        return None

    def update_activity(self) -> None:
        """Update session's last activity timestamp to current time.

        Called on each request to reset idle timeout counter.
        """
        self.last_activity_at = datetime.now(timezone.utc)

    def avg_tokens_per_request(self) -> float:
        """Calculate average tokens consumed per request.

        Returns:
            float: Average tokens per request (or 0 if no requests)
        """
        if self.total_requests == 0:
            return 0.0
        return self.total_tokens_used / self.total_requests
