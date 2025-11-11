"""Unit tests for token refund mechanism.

Tests FIX 2.2: Token refund when API fails after tokens are deducted.

Author: Lab01-MCP Team
Created: 2025-11-03
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
async def test_refund_tokens_success(token_bucket):
    """Test successful token refund."""
    mock_result = {
        "tokens_consumed": 100,
        "is_blocked": False,
    }
    token_bucket.db.execute_one.return_value = mock_result

    tokens_remaining = await token_bucket.refund_tokens("user_123", tokens_to_refund=50)

    # Tokens consumed should decrease from 150 to 100
    # So remaining = max_tokens - 100
    expected_remaining = config.DEMO_MAX_TOKENS - 100
    assert tokens_remaining == expected_remaining


@pytest.mark.asyncio
async def test_refund_tokens_multiple(token_bucket):
    """Test refunding multiple times."""
    # First deduction
    first_mock = {
        "tokens_consumed": 200,
        "is_blocked": False,
    }

    # Second refund
    second_mock = {
        "tokens_consumed": 100,
        "is_blocked": False,
    }

    token_bucket.db.execute_one.side_effect = [first_mock, second_mock]

    # Deduct 200 tokens
    await token_bucket.deduct_tokens("user_123", tokens_used=200)

    # Refund 100 tokens
    remaining = await token_bucket.refund_tokens("user_123", tokens_to_refund=100)

    expected = config.DEMO_MAX_TOKENS - 100
    assert remaining == expected


@pytest.mark.asyncio
async def test_refund_tokens_cannot_go_negative(token_bucket):
    """Test that refund cannot result in negative tokens consumed."""
    # User consumed 50 tokens
    mock_result = {
        "tokens_consumed": 0,  # After MAX(0, 50 - 100)
        "is_blocked": False,
    }
    token_bucket.db.execute_one.return_value = mock_result

    # Try to refund 100 (more than consumed)
    remaining = await token_bucket.refund_tokens("user_123", tokens_to_refund=100)

    # Tokens consumed cannot be negative
    assert remaining == config.DEMO_MAX_TOKENS


@pytest.mark.asyncio
async def test_refund_tokens_invalid_amount_negative(token_bucket):
    """Test refund with negative amount (should be ignored)."""
    remaining = await token_bucket.refund_tokens("user_123", tokens_to_refund=-50)

    # Should return max_tokens without doing anything
    assert remaining == config.DEMO_MAX_TOKENS
    token_bucket.db.execute_one.assert_not_called()


@pytest.mark.asyncio
async def test_refund_tokens_invalid_amount_zero(token_bucket):
    """Test refund with zero amount (should be ignored)."""
    remaining = await token_bucket.refund_tokens("user_123", tokens_to_refund=0)

    assert remaining == config.DEMO_MAX_TOKENS
    token_bucket.db.execute_one.assert_not_called()


@pytest.mark.asyncio
async def test_refund_tokens_auto_unblock(token_bucket):
    """Test that refund auto-unblocks user if they were blocked."""
    # User was blocked
    mock_result = {
        "tokens_consumed": 4800,  # Almost at limit
        "is_blocked": True,
    }
    token_bucket.db.execute_one.return_value = mock_result

    # Refund enough tokens to bring them below limit
    remaining = await token_bucket.refund_tokens("user_123", tokens_to_refund=1000)

    # User should be auto-unblocked
    # Check that unblock query was called
    unblock_call = token_bucket.db.execute.call_args_list[0]
    assert "is_blocked = false" in unblock_call[0][0]


@pytest.mark.asyncio
async def test_refund_tokens_no_unblock_if_still_over_quota(token_bucket):
    """Test that refund does NOT unblock if user still over quota."""
    # User is at max quota
    max_tokens = config.DEMO_MAX_TOKENS
    mock_result = {
        "tokens_consumed": max_tokens,
        "is_blocked": True,
    }
    token_bucket.db.execute_one.return_value = mock_result

    # Refund small amount
    await token_bucket.refund_tokens("user_123", tokens_to_refund=100)

    # User still at or above quota, so should NOT unblock
    # Check that execute was NOT called for unblock
    # (execute is called for the UPDATE, but not for unblock)
    token_bucket.db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_refund_tokens_user_not_found(token_bucket):
    """Test refund when user not found in database."""
    token_bucket.db.execute_one.return_value = None

    remaining = await token_bucket.refund_tokens("nonexistent_user", tokens_to_refund=100)

    assert remaining == config.DEMO_MAX_TOKENS


@pytest.mark.asyncio
async def test_refund_tokens_database_error(token_bucket):
    """Test error handling in refund_tokens."""
    token_bucket.db.execute_one.side_effect = Exception("DB Error")

    remaining = await token_bucket.refund_tokens("user_123", tokens_to_refund=100)

    # Should handle error gracefully
    assert remaining == config.DEMO_MAX_TOKENS


class TestTokenRefundIntegration:
    """Integration tests for token refund scenarios."""

    @pytest.mark.asyncio
    async def test_api_failure_refund_scenario(self, token_bucket):
        """Test complete scenario: deduct, API fails, refund."""
        user_key = "user_123"

        # Step 1: Check quota (passes)
        check_result = {
            "id": 1,
            "user_key": user_key,
            "tokens_consumed": 0,
            "requests_count": 0,
            "last_reset": datetime.now(timezone.utc),
            "is_blocked": False,
            "blocked_until": None,
        }
        token_bucket.db.execute_one.return_value = check_result

        can_proceed, remaining = await token_bucket.check_quota(
            user_key, tokens_needed=100
        )
        assert can_proceed is True

        # Step 2: Deduct tokens
        deduct_result = {
            "tokens_consumed": 250,
            "is_blocked": False,
        }
        token_bucket.db.execute_one.return_value = deduct_result

        remaining = await token_bucket.deduct_tokens(user_key, tokens_used=250)
        assert remaining == config.DEMO_MAX_TOKENS - 250

        # Step 3: API fails, refund tokens
        refund_result = {
            "tokens_consumed": 0,
            "is_blocked": False,
        }
        token_bucket.db.execute_one.return_value = refund_result

        remaining = await token_bucket.refund_tokens(user_key, tokens_to_refund=250)
        assert remaining == config.DEMO_MAX_TOKENS

    @pytest.mark.asyncio
    async def test_refund_unblocks_user(self, token_bucket):
        """Test scenario: user blocked, refund unblocks them."""
        user_key = "user_123"

        # User is blocked after consuming all tokens
        blocked_result = {
            "tokens_consumed": config.DEMO_MAX_TOKENS,
            "is_blocked": True,
        }
        token_bucket.db.execute_one.return_value = blocked_result

        # Refund significant amount
        refund_result = {
            "tokens_consumed": config.DEMO_MAX_TOKENS - 500,
            "is_blocked": True,
        }
        token_bucket.db.execute_one.return_value = refund_result

        remaining = await token_bucket.refund_tokens(user_key, tokens_to_refund=500)

        # Should trigger unblock
        unblock_call = token_bucket.db.execute.call_args_list[0]
        assert "is_blocked = false" in unblock_call[0][0]

    @pytest.mark.asyncio
    async def test_partial_refund_scenario(self, token_bucket):
        """Test scenario: partial refund of failed API call."""
        user_key = "user_123"

        # Original: 2000 tokens consumed
        # API call uses 250 tokens but fails
        # Refund only 250

        refund_result = {
            "tokens_consumed": 2000,  # After refunding 250
            "is_blocked": False,
        }
        token_bucket.db.execute_one.return_value = refund_result

        remaining = await token_bucket.refund_tokens(user_key, tokens_to_refund=250)

        expected = config.DEMO_MAX_TOKENS - 2000
        assert remaining == expected
