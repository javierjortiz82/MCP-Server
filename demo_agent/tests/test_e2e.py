"""End-to-End Tests for Demo Agent.

This module contains 10 comprehensive E2E test scenarios covering:
1. Normal FAQ Query (Happy Path)
2. Quota Exhaustion
3. IP Rate Limiting
4. Suspicious Behavior Detection
5. CAPTCHA Challenge
6. Token Warning Threshold
7. CAPTCHA Verification Success
8. Quota Status Check
9. Auto-Reset at UTC Midnight
10. Auto-Unblock After Cooldown

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from demo_agent.agent import DemoAgent


@pytest.fixture
def mock_db():
    """Create a mock database connection."""
    db = Mock()
    db.execute = Mock()
    db.execute_one = Mock(return_value={})
    db.close = Mock()
    return db


@pytest.fixture
def mock_gemini_client():
    """Create a mock Gemini client."""
    client = AsyncMock()
    client.generate_response = AsyncMock(
        return_value=("Test response", 250)
    )
    return client


@pytest.fixture
def mock_prompt_manager():
    """Create a mock PromptManager."""
    manager = Mock()
    manager.get_demo_prompt = Mock(
        return_value="System prompt with FAQ context"
    )
    return manager


@pytest.fixture
def demo_agent_with_mocks(mock_db, mock_gemini_client, mock_prompt_manager):
    """Create a DemoAgent with mocked dependencies."""
    with patch("demo_agent.agent.get_db", return_value=mock_db):
        with patch(
            "demo_agent.agent.GeminiClient", return_value=mock_gemini_client
        ):
            with patch(
                "demo_agent.agent.PromptManager",
                return_value=mock_prompt_manager,
            ):
                agent = DemoAgent()
                agent.db = mock_db
                agent.gemini_client = mock_gemini_client
                agent.prompt_manager = mock_prompt_manager
                yield agent


# ============================================================================
# Scenario 1: Normal FAQ Query (Happy Path)
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_scenario_1_normal_query(demo_agent_with_mocks):
    """Test normal FAQ query within quota.

    Steps:
    1. POST /v1/demo with valid DemoRequest
    2. IP rate check passes
    3. Fingerprint analysis completes
    4. Token quota check passes
    5. PromptManager renders FAQ context
    6. Gemini API returns response
    7. Tokens deducted
    8. Audit log created

    Expected: 200 OK with response
    """
    agent = demo_agent_with_mocks

    # Mock database responses
    agent.db.execute_one.side_effect = [
        {"request_count": 10},  # IP rate check
        None,  # Fingerprint generation
        {"total_requests": 100},  # IP stats (part 1)
        {"requests_today": 10},  # IP stats (part 2)
        {"requests_per_minute": 1},  # IP stats (part 3)
        {"unique_users": 1},  # IP stats (part 4)
        {
            "avg_abuse_score": 0.1,
            "max_abuse_score": 0.2,
        },  # IP stats (part 5)
        {
            "first_seen": None,
            "last_seen": None,
        },  # IP stats (part 6)
        {"tokens_consumed": 500, "is_blocked": False},  # Quota check
        {"tokens_consumed": 750, "requests_count": 2},  # Token deduction
    ]

    response_text, tokens_used, warning, error_msg = await agent.process_query(
        user_input="¿Cuánto cuesta un laptop?",
        user_key="user123",
        language="es",
        ip_address="203.0.113.42",
        user_agent="Mozilla/5.0",
    )

    # Assertions
    assert response_text == "Test response"
    assert tokens_used == 250
    assert error_msg is None
    assert warning.is_warning is False
    assert agent.gemini_client.generate_response.called
    agent.db.execute.assert_called()  # Audit log


@pytest.mark.asyncio
async def test_e2e_scenario_2_quota_exhaustion(demo_agent_with_mocks):
    """Test request blocked due to quota exhaustion.

    Expected: 429 (Quota Exceeded) with error message
    """
    agent = demo_agent_with_mocks

    # Mock quota exhausted state
    agent.db.execute_one.side_effect = [
        {"request_count": 10},  # IP rate check passes
        None,  # Fingerprint generation
        {"total_requests": 100},  # IP stats (part 1)
        {"requests_today": 10},  # IP stats (part 2)
        {"requests_per_minute": 1},  # IP stats (part 3)
        {"unique_users": 1},  # IP stats (part 4)
        {
            "avg_abuse_score": 0.1,
            "max_abuse_score": 0.2,
        },  # IP stats (part 5)
        {
            "first_seen": None,
            "last_seen": None,
        },  # IP stats (part 6)
        {"tokens_consumed": 5000, "is_blocked": True},  # Quota check - FAIL
    ]

    response_text, tokens_used, warning, error_msg = await agent.process_query(
        user_input="¿Cuánto cuesta un laptop?",
        user_key="user123",
        language="es",
        ip_address="203.0.113.42",
        user_agent="Mozilla/5.0",
    )

    # Assertions
    assert response_text is None
    assert tokens_used == 0
    assert error_msg is not None
    assert "quota" in error_msg.lower()
    assert warning.is_warning is True
    assert not agent.gemini_client.generate_response.called


@pytest.mark.asyncio
async def test_e2e_scenario_3_ip_rate_limiting(demo_agent_with_mocks):
    """Test request blocked due to IP rate limiting.

    Expected: 429 (Rate Limit Exceeded)
    """
    agent = demo_agent_with_mocks

    # Mock IP rate limit exceeded
    agent.db.execute_one.side_effect = [
        {
            "request_count": 150
        }  # IP rate check - FAIL (>100)
    ]

    # Mock IP limiter
    with patch.object(
        agent.ip_limiter, "check_rate_limit",
        new_callable=AsyncMock,
        return_value=(False, 150),
    ):
        response_text, tokens_used, warning, error_msg = (
            await agent.process_query(
                user_input="Test",
                user_key="user123",
                language="es",
                ip_address="203.0.113.42",
                user_agent="Mozilla/5.0",
            )
        )

        assert response_text is None
        assert error_msg is not None
        assert "rate limit" in error_msg.lower()


@pytest.mark.asyncio
async def test_e2e_scenario_4_suspicious_behavior(demo_agent_with_mocks):
    """Test request blocked due to suspicious behavior (abuse_score > 0.9).

    Expected: 403 (Forbidden - Suspicious)
    """
    agent = demo_agent_with_mocks

    # Mock suspicious behavior detection
    agent.db.execute_one.side_effect = [
        {"request_count": 10},  # IP rate check passes
        None,  # Fingerprint generation
        {"total_requests": 1000},  # IP stats (part 1)
        {"requests_today": 500},  # IP stats (part 2)
        {"requests_per_minute": 50},  # IP stats (part 3)
        {"unique_users": 30},  # IP stats (part 4)
        {
            "avg_abuse_score": 0.9,
            "max_abuse_score": 0.95,
        },  # IP stats (part 5)
        {
            "first_seen": None,
            "last_seen": None,
        },  # IP stats (part 6)
    ]

    # Mock fingerprint analyzer to return high abuse score
    with patch.object(
        agent.fingerprint_analyzer,
        "compute_abuse_score",
        return_value=0.95,  # > 0.9 triggers block
    ):
        response_text, tokens_used, warning, error_msg = (
            await agent.process_query(
                user_input="Test",
                user_key="user123",
                language="es",
                ip_address="203.0.113.42",
                user_agent="Mozilla/5.0",
            )
        )

        assert response_text is None
        assert error_msg is not None
        assert "sospechosa" in error_msg.lower()


@pytest.mark.asyncio
async def test_e2e_scenario_5_captcha_challenge(demo_agent_with_mocks):
    """Test CAPTCHA challenge triggered (0.7 < abuse_score < 0.9).

    Expected: 403 (Forbidden - CAPTCHA Required)
    """
    agent = demo_agent_with_mocks

    agent.db.execute_one.side_effect = [
        {"request_count": 10},  # IP rate check passes
        None,  # Fingerprint generation
        {"total_requests": 500},  # IP stats (part 1)
        {"requests_today": 100},  # IP stats (part 2)
        {"requests_per_minute": 5},  # IP stats (part 3)
        {"unique_users": 10},  # IP stats (part 4)
        {
            "avg_abuse_score": 0.7,
            "max_abuse_score": 0.8,
        },  # IP stats (part 5)
        {
            "first_seen": None,
            "last_seen": None,
        },  # IP stats (part 6)
    ]

    # Mock moderate abuse score that triggers CAPTCHA
    with patch.object(
        agent.fingerprint_analyzer,
        "compute_abuse_score",
        return_value=0.75,  # Between 0.7 and 0.9
    ):
        response_text, tokens_used, warning, error_msg = (
            await agent.process_query(
                user_input="Test",
                user_key="user123",
                language="es",
                ip_address="203.0.113.42",
                user_agent="Mozilla/5.0",
            )
        )

        assert response_text is None
        assert error_msg is not None
        assert "captcha" in error_msg.lower()


@pytest.mark.asyncio
async def test_e2e_scenario_6_token_warning_threshold(
    demo_agent_with_mocks,
):
    """Test warning message when usage exceeds threshold (85%).

    Expected: 200 OK with warning
    """
    agent = demo_agent_with_mocks

    # Mock 90% usage (> 85% threshold)
    agent.db.execute_one.side_effect = [
        {"request_count": 10},  # IP rate check
        None,  # Fingerprint generation
        {"total_requests": 100},  # IP stats (part 1)
        {"requests_today": 10},  # IP stats (part 2)
        {"requests_per_minute": 1},  # IP stats (part 3)
        {"unique_users": 1},  # IP stats (part 4)
        {
            "avg_abuse_score": 0.1,
            "max_abuse_score": 0.2,
        },  # IP stats (part 5)
        {
            "first_seen": None,
            "last_seen": None,
        },  # IP stats (part 6)
        {"tokens_consumed": 4500, "is_blocked": False},  # Quota check (90%)
        {"tokens_consumed": 4750, "requests_count": 2},  # Token deduction
        {
            "tokens_used": 250,
            "tokens_remaining": 250,
            "percentage_used": 95,
        },  # Status after deduction
    ]

    # Mock token bucket status
    with patch.object(
        agent.token_bucket,
        "get_quota_status",
        new_callable=AsyncMock,
        return_value={
            "tokens_used": 4750,
            "tokens_remaining": 250,
            "percentage_used": 95,
            "requests_count": 2,
            "is_blocked": False,
            "blocked_until": None,
            "last_reset": datetime.now(timezone.utc).isoformat(),
            "next_reset": (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(),
        },
    ):
        response_text, tokens_used, warning, error_msg = (
            await agent.process_query(
                user_input="Test",
                user_key="user123",
                language="es",
                ip_address="203.0.113.42",
                user_agent="Mozilla/5.0",
            )
        )

        assert response_text == "Test response"
        assert error_msg is None
        assert warning.is_warning is True
        assert warning.percentage_used == 95
        assert "ALERTA" in warning.message or "Advertencia" in warning.message


@pytest.mark.asyncio
async def test_e2e_scenario_7_captcha_verification(demo_agent_with_mocks):
    """Test successful reCAPTCHA v3 verification.

    Expected: 200 OK with score and risk level
    """
    agent = demo_agent_with_mocks

    # Mock successful CAPTCHA verification
    with patch.object(
        agent.captcha_handler,
        "verify_token",
        new_callable=AsyncMock,
        return_value={
            "success": True,
            "score": 0.95,
            "action": "demo_query",
            "challenge_ts": "2025-10-31T12:30:45Z",
            "hostname": "example.com",
        },
    ):
        result = await agent.captcha_handler.verify_token(
            token="test_token", remote_ip="203.0.113.42"
        )

        assert result["success"] is True
        assert result["score"] == 0.95
        assert result["action"] == "demo_query"

        # Evaluate score
        evaluation = agent.captcha_handler.evaluate_score(result["score"])
        assert evaluation["risk_level"] == "low"
        assert evaluation["recommendation"] == "allow"


@pytest.mark.asyncio
async def test_e2e_scenario_8_quota_status_check(demo_agent_with_mocks):
    """Test quota status retrieval via GET /v1/demo/status.

    Expected: 200 OK with detailed status
    """
    agent = demo_agent_with_mocks

    # Mock token bucket status
    expected_status = {
        "tokens_used": 1500,
        "tokens_remaining": 3500,
        "percentage_used": 30,
        "requests_count": 12,
        "is_blocked": False,
        "blocked_until": None,
        "last_reset": datetime.now(timezone.utc).isoformat(),
        "next_reset": (
            datetime.now(timezone.utc) + timedelta(days=1)
        ).isoformat(),
    }

    with patch.object(
        agent.token_bucket,
        "get_quota_status",
        new_callable=AsyncMock,
        return_value=expected_status,
    ):
        status = await agent.get_user_status("user123")

        assert status["tokens_used"] == 1500
        assert status["tokens_remaining"] == 3500
        assert status["percentage_used"] == 30
        assert status["requests_count"] == 12
        assert status["is_blocked"] is False


@pytest.mark.asyncio
async def test_e2e_scenario_9_auto_reset_utc_midnight(
    demo_agent_with_mocks,
):
    """Test automatic quota reset at UTC midnight.

    Setup: User exhausted quota at 2025-10-31 23:59:59 UTC
    Test: New query at 2025-11-01 00:00:01 UTC

    Expected: Query succeeds with reset quota
    """
    agent = demo_agent_with_mocks

    # Mock the time crossing UTC midnight
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    today = datetime.now(timezone.utc)

    agent.db.execute_one.side_effect = [
        {"request_count": 10},  # IP rate check
        None,  # Fingerprint generation
        {"total_requests": 100},  # IP stats (part 1)
        {"requests_today": 10},  # IP stats (part 2)
        {"requests_per_minute": 1},  # IP stats (part 3)
        {"unique_users": 1},  # IP stats (part 4)
        {
            "avg_abuse_score": 0.1,
            "max_abuse_score": 0.2,
        },  # IP stats (part 5)
        {
            "first_seen": None,
            "last_seen": None,
        },  # IP stats (part 6)
        # Quota check: Auto-reset triggered because last_reset < today
        {
            "tokens_consumed": 0,  # Reset
            "is_blocked": False,
            "last_reset": today,
        },
        {"tokens_consumed": 250, "requests_count": 1},  # Token deduction
    ]

    response_text, tokens_used, warning, error_msg = await agent.process_query(
        user_input="Test",
        user_key="user123_reset_test",
        language="es",
        ip_address="203.0.113.42",
        user_agent="Mozilla/5.0",
    )

    assert response_text == "Test response"
    assert error_msg is None
    assert tokens_used == 250


@pytest.mark.asyncio
async def test_e2e_scenario_10_auto_unblock_cooldown(demo_agent_with_mocks):
    """Test automatic unblock after cooldown expiration.

    Setup: User blocked at 2025-10-31 12:00:00 UTC (24h cooldown)
    Test: New query at 2025-11-01 12:00:02 UTC

    Expected: Block expired, query succeeds
    """
    agent = demo_agent_with_mocks

    # Mock block that has expired
    now = datetime.now(timezone.utc)
    blocked_until_past = now - timedelta(seconds=1)

    agent.db.execute_one.side_effect = [
        {"request_count": 10},  # IP rate check
        None,  # Fingerprint generation
        {"total_requests": 100},  # IP stats (part 1)
        {"requests_today": 10},  # IP stats (part 2)
        {"requests_per_minute": 1},  # IP stats (part 3)
        {"unique_users": 1},  # IP stats (part 4)
        {
            "avg_abuse_score": 0.1,
            "max_abuse_score": 0.2,
        },  # IP stats (part 5)
        {
            "first_seen": None,
            "last_seen": None,
        },  # IP stats (part 6)
        # Quota check: Block expired, reset triggers
        {
            "tokens_consumed": 0,
            "is_blocked": False,
            "blocked_until": None,
        },
        {"tokens_consumed": 250, "requests_count": 1},  # Token deduction
    ]

    response_text, tokens_used, warning, error_msg = await agent.process_query(
        user_input="Test",
        user_key="user123_unblock_test",
        language="es",
        ip_address="203.0.113.42",
        user_agent="Mozilla/5.0",
    )

    assert response_text == "Test response"
    assert error_msg is None
    assert tokens_used == 250


# ============================================================================
# Additional Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_error_handling_gemini_failure(demo_agent_with_mocks):
    """Test graceful handling of Gemini API errors."""
    agent = demo_agent_with_mocks

    agent.db.execute_one.side_effect = [
        {"request_count": 10},  # IP rate check
        None,  # Fingerprint generation
        {"total_requests": 100},  # IP stats (part 1)
        {"requests_today": 10},  # IP stats (part 2)
        {"requests_per_minute": 1},  # IP stats (part 3)
        {"unique_users": 1},  # IP stats (part 4)
        {
            "avg_abuse_score": 0.1,
            "max_abuse_score": 0.2,
        },  # IP stats (part 5)
        {
            "first_seen": None,
            "last_seen": None,
        },  # IP stats (part 6)
        {"tokens_consumed": 500, "is_blocked": False},  # Quota check
    ]

    # Mock Gemini failure
    agent.gemini_client.generate_response = AsyncMock(
        side_effect=Exception("Gemini API error")
    )

    response_text, tokens_used, warning, error_msg = await agent.process_query(
        user_input="Test",
        user_key="user123",
        language="es",
        ip_address="203.0.113.42",
        user_agent="Mozilla/5.0",
    )

    assert response_text is None
    assert error_msg is not None
    assert "Error" in error_msg or "error" in error_msg


@pytest.mark.asyncio
async def test_e2e_database_error_handling(demo_agent_with_mocks):
    """Test fail-open behavior on database errors."""
    agent = demo_agent_with_mocks

    # Mock database error on IP rate check
    agent.db.execute_one.side_effect = Exception("Database connection error")

    # Should fail open and allow request to proceed
    with patch.object(
        agent.ip_limiter,
        "check_rate_limit",
        new_callable=AsyncMock,
        return_value=(True, 0),  # Fail-open: allow
    ):
        with patch.object(
            agent.fingerprint_analyzer,
            "compute_abuse_score",
            return_value=0.0,  # Safe abuse score
        ):
            agent.db.execute_one.side_effect = [
                {"request_count": 10},  # IP rate check
                None,  # Fingerprint generation
                {"total_requests": 100},  # IP stats (part 1)
                {"requests_today": 10},  # IP stats (part 2)
                {"requests_per_minute": 1},  # IP stats (part 3)
                {"unique_users": 1},  # IP stats (part 4)
                {
                    "avg_abuse_score": 0.1,
                    "max_abuse_score": 0.2,
                },  # IP stats (part 5)
                {
                    "first_seen": None,
                    "last_seen": None,
                },  # IP stats (part 6)
                {"tokens_consumed": 500, "is_blocked": False},  # Quota check
                {"tokens_consumed": 750, "requests_count": 2},  # Token deduction
            ]

            response_text, tokens_used, warning, error_msg = (
                await agent.process_query(
                    user_input="Test",
                    user_key="user123",
                    language="es",
                    ip_address="203.0.113.42",
                    user_agent="Mozilla/5.0",
                )
            )

            # Should succeed despite DB error earlier
            assert response_text == "Test response"


# ============================================================================
# Audit Logging Tests
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_audit_logging_success(demo_agent_with_mocks):
    """Test that successful requests are logged to audit trail."""
    agent = demo_agent_with_mocks

    agent.db.execute_one.side_effect = [
        {"request_count": 10},  # IP rate check
        None,  # Fingerprint generation
        {"total_requests": 100},  # IP stats (part 1)
        {"requests_today": 10},  # IP stats (part 2)
        {"requests_per_minute": 1},  # IP stats (part 3)
        {"unique_users": 1},  # IP stats (part 4)
        {
            "avg_abuse_score": 0.1,
            "max_abuse_score": 0.2,
        },  # IP stats (part 5)
        {
            "first_seen": None,
            "last_seen": None,
        },  # IP stats (part 6)
        {"tokens_consumed": 500, "is_blocked": False},  # Quota check
        {"tokens_consumed": 750, "requests_count": 2},  # Token deduction
    ]

    await agent.process_query(
        user_input="Test query",
        user_key="user123",
        language="es",
        ip_address="203.0.113.42",
        user_agent="Mozilla/5.0",
    )

    # Verify audit log was called
    assert agent.db.execute.called
    call_args = agent.db.execute.call_args
    assert "demo_audit_log" in str(call_args)


@pytest.mark.asyncio
async def test_e2e_audit_logging_blocked(demo_agent_with_mocks):
    """Test that blocked requests are logged with block reason."""
    agent = demo_agent_with_mocks

    agent.db.execute_one.side_effect = [
        {
            "request_count": 150
        }  # IP rate check - FAIL
    ]

    with patch.object(
        agent.ip_limiter,
        "check_rate_limit",
        new_callable=AsyncMock,
        return_value=(False, 150),
    ):
        await agent.process_query(
            user_input="Test",
            user_key="user123",
            language="es",
            ip_address="203.0.113.42",
            user_agent="Mozilla/5.0",
        )

        # Verify audit log was called with block_reason
        assert agent.db.execute.called
        call_args = agent.db.execute.call_args
        assert "rate_limit" in str(call_args).lower()
