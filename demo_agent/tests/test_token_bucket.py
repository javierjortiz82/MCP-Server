"""Unit tests for TokenBucket rate limiting.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from demo_agent.config.settings import config
from demo_agent.rate_limiter.token_bucket import TokenBucket


@pytest.fixture
def token_bucket():
    """Create TokenBucket instance with mocked database."""
    with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_db:
        mock_db.return_value = Mock()
        bucket = TokenBucket()
        bucket.db = Mock()
        yield bucket


@pytest.mark.asyncio
async def test_check_quota_new_user(token_bucket):
    """Test check_quota for new user (not in database)."""
    token_bucket.db.execute_one.return_value = None
    token_bucket.db.execute.return_value = None

    can_proceed, tokens_remaining = await token_bucket.check_quota(
        "user_123", tokens_needed=100
    )

    assert can_proceed is True
    assert tokens_remaining == config.DEMO_MAX_TOKENS - 100
    token_bucket.db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_quota_user_with_remaining(token_bucket):
    """Test check_quota for user with remaining tokens."""
    mock_result = {
        "id": 1,
        "user_key": "user_123",
        "tokens_consumed": 1000,
        "requests_count": 5,
        "last_reset": datetime.now(timezone.utc),
        "is_blocked": False,
        "blocked_until": None,
    }
    token_bucket.db.execute_one.return_value = mock_result

    can_proceed, tokens_remaining = await token_bucket.check_quota(
        "user_123", tokens_needed=100
    )

    assert can_proceed is True
    expected_remaining = config.DEMO_MAX_TOKENS - 1000 - 100
    assert tokens_remaining == expected_remaining


@pytest.mark.asyncio
async def test_check_quota_quota_exhausted(token_bucket):
    """Test check_quota when quota is exhausted."""
    mock_result = {
        "id": 1,
        "user_key": "user_123",
        "tokens_consumed": config.DEMO_MAX_TOKENS - 50,
        "requests_count": 100,
        "last_reset": datetime.now(timezone.utc),
        "is_blocked": False,
        "blocked_until": None,
    }
    token_bucket.db.execute_one.return_value = mock_result

    can_proceed, tokens_remaining = await token_bucket.check_quota(
        "user_123", tokens_needed=100
    )

    assert can_proceed is False
    assert tokens_remaining == 0  # Max of 50 means 0 remaining after 100 request


@pytest.mark.asyncio
async def test_check_quota_auto_reset_daily(token_bucket):
    """Test auto-reset of quota at UTC midnight."""
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    mock_result = {
        "id": 1,
        "user_key": "user_123",
        "tokens_consumed": config.DEMO_MAX_TOKENS,
        "requests_count": 50,
        "last_reset": yesterday,
        "is_blocked": False,
        "blocked_until": None,
    }
    token_bucket.db.execute_one.return_value = mock_result

    can_proceed, tokens_remaining = await token_bucket.check_quota(
        "user_123", tokens_needed=100
    )

    assert can_proceed is True
    assert tokens_remaining == config.DEMO_MAX_TOKENS - 100
    # Verify reset query was called
    reset_call = token_bucket.db.execute.call_args_list[0]
    assert "tokens_consumed = 0" in reset_call[0][0]


@pytest.mark.asyncio
async def test_check_quota_blocked_user_active(token_bucket):
    """Test check_quota for actively blocked user."""
    future = datetime.now(timezone.utc) + timedelta(hours=12)
    mock_result = {
        "id": 1,
        "user_key": "user_123",
        "tokens_consumed": config.DEMO_MAX_TOKENS,
        "requests_count": 50,
        "last_reset": datetime.now(timezone.utc),
        "is_blocked": True,
        "blocked_until": future,
    }
    token_bucket.db.execute_one.return_value = mock_result

    can_proceed, tokens_remaining = await token_bucket.check_quota(
        "user_123", tokens_needed=100
    )

    assert can_proceed is False


@pytest.mark.asyncio
async def test_check_quota_blocked_user_expired(token_bucket):
    """Test auto-unblock when block expires."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    mock_result = {
        "id": 1,
        "user_key": "user_123",
        "tokens_consumed": config.DEMO_MAX_TOKENS,
        "requests_count": 50,
        "last_reset": datetime.now(timezone.utc),
        "is_blocked": True,
        "blocked_until": past,
    }
    token_bucket.db.execute_one.return_value = mock_result

    can_proceed, tokens_remaining = await token_bucket.check_quota(
        "user_123", tokens_needed=100
    )

    # Block is expired so auto-unblock happens, but quota still exhausted
    # So can_proceed should be False
    assert can_proceed is False
    # Verify unblock query was called
    unblock_call = token_bucket.db.execute.call_args_list[0]
    assert "is_blocked = false" in unblock_call[0][0]


