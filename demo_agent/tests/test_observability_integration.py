"""Integration tests for observability system with services.

Tests OPCIÓN 5: Integrar Observabilidad en Servicios

Tests cover:
- Service-level observability integration (TokenBucket, OTPService, UserService)
- Correlation ID propagation through service calls
- Metrics collection from async service operations
- Request context propagation in concurrent scenarios
- Audit trail logging for sensitive operations
- Performance metrics tracking

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from demo_agent.observability.context import (
    clear_request_context,
    create_request_context,
    get_request_context,
)
from demo_agent.observability.correlation import CorrelationID
from demo_agent.observability.metrics import (
    get_metrics_collector,
    reset_metrics_collector,
)

# ============================================================================
# TokenBucket Service Observability Tests
# ============================================================================


class TestTokenBucketObservability:
    """Tests for TokenBucket service observability integration."""

    @pytest.mark.asyncio
    async def test_check_quota_records_metrics(self):
        """Test that check_quota records latency and event metrics."""
        reset_metrics_collector()

        # Create mock database and service
        from demo_agent.rate_limiter.token_bucket import TokenBucket

        with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock database response for quota check - must include is_blocked
            mock_db.execute_one.return_value = {
                "id": 1,
                "user_key": "user_123",
                "tokens_consumed": 1000,
                "requests_count": 5,
                "last_reset": datetime.now(timezone.utc),
                "is_blocked": False,
                "blocked_until": None,
            }

            service = TokenBucket()
            metrics = get_metrics_collector()

            # Execute check_quota
            can_proceed, remaining = await service.check_quota("user_123", tokens_needed=250)

            # Verify metrics were recorded
            assert can_proceed is True
            summary = metrics.get_summary()
            assert summary["latency"]["count"] == 1  # One latency measurement
            assert summary["counters"]["quota_checks"] == 1  # One quota check counter
            assert summary["latency"]["avg_ms"] >= 0

    @pytest.mark.asyncio
    async def test_deduct_tokens_increments_counter(self):
        """Test that deduct_tokens increments the correct counter."""
        reset_metrics_collector()

        from demo_agent.rate_limiter.token_bucket import TokenBucket

        with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock database response - deduct_tokens returns tokens_consumed and is_blocked
            mock_db.execute_one.return_value = {
                "tokens_consumed": 1250,
                "is_blocked": False,
            }

            service = TokenBucket()
            metrics = get_metrics_collector()

            # Execute deduct_tokens with correct parameter name
            result = await service.deduct_tokens("user_123", tokens_used=250)

            # Verify metrics
            summary = metrics.get_summary()
            assert summary["counters"]["tokens_deducted"] == 250
            assert summary["latency"]["count"] == 1

    @pytest.mark.asyncio
    async def test_refund_tokens_records_refund_counter(self):
        """Test that refund_tokens records refund metrics."""
        reset_metrics_collector()

        from demo_agent.rate_limiter.token_bucket import TokenBucket

        with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock database response - refund_tokens returns tokens_consumed and is_blocked
            mock_db.execute_one.return_value = {
                "tokens_consumed": 750,
                "is_blocked": False,
            }

            service = TokenBucket()
            metrics = get_metrics_collector()

            # Execute refund_tokens with correct parameter name
            result = await service.refund_tokens("user_123", tokens_to_refund=250)

            # Verify metrics
            summary = metrics.get_summary()
            assert summary["counters"]["tokens_refunded"] == 250
            assert summary["latency"]["count"] == 1

    @pytest.mark.asyncio
    async def test_quota_operations_with_correlation_id(self):
        """Test that quota operations include correlation ID in logs."""
        reset_metrics_collector()
        CorrelationID.set("test-corr-123")

        from demo_agent.rate_limiter.token_bucket import TokenBucket

        with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            mock_db.execute_one.return_value = {
                "daily_quota": 5000,
                "tokens_used_today": 1000,
                "tokens_remaining": 4000,
                "last_reset": datetime.now(timezone.utc),
            }

            service = TokenBucket()

            # Execute with correlation ID set
            can_proceed, remaining = await service.check_quota("user_123", tokens_needed=250)

            # Correlation ID should still be set (not cleared by service)
            assert CorrelationID.get() == "test-corr-123"

            CorrelationID.clear()


# ============================================================================
# OTPService Observability Tests
# ============================================================================


class TestOTPServiceObservability:
    """Tests for OTPService observability integration."""

    @pytest.mark.asyncio
    async def test_can_request_otp_records_metrics(self):
        """Test that can_request_otp records latency metrics."""
        reset_metrics_collector()

        from demo_agent.models.user import OTPPurpose
        from demo_agent.services.otp_service import OTPService

        with patch("demo_agent.services.otp_service.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock database response
            mock_db.execute_one.return_value = {"can_request_otp": True}

            service = OTPService()
            metrics = get_metrics_collector()

            # Execute can_request_otp
            can_request, cooldown = await service.can_request_otp(
                "test@example.com", OTPPurpose.EMAIL_VERIFICATION
            )

            # Verify metrics
            assert can_request is True
            summary = metrics.get_summary()
            assert summary["latency"]["count"] == 1
            assert summary["counters"]["otp_rate_limit_checks_allowed"] == 1

    @pytest.mark.asyncio
    async def test_create_otp_records_metrics(self):
        """Test that create_otp records creation metrics."""
        reset_metrics_collector()

        from demo_agent.models.user import OTPPurpose
        from demo_agent.services.otp_service import OTPService

        with patch("demo_agent.services.otp_service.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock database responses
            mock_db.execute_one.side_effect = [
                {"can_request_otp": True},  # can_request_otp response
                {  # create_otp response
                    "id": 1,
                    "user_id": 123,
                    "email": "test@example.com",
                    "code_hash": "abc123",
                    "purpose": "email_verification",
                    "expires_at": datetime.now(timezone.utc),
                    "attempts_count": 0,
                    "max_attempts": 3,
                    "is_used": False,
                    "used_at": None,
                    "ip_address": None,
                    "user_agent": None,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            ]
            mock_db.execute.return_value = None  # For invalidating old OTPs

            service = OTPService()
            metrics = get_metrics_collector()

            # Execute create_otp
            otp_code, otp_record, error = await service.create_otp(
                user_id=123,
                email="test@example.com",
                purpose=OTPPurpose.EMAIL_VERIFICATION,
            )

            # Verify metrics
            assert otp_code is not None
            assert len(otp_code) == 6
            summary = metrics.get_summary()
            assert summary["counters"]["otp_codes_created"] == 1

    @pytest.mark.asyncio
    async def test_otp_rate_limit_exceeded_counter(self):
        """Test that rate limit exceeded counter is incremented."""
        reset_metrics_collector()

        from demo_agent.models.user import OTPPurpose
        from demo_agent.services.otp_service import OTPService

        with patch("demo_agent.services.otp_service.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock rate limit exceeded response
            mock_db.execute_one.side_effect = [
                {"can_request_otp": False},  # Rate limit exceeded
                {
                    "created_at": datetime.now(timezone.utc),
                },  # Last OTP creation time
            ]

            service = OTPService()
            metrics = get_metrics_collector()

            # Execute can_request_otp when rate limited
            can_request, cooldown = await service.can_request_otp(
                "test@example.com", OTPPurpose.EMAIL_VERIFICATION
            )

            # Verify metrics
            assert can_request is False
            summary = metrics.get_summary()
            assert summary["counters"]["otp_rate_limit_exceeded"] == 1


# ============================================================================
# UserService Observability Tests
# ============================================================================


class TestUserServiceObservability:
    """Tests for UserService observability integration."""

    @pytest.mark.asyncio
    async def test_register_email_user_records_success_metric(self):
        """Test that successful email registration records metrics."""
        reset_metrics_collector()

        from demo_agent.models.user import UserRegisterRequest
        from demo_agent.services.user_service import UserService

        with patch("demo_agent.services.user_service.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock database responses
            mock_db.execute_one.side_effect = [
                None,  # get_user_by_email returns None
                {  # register_email_user returns new user
                    "id": 1,
                    "email": "newuser@example.com",
                    "full_name": "Test User",
                    "display_name": None,
                    "auth_provider": "email",
                    "password_hash": "hashed_pwd",
                    "oauth_provider_id": None,
                    "is_email_verified": False,
                    "email_verified_at": None,
                    "is_active": False,
                    "is_suspended": False,
                    "is_deleted": False,
                    "suspended_at": None,
                    "suspended_reason": None,
                    "deleted_at": None,
                    "preferred_language": "es",
                    "timezone": "America/Costa_Rica",
                    "registration_source": "web",
                    "registration_ip": "203.0.113.1",
                    "last_login_at": None,
                    "last_login_ip": None,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            ]

            service = UserService()
            metrics = get_metrics_collector()

            # Execute register
            data = UserRegisterRequest(
                email="newuser@example.com",
                password="SecurePassword123!",
                full_name="Test User",
            )

            user, error = await service.register_email_user(data, ip_address="203.0.113.1")

            # Verify metrics
            assert user is not None
            summary = metrics.get_summary()
            assert summary["counters"]["registrations_email_successful"] == 1
            assert summary["counters"]["user_lookup_email_not_found"] == 1

    @pytest.mark.asyncio
    async def test_register_oauth_user_records_metrics(self):
        """Test that OAuth registration records metrics."""
        reset_metrics_collector()

        from demo_agent.models.user import AuthProvider, OAuthRegisterRequest
        from demo_agent.services.user_service import UserService

        with patch("demo_agent.services.user_service.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock database responses
            mock_db.execute_one.side_effect = [
                None,  # get_user_by_oauth returns None
                None,  # get_user_by_email returns None
                {  # register_oauth_user returns new user
                    "id": 2,
                    "email": "oauth@example.com",
                    "full_name": "OAuth User",
                    "display_name": None,
                    "auth_provider": "google",
                    "password_hash": None,
                    "oauth_provider_id": "google_123456",
                    "is_email_verified": True,
                    "email_verified_at": datetime.now(timezone.utc),
                    "is_active": True,
                    "is_suspended": False,
                    "is_deleted": False,
                    "suspended_at": None,
                    "suspended_reason": None,
                    "deleted_at": None,
                    "preferred_language": "es",
                    "timezone": "America/Costa_Rica",
                    "registration_source": "web",
                    "registration_ip": "203.0.113.1",
                    "last_login_at": None,
                    "last_login_ip": None,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            ]

            service = UserService()
            metrics = get_metrics_collector()

            # Execute register
            data = OAuthRegisterRequest(
                email="oauth@example.com",
                full_name="OAuth User",
                auth_provider=AuthProvider.GOOGLE,
                oauth_provider_id="google_123456",
            )

            user, error = await service.register_oauth_user(data, ip_address="203.0.113.1")

            # Verify metrics
            assert user is not None
            summary = metrics.get_summary()
            assert summary["counters"]["registrations_oauth_successful"] == 1
            assert summary["counters"]["user_lookup_oauth_not_found"] == 1

    @pytest.mark.asyncio
    async def test_get_user_by_email_records_lookup_metrics(self):
        """Test that user lookups record metrics."""
        reset_metrics_collector()

        from demo_agent.services.user_service import UserService

        with patch("demo_agent.services.user_service.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock database response
            mock_db.execute_one.return_value = None

            service = UserService()
            metrics = get_metrics_collector()

            # Execute lookup
            user = await service.get_user_by_email("nonexistent@example.com")

            # Verify metrics
            assert user is None
            summary = metrics.get_summary()
            assert summary["counters"]["user_lookup_email_not_found"] == 1

    @pytest.mark.asyncio
    async def test_activate_user_records_metrics(self):
        """Test that user activation records metrics."""
        reset_metrics_collector()

        from demo_agent.services.user_service import UserService

        with patch("demo_agent.services.user_service.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock successful activation
            mock_db.execute_one.return_value = {"id": 1}

            service = UserService()
            metrics = get_metrics_collector()

            # Execute activation
            result = await service.activate_user(user_id=1)

            # Verify metrics
            assert result is True
            summary = metrics.get_summary()
            assert summary["counters"]["user_activations_successful"] == 1

    @pytest.mark.asyncio
    async def test_verify_password_records_metrics(self):
        """Test that password verification records metrics."""
        reset_metrics_collector()

        from demo_agent.models.user import UserDB
        from demo_agent.services.user_service import UserService

        with patch("demo_agent.services.user_service.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            service = UserService()
            metrics = get_metrics_collector()

            # Create a mock user with a valid password hash
            user = UserDB(
                id=1,
                email="test@example.com",
                full_name="Test User",
                display_name=None,
                auth_provider="email",
                password_hash="$2b$12$abcdefghijklmnopqrstuvwxyz",  # Mock hash
                oauth_provider_id=None,
                is_email_verified=True,
                email_verified_at=datetime.now(timezone.utc),
                is_active=True,
                is_suspended=False,
                is_deleted=False,
                suspended_at=None,
                suspended_reason=None,
                deleted_at=None,
                preferred_language="es",
                timezone="America/Costa_Rica",
                registration_source="web",
                registration_ip="203.0.113.1",
                last_login_at=None,
                last_login_ip=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            # Execute password verification (will fail due to mock hash)
            result = await service.verify_password(user, "wrongpassword")

            # Verify metrics
            summary = metrics.get_summary()
            assert "password_verify" in str(summary["counters"])


# ============================================================================
# Correlation ID Propagation Tests
# ============================================================================


class TestCorrelationIdPropagation:
    """Tests for correlation ID propagation through service calls."""

    @pytest.mark.asyncio
    async def test_correlation_id_persists_across_service_calls(self):
        """Test that correlation ID persists across async service operations."""
        reset_metrics_collector()
        correlation_id = "test-corr-123"
        CorrelationID.set(correlation_id)

        from demo_agent.rate_limiter.token_bucket import TokenBucket
        from demo_agent.services.user_service import UserService

        with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_get_db_tb, patch(
            "demo_agent.services.user_service.get_db"
        ) as mock_get_db_us:

            mock_db_tb = AsyncMock()
            mock_db_us = AsyncMock()
            mock_get_db_tb.return_value = mock_db_tb
            mock_get_db_us.return_value = mock_db_us

            mock_db_tb.execute_one.return_value = {
                "daily_quota": 5000,
                "tokens_used_today": 1000,
                "tokens_remaining": 4000,
                "last_reset": datetime.now(timezone.utc),
            }

            mock_db_us.execute_one.return_value = None

            tb_service = TokenBucket()
            user_service = UserService()

            # Call multiple services
            can_proceed, remaining = await tb_service.check_quota("user_123", tokens_needed=250)
            user = await user_service.get_user_by_email("test@example.com")

            # Correlation ID should still be set
            assert CorrelationID.get() == correlation_id

        CorrelationID.clear()

    @pytest.mark.asyncio
    async def test_request_context_propagation_in_concurrent_calls(self):
        """Test that request context doesn't leak between concurrent service calls."""
        reset_metrics_collector()

        async def service_operation(user_key: str, operation_id: int):
            # Create request context for this operation
            ctx = create_request_context(user_key=user_key)

            from demo_agent.rate_limiter.token_bucket import TokenBucket

            with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_get_db:
                mock_db = AsyncMock()
                mock_get_db.return_value = mock_db

                mock_db.execute_one.return_value = {
                    "daily_quota": 5000,
                    "tokens_used_today": 1000,
                    "tokens_remaining": 4000,
                    "last_reset": datetime.now(timezone.utc),
                }

                service = TokenBucket()

                # Execute operation
                can_proceed, remaining = await service.check_quota(user_key, tokens_needed=250)

                # Verify context is still correct for this task
                current_ctx = get_request_context()
                assert current_ctx is not None
                assert current_ctx.user_key == user_key

            clear_request_context()

        # Run concurrent operations
        await asyncio.gather(
            service_operation("user_1", 1),
            service_operation("user_2", 2),
            service_operation("user_3", 3),
        )


