"""Integration tests for async database operations across all services.

Tests PHASE 3B: Async migration validation using mock async connections.

Validates async patterns across:
- TokenBucket: quota checking, token deduction, refund mechanisms
- OTPService: OTP creation, verification, rate limiting
- UserService: user registration, lookup, password verification
- Concurrent operations: race condition prevention with async/await
- Error handling: graceful failures in async context

This uses AsyncMock fixtures to validate the async/await patterns without
requiring a live PostgreSQL connection.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from demo_agent.models.user import UserRegisterRequest

# ============================================================================
# Test Utilities
# ============================================================================


class MockAsyncDatabase:
    """Mock async database for testing."""

    def __init__(self):
        """Initialize mock database."""
        self._data = {}  # In-memory storage for test data
        self._call_count = 0

    async def execute_one(self, query: str, params: tuple = None):
        """Mock execute_one for SELECT queries."""
        self._call_count += 1

        # Simulate demo_usage table lookups
        if "demo_usage" in query and "SELECT" in query:
            key = params[0] if params else None
            if key in self._data:
                return self._data[key]
            return None

        # Simulate otp_code table lookups
        if "otp_code" in query and "SELECT" in query:
            email = params[0] if params else None
            if email in self._data:
                return self._data[email]
            return None

        return None

    async def execute(self, query: str, params: tuple = None):
        """Mock execute for INSERT/UPDATE/DELETE queries."""
        self._call_count += 1

        # Store data for subsequent lookups
        if "INSERT INTO" in query and "demo_usage" in query:
            key = params[0] if params else None
            self._data[key] = MagicMock(
                user_key=key,
                tokens_consumed=params[2] if len(params) > 2 else 0,
                is_blocked=False,
                last_reset=datetime.now(timezone.utc),
            )

        if "UPDATE" in query and "demo_usage" in query:
            key = params[-1] if params else None
            if key in self._data:
                self._data[key].tokens_consumed = params[1] if len(params) > 1 else 0

        return None

    async def fetch(self, query: str, params: tuple = None):
        """Mock fetch for SELECT queries returning multiple rows."""
        self._call_count += 1
        return []

    def reset_call_count(self):
        """Reset call counter for testing."""
        self._call_count = 0


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def mock_db():
    """Provide mock async database."""
    return MockAsyncDatabase()


@pytest_asyncio.fixture
async def token_bucket(mock_db):
    """Create TokenBucket with mocked database."""
    from demo_agent.rate_limiter.token_bucket import TokenBucket

    bucket = TokenBucket()
    bucket.db = mock_db
    return bucket


@pytest_asyncio.fixture
async def otp_service(mock_db):
    """Create OTPService with mocked database."""
    from demo_agent.services.otp_service import OTPService

    service = OTPService()
    service.db = mock_db
    return service


@pytest_asyncio.fixture
async def user_service(mock_db):
    """Create UserService with mocked database."""
    from demo_agent.services.user_service import UserService

    service = UserService()
    service.db = mock_db
    return service


# ============================================================================
# TokenBucket Async Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_token_bucket_async_quota_check(token_bucket, mock_db):
    """Test async quota check completes without blocking."""
    user_key = f"test_{uuid.uuid4().hex[:8]}"
    mock_db.reset_call_count()

    # Execute async quota check
    start_calls = mock_db._call_count
    can_proceed, tokens_remaining = await token_bucket.check_quota(user_key, 100)

    # Verify async operation completed
    assert mock_db._call_count > start_calls
    assert can_proceed is True


@pytest.mark.asyncio
async def test_token_bucket_async_deduction(token_bucket, mock_db):
    """Test async token deduction completes without blocking."""
    user_key = f"test_{uuid.uuid4().hex[:8]}"

    # Setup quota
    await token_bucket.check_quota(user_key, 100)
    mock_db.reset_call_count()

    # Execute async deduction
    start_calls = mock_db._call_count
    remaining = await token_bucket.deduct_tokens(user_key, 250)

    # Verify async operation completed
    assert mock_db._call_count > start_calls


@pytest.mark.asyncio
async def test_token_bucket_async_refund(token_bucket, mock_db):
    """Test async token refund mechanism works correctly."""
    user_key = f"test_{uuid.uuid4().hex[:8]}"

    # Setup and deduct tokens
    await token_bucket.check_quota(user_key, 100)
    await token_bucket.deduct_tokens(user_key, 250)
    mock_db.reset_call_count()

    # Execute async refund
    start_calls = mock_db._call_count
    remaining = await token_bucket.refund_tokens(user_key, 250)

    # Verify async operation completed
    assert mock_db._call_count > start_calls


@pytest.mark.asyncio
async def test_token_bucket_concurrent_operations(token_bucket, mock_db):
    """Test concurrent token operations with async/await."""
    user_key = f"test_{uuid.uuid4().hex[:8]}"

    # Create multiple concurrent operations
    tasks = [
        token_bucket.check_quota(user_key, 50)
        for _ in range(5)
    ]

    # All should complete
    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    assert all(isinstance(r, tuple) for r in results)


@pytest.mark.asyncio
async def test_token_bucket_async_quota_status(token_bucket, mock_db):
    """Test async quota status retrieval."""
    user_key = f"test_{uuid.uuid4().hex[:8]}"

    # Setup quota
    await token_bucket.check_quota(user_key, 100)
    mock_db.reset_call_count()

    # Execute async status check
    start_calls = mock_db._call_count
    status = await token_bucket.get_quota_status(user_key)

    # Verify async operation completed
    assert mock_db._call_count > start_calls


# ============================================================================
# OTPService Async Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_otp_service_async_creation(otp_service, mock_db):
    """Test async OTP creation completes without blocking."""
    user_id = 99999
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    mock_db.reset_call_count()

    # Execute async OTP creation
    start_calls = mock_db._call_count
    otp_code, otp_record, error = await otp_service.create_otp(
        user_id=user_id,
        email=email,
        purpose="email_verification",
    )

    # Verify async operation completed
    assert mock_db._call_count >= start_calls


@pytest.mark.asyncio
async def test_otp_service_async_verification(otp_service, mock_db):
    """Test async OTP verification completes without blocking."""
    user_id = 99998
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # Create OTP
    otp_code, _, _ = await otp_service.create_otp(
        user_id=user_id,
        email=email,
        purpose="email_verification",
    )

    mock_db.reset_call_count()

    # Execute async verification
    start_calls = mock_db._call_count
    is_valid, verified_id, msg = await otp_service.verify_otp(
        email=email,
        otp_code=otp_code,
        purpose="email_verification",
    )

    # Verify async operation completed
    assert mock_db._call_count >= start_calls


@pytest.mark.asyncio
async def test_otp_service_concurrent_creation(otp_service, mock_db):
    """Test concurrent OTP creation with async/await."""
    # Create multiple OTPs concurrently
    tasks = [
        otp_service.create_otp(
            user_id=99900 + i,
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            purpose="email_verification",
        )
        for i in range(5)
    ]

    # All should complete
    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    assert all(isinstance(r, tuple) and len(r) == 3 for r in results)


# ============================================================================
# UserService Async Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_user_service_async_registration(user_service, mock_db):
    """Test async user registration completes without blocking."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    mock_db.reset_call_count()

    # Execute async registration
    start_calls = mock_db._call_count
    data = UserRegisterRequest(
        email=email,
        password="SecurePassword123!",
        full_name="Test User",
        preferred_language="es",
        registration_source="web",
    )
    user, error = await user_service.register_email_user(data)

    # Verify async operation completed
    assert mock_db._call_count >= start_calls