@pytest.mark.asyncio
async def test_deduct_tokens_success(token_bucket):
    """Test successful token deduction."""
    mock_result = {
        "tokens_consumed": 1500,
        "is_blocked": False,
    }
    token_bucket.db.execute_one.return_value = mock_result

    tokens_remaining = await token_bucket.deduct_tokens("user_123", tokens_used=500)

    expected_remaining = config.DEMO_MAX_TOKENS - 1500
    assert tokens_remaining == expected_remaining


@pytest.mark.asyncio
async def test_deduct_tokens_quota_exceeded(token_bucket):
    """Test token deduction triggers blocking."""
    mock_result = {
        "tokens_consumed": config.DEMO_MAX_TOKENS + 100,
        "is_blocked": False,
    }
    token_bucket.db.execute_one.return_value = mock_result

    tokens_remaining = await token_bucket.deduct_tokens("user_123", tokens_used=500)

    assert tokens_remaining <= 0
    # Verify block query was called (first execute call)
    block_call = token_bucket.db.execute.call_args_list[0]
    assert "is_blocked = true" in block_call[0][0]


@pytest.mark.asyncio
async def test_deduct_tokens_user_not_found(token_bucket):
    """Test deduction when user not found."""
    token_bucket.db.execute_one.return_value = None

    tokens_remaining = await token_bucket.deduct_tokens(
        "nonexistent_user", tokens_used=500
    )

    assert tokens_remaining == config.DEMO_MAX_TOKENS


@pytest.mark.asyncio
async def test_get_quota_status_new_user(token_bucket):
    """Test quota status for new user."""
    token_bucket.db.execute_one.return_value = None

    status = await token_bucket.get_quota_status("user_123")

    assert status["tokens_used"] == 0
    assert status["tokens_remaining"] == config.DEMO_MAX_TOKENS
    assert status["percentage_used"] == 0
    assert status["is_blocked"] is False
    assert status["blocked_until"] is None


@pytest.mark.asyncio
async def test_get_quota_status_with_consumption(token_bucket):
    """Test quota status with token consumption."""
    mock_result = {
        "tokens_consumed": 2500,
        "requests_count": 10,
        "is_blocked": False,
        "blocked_until": None,
        "last_reset": datetime.now(timezone.utc),
    }
    token_bucket.db.execute_one.return_value = mock_result

    status = await token_bucket.get_quota_status("user_123")

    assert status["tokens_used"] == 2500
    assert status["tokens_remaining"] == config.DEMO_MAX_TOKENS - 2500
    assert status["percentage_used"] == 50
    assert status["requests_count"] == 10


@pytest.mark.asyncio
async def test_get_quota_status_percentage_calculation(token_bucket):
    """Test percentage calculation accuracy."""
    mock_result = {
        "tokens_consumed": 4250,  # 85%
        "requests_count": 1,
        "is_blocked": False,
        "blocked_until": None,
        "last_reset": datetime.now(timezone.utc),
    }
    token_bucket.db.execute_one.return_value = mock_result

    status = await token_bucket.get_quota_status("user_123")

    assert status["percentage_used"] == 85


@pytest.mark.asyncio
async def test_unblock_user(token_bucket):
    """Test admin unblock operation."""
    token_bucket.db.execute.return_value = None

    result = await token_bucket.unblock_user("user_123")

    assert result is True
    token_bucket.db.execute.assert_called_once()
    call_args = token_bucket.db.execute.call_args[0][0]
    assert "is_blocked = false" in call_args


@pytest.mark.asyncio
async def test_unblock_user_error(token_bucket):
    """Test unblock operation error handling."""
    token_bucket.db.execute.side_effect = Exception("DB error")

    result = await token_bucket.unblock_user("user_123")

    assert result is False


def test_next_utc_midnight():
    """Test UTC midnight calculation."""
    midnight = TokenBucket._next_utc_midnight()

    # Parse the ISO string
    next_midnight = datetime.fromisoformat(midnight)

    # Should be in the future
    assert next_midnight > datetime.now(timezone.utc)

    # Should be at midnight (00:00:00)
    assert next_midnight.hour == 0
    assert next_midnight.minute == 0
    assert next_midnight.second == 0


@pytest.mark.asyncio
async def test_error_handling_check_quota(token_bucket):
    """Test error handling in check_quota."""
    token_bucket.db.execute_one.side_effect = Exception("DB connection error")

    can_proceed, tokens_remaining = await token_bucket.check_quota(
        "user_123", tokens_needed=100
    )

    # Should fail open on error
    assert can_proceed is True
    assert tokens_remaining == config.DEMO_MAX_TOKENS


@pytest.mark.asyncio
async def test_error_handling_deduct_tokens(token_bucket):
    """Test error handling in deduct_tokens."""
    token_bucket.db.execute_one.side_effect = Exception("DB connection error")

    tokens_remaining = await token_bucket.deduct_tokens("user_123", tokens_used=100)

    assert tokens_remaining == config.DEMO_MAX_TOKENS