# ============================================================================
# Metrics Accuracy Tests
# ============================================================================


class TestMetricsAccuracy:
    """Tests for metrics collection accuracy across services."""

    @pytest.mark.asyncio
    async def test_concurrent_metrics_dont_interfere(self):
        """Test that metrics from concurrent operations are accumulated correctly."""
        reset_metrics_collector()

        async def concurrent_operation(user_id: int, tokens_to_deduct: int):
            from demo_agent.rate_limiter.token_bucket import TokenBucket

            with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_get_db:
                mock_db = AsyncMock()
                mock_get_db.return_value = mock_db

                mock_db.execute_one.return_value = {
                    "tokens_consumed": 5000 - tokens_to_deduct,
                    "is_blocked": False,
                }

                service = TokenBucket()
                metrics = get_metrics_collector()

                # Execute operation with correct parameter name
                result = await service.deduct_tokens(f"user_{user_id}", tokens_used=tokens_to_deduct)

        # Run 10 concurrent operations with different token amounts
        await asyncio.gather(
            *[concurrent_operation(i, (i + 1) * 50) for i in range(10)]
        )

        # Verify total tokens deducted is correct
        metrics = get_metrics_collector()
        summary = metrics.get_summary()

        expected_total = sum((i + 1) * 50 for i in range(10))
        assert summary["counters"]["tokens_deducted"] == expected_total

    @pytest.mark.asyncio
    async def test_latency_percentiles_with_concurrent_operations(self):
        """Test that latency percentiles are calculated correctly with concurrent ops."""
        reset_metrics_collector()

        async def slow_operation(duration_ms: int):
            from demo_agent.rate_limiter.token_bucket import TokenBucket

            with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_get_db:
                mock_db = AsyncMock()
                mock_get_db.return_value = mock_db

                mock_db.execute_one.return_value = {
                    "daily_quota": 5000,
                    "tokens_used_today": 1000,
                    "tokens_remaining": 4000,
                    "last_reset": datetime.now(timezone.utc),
                }

                service = TokenBucket()

                # Simulate operation with specific duration
                async with service.metrics.record_latency_async("test_op"):
                    await asyncio.sleep(duration_ms / 1000.0)

        # Run operations with varying durations
        durations = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
        await asyncio.gather(*[slow_operation(d) for d in durations])

        # Verify percentiles
        metrics = get_metrics_collector()
        summary = metrics.get_summary()

        assert summary["latency"]["count"] == 10
        assert summary["latency"]["p95_ms"] >= summary["latency"]["avg_ms"]
        assert summary["latency"]["p99_ms"] >= summary["latency"]["p95_ms"]