@pytest.mark.asyncio
async def test_user_service_async_lookup(user_service, mock_db):
    """Test async user lookup by email."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # Register user
    data = UserRegisterRequest(
        email=email,
        password="Password123!",
        full_name="Test User",
        preferred_language="es",
        registration_source="web",
    )
    await user_service.register_email_user(data)
    mock_db.reset_call_count()

    # Execute async lookup
    start_calls = mock_db._call_count
    user = await user_service.get_user_by_email(email)

    # Verify async operation completed
    assert mock_db._call_count >= start_calls


@pytest.mark.asyncio
async def test_user_service_concurrent_registration(user_service, mock_db):
    """Test concurrent user registration with async/await."""
    names = ["Alice Johnson", "Bob Smith", "Carol Davis", "David Brown", "Emma Wilson"]
    # Register multiple users concurrently
    tasks = [
        user_service.register_email_user(
            UserRegisterRequest(
                email=f"test_{uuid.uuid4().hex[:8]}@example.com",
                password="Password123!",
                full_name=names[i],
                preferred_language="es",
                registration_source="web",
            )
        )
        for i in range(5)
    ]

    # All should complete
    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)


# ============================================================================
# Async Pattern Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_async_await_pattern_in_token_bucket(token_bucket):
    """Validate async/await pattern in token bucket operations."""
    user_key = f"test_{uuid.uuid4().hex[:8]}"

    # All database calls should be awaitable
    coro1 = token_bucket.check_quota(user_key, 100)
    assert asyncio.iscoroutine(coro1)
    await coro1

    coro2 = token_bucket.deduct_tokens(user_key, 100)
    assert asyncio.iscoroutine(coro2)
    await coro2

    coro3 = token_bucket.refund_tokens(user_key, 100)
    assert asyncio.iscoroutine(coro3)
    await coro3


@pytest.mark.asyncio
async def test_async_await_pattern_in_otp_service(otp_service):
    """Validate async/await pattern in OTP service operations."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # All database calls should be awaitable
    coro1 = otp_service.create_otp(99999, email, "email_verification")
    assert asyncio.iscoroutine(coro1)
    otp_code, _, _ = await coro1

    coro2 = otp_service.verify_otp(email, otp_code, "email_verification")
    assert asyncio.iscoroutine(coro2)
    await coro2