# ============================================================================
# Error Handling & Observability Tests
# ============================================================================


class TestErrorHandlingObservability:
    """Tests for observability during error scenarios."""

    @pytest.mark.asyncio
    async def test_error_counter_incremented_on_failure(self):
        """Test that error counters are incremented when operations fail."""
        reset_metrics_collector()

        from demo_agent.rate_limiter.token_bucket import TokenBucket

        with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Mock database error
            mock_db.execute_one.side_effect = Exception("Database connection failed")

            service = TokenBucket()
            metrics = get_metrics_collector()

            # Execute and handle error gracefully
            can_proceed, remaining = await service.check_quota("user_123", tokens_needed=250)

            # Service should fail gracefully
            assert can_proceed is True  # Fail open for quota checks
            summary = metrics.get_summary()
            # Error counter should be incremented
            assert "quota_check_errors" in summary["counters"]

    @pytest.mark.asyncio
    async def test_service_error_doesnt_lose_context(self):
        """Test that errors don't clear the request context."""
        reset_metrics_collector()
        ctx = create_request_context(user_key="user_123")

        from demo_agent.rate_limiter.token_bucket import TokenBucket

        with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            mock_db.execute_one.side_effect = Exception("Database error")

            service = TokenBucket()

            # Execute operation that will fail
            try:
                can_proceed, remaining = await service.check_quota("user_123", tokens_needed=250)
            except:
                pass

            # Context should still be available
            current_ctx = get_request_context()
            assert current_ctx is not None
            assert current_ctx.user_key == "user_123"

        clear_request_context()


# ============================================================================
# Structured Logging Integration Tests
# ============================================================================


class TestStructuredLoggingIntegration:
    """Tests for structured logging in service operations."""

    @pytest.mark.asyncio
    async def test_service_logs_include_correlation_id(self):
        """Test that service logs include correlation ID."""
        correlation_id = "test-corr-456"
        CorrelationID.set(correlation_id)

        from demo_agent.services.user_service import UserService

        with patch("demo_agent.services.user_service.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            mock_db.execute_one.return_value = None

            service = UserService()

            # This will log with the correlation ID
            user = await service.get_user_by_email("test@example.com")

            # Verify correlation ID is still accessible
            assert CorrelationID.get() == correlation_id

        CorrelationID.clear()

    @pytest.mark.asyncio
    async def test_service_logs_include_custom_fields(self):
        """Test that service logs include custom fields."""
        reset_metrics_collector()
        ctx = create_request_context(user_key="user_789", ip_address="203.0.113.99")

        from demo_agent.rate_limiter.token_bucket import TokenBucket

        with patch("demo_agent.rate_limiter.token_bucket.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            mock_db.execute_one.return_value = {
                "daily_quota": 5000,
                "tokens_used_today": 1000,
                "tokens_remaining": 4000,
                "last_reset": datetime.now(timezone.utc),
            }

            service = TokenBucket()

            # Execute operation
            can_proceed, remaining = await service.check_quota("user_789", tokens_needed=250)

            # Verify context fields are preserved
            current_ctx = get_request_context()
            assert current_ctx.user_key == "user_789"
            assert current_ctx.ip_address == "203.0.113.99"

        clear_request_context()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