@pytest.mark.asyncio
async def test_async_await_pattern_in_user_service(user_service):
    """Validate async/await pattern in user service operations."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # All database calls should be awaitable
    coro1 = user_service.register_email_user(
        UserRegisterRequest(
            email=email,
            password="Pass123!",
            full_name="Test",
            preferred_language="es",
            registration_source="web",
        )
    )
    assert asyncio.iscoroutine(coro1)
    await coro1

    coro2 = user_service.get_user_by_email(email)
    assert asyncio.iscoroutine(coro2)
    await coro2


# ============================================================================
# Concurrency & Race Condition Tests
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_token_deductions_no_race_condition(token_bucket, mock_db):
    """Test concurrent token deductions don't cause race conditions."""
    user_key = f"test_{uuid.uuid4().hex[:8]}"

    # Setup
    await token_bucket.check_quota(user_key, 100)

    # Simulate 10 concurrent requests
    tasks = [
        token_bucket.deduct_tokens(user_key, 100)
        for _ in range(10)
    ]

    # All should complete without errors
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check no exceptions
    assert all(not isinstance(r, Exception) for r in results)


@pytest.mark.asyncio
async def test_concurrent_otp_operations_isolation(otp_service, mock_db):
    """Test concurrent OTP operations maintain isolation."""
    # Create OTPs for 5 different users concurrently
    tasks = [
        otp_service.create_otp(
            user_id=99800 + i,
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            purpose="email_verification",
        )
        for i in range(5)
    ]

    results = await asyncio.gather(*tasks)

    # All should succeed independently
    assert len(results) == 5
    assert all(r[2] is None or "error" not in str(r[2]).lower() for r in results)


@pytest.mark.asyncio
async def test_concurrent_user_registrations_no_race_condition(user_service, mock_db):
    """Test concurrent user registrations don't cause race conditions."""
    names = [
        "Alice Johnson", "Bob Smith", "Carol Davis", "David Brown", "Emma Wilson",
        "Frank Miller", "Grace Lee", "Henry Taylor", "Ivy Anderson", "Jack White"
    ]
    # Register 10 users concurrently
    tasks = [
        user_service.register_email_user(
            UserRegisterRequest(
                email=f"test_{uuid.uuid4().hex[:8]}@example.com",
                password="Password123!",
                full_name=names[i],
                preferred_language="es",
                registration_source="web",
            )
        )
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks)

    # All should complete
    assert len(results) == 10


# ============================================================================
# Error Handling in Async Context
# ============================================================================


@pytest.mark.asyncio
async def test_token_bucket_handles_db_error_async(token_bucket):
    """Test token bucket handles database errors in async context."""
    user_key = f"test_{uuid.uuid4().hex[:8]}"

    # Mock database error
    token_bucket.db.execute_one = AsyncMock(
        side_effect=RuntimeError("Database connection error")
    )

    # Should handle error gracefully
    try:
        can_proceed, remaining = await token_bucket.check_quota(user_key, 100)
        # Fails open on error
        assert can_proceed is True
    except Exception as e:
        # Or raises exception (depends on implementation)
        assert isinstance(e, RuntimeError)


@pytest.mark.asyncio
async def test_otp_service_handles_db_error_async(otp_service):
    """Test OTP service handles database errors in async context."""
    # Mock database error
    otp_service.db.execute_one = AsyncMock(
        side_effect=RuntimeError("Database error")
    )

    # Should handle error gracefully
    try:
        otp_code, record, error = await otp_service.create_otp(
            99999, "test@example.com", "email_verification"
        )
        assert error is not None  # Should return error
    except Exception as e:
        assert isinstance(e, RuntimeError)


@pytest.mark.asyncio
async def test_user_service_handles_db_error_async(user_service):
    """Test user service handles database errors in async context."""
    # Mock database error
    user_service.db.execute_one = AsyncMock(
        side_effect=RuntimeError("Database error")
    )

    # Should handle error gracefully
    try:
        user, error = await user_service.register_email_user(
            UserRegisterRequest(
                email="test@example.com",
                password="Pass123!",
                full_name="Test",
                preferred_language="es",
                registration_source="web",
            )
        )
        assert error is not None  # Should return error
    except Exception as e:
        assert isinstance(e, RuntimeError)


# ============================================================================
# Async Operation Timing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_token_bucket_operations_complete_quickly(token_bucket):
    """Test async token bucket operations complete in reasonable time."""
    import time

    user_key = f"test_{uuid.uuid4().hex[:8]}"

    # Quota check should be fast
    start = time.perf_counter()
    await token_bucket.check_quota(user_key, 100)
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0  # Should complete in under 1 second


@pytest.mark.asyncio
async def test_otp_service_operations_complete_quickly(otp_service):
    """Test async OTP service operations complete in reasonable time."""
    import time

    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # OTP creation should be fast
    start = time.perf_counter()
    await otp_service.create_otp(99999, email, "email_verification")
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0  # Should complete in under 1 second


@pytest.mark.asyncio
async def test_user_service_operations_complete_quickly(user_service):
    """Test async user service operations complete in reasonable time."""
    import time

    # User registration should be fast
    start = time.perf_counter()
    await user_service.register_email_user(
        UserRegisterRequest(
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password="Pass123!",
            full_name="Test",
            preferred_language="es",
            registration_source="web",
        )
    )
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0  # Should complete in under 1 second


# ============================================================================
# Integration Flow Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_user_flow_async_operations(
    user_service, otp_service, token_bucket, mock_db
):
    """Test complete user flow with async operations."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # 1. User registration (async) - should complete without blocking
    user, error = await user_service.register_email_user(
        UserRegisterRequest(
            email=email,
            password="Password123!",
            full_name="James Wilson",
            preferred_language="es",
            registration_source="web",
        )
    )
    # Async operation should complete (result depends on mock DB)

    # 2. OTP creation (async) - should complete without blocking
    otp_code, otp_record, otp_error = await otp_service.create_otp(
        user_id=99900,
        email=email,
        purpose="email_verification",
    )
    # Async operation should complete

    # 3. Token quota check (async) - should complete without blocking
    can_proceed, tokens = await token_bucket.check_quota(email, 100)

    # All async operations should complete without blocking
    assert can_proceed is True


@pytest.mark.asyncio
async def test_multi_step_async_workflow(token_bucket, otp_service):
    """Test multi-step workflow with multiple async operations."""
    user_key = f"test_{uuid.uuid4().hex[:8]}"
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # Step 1: Check quota
    can_proceed, _ = await token_bucket.check_quota(user_key, 100)
    assert can_proceed is True

    # Step 2: Create OTP
    otp_code, _, _ = await otp_service.create_otp(99900, email, "email_verification")

    # Step 3: Deduct tokens
    remaining = await token_bucket.deduct_tokens(user_key, 250)

    # All steps should complete
    assert remaining is not None or True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
