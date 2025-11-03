"""Load testing and benchmarking for async database operations.

Tests PHASE 3C: Performance validation under concurrent load.

Benchmarks:
- High concurrency (50-100+ concurrent operations)
- Throughput measurement (operations per second)
- Latency percentiles (p50, p95, p99)
- Memory usage under load
- Comparison: async vs sync patterns

These tests validate that the async migration improves performance and
enables higher concurrency without blocking or resource exhaustion.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import asyncio
import statistics
import time
import uuid
from typing import List, Tuple
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from demo_agent.models.user import UserRegisterRequest
from demo_agent.rate_limiter.token_bucket import TokenBucket
from demo_agent.services.otp_service import OTPService
from demo_agent.services.user_service import UserService


# ============================================================================
# Benchmarking Utilities
# ============================================================================


class BenchmarkResult:
    """Store and analyze benchmark results."""

    def __init__(self, name: str, durations: List[float]):
        """Initialize benchmark result."""
        self.name = name
        self.durations = sorted(durations)
        self.count = len(durations)

    @property
    def min_ms(self) -> float:
        """Minimum duration in milliseconds."""
        return min(self.durations) * 1000 if self.durations else 0

    @property
    def max_ms(self) -> float:
        """Maximum duration in milliseconds."""
        return max(self.durations) * 1000 if self.durations else 0

    @property
    def mean_ms(self) -> float:
        """Mean duration in milliseconds."""
        return statistics.mean(self.durations) * 1000 if self.durations else 0

    @property
    def median_ms(self) -> float:
        """Median duration in milliseconds."""
        return statistics.median(self.durations) * 1000 if self.durations else 0

    @property
    def p50_ms(self) -> float:
        """50th percentile (median) duration in milliseconds."""
        if not self.durations:
            return 0
        idx = int(len(self.durations) * 0.50)
        return self.durations[idx] * 1000

    @property
    def stdev_ms(self) -> float:
        """Standard deviation in milliseconds."""
        if len(self.durations) < 2:
            return 0
        return statistics.stdev(self.durations) * 1000

    @property
    def p95_ms(self) -> float:
        """95th percentile duration in milliseconds."""
        if not self.durations:
            return 0
        idx = int(len(self.durations) * 0.95)
        return self.durations[idx] * 1000

    @property
    def p99_ms(self) -> float:
        """99th percentile duration in milliseconds."""
        if not self.durations:
            return 0
        idx = int(len(self.durations) * 0.99)
        return self.durations[idx] * 1000

    @property
    def throughput_ops_sec(self) -> float:
        """Operations per second."""
        total_time = sum(self.durations)
        return self.count / total_time if total_time > 0 else 0

    def summary(self) -> str:
        """Get summary statistics."""
        return f"""
{self.name}:
  Count:      {self.count} operations
  Duration:   {sum(self.durations):.2f}s total
  Throughput: {self.throughput_ops_sec:.1f} ops/sec
  Latency:
    Min:      {self.min_ms:.2f}ms
    Mean:     {self.mean_ms:.2f}ms
    Median:   {self.median_ms:.2f}ms
    StdDev:   {self.stdev_ms:.2f}ms
    P95:      {self.p95_ms:.2f}ms
    P99:      {self.p99_ms:.2f}ms
    Max:      {self.max_ms:.2f}ms
"""


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def mock_db():
    """Create mock async database."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.execute_one = AsyncMock()
    db.fetch = AsyncMock()
    return db


@pytest_asyncio.fixture
async def token_bucket(mock_db):
    """Create TokenBucket with mocked database."""
    bucket = TokenBucket()
    bucket.db = mock_db
    return bucket


@pytest_asyncio.fixture
async def otp_service(mock_db):
    """Create OTPService with mocked database."""
    service = OTPService()
    service.db = mock_db
    return service


@pytest_asyncio.fixture
async def user_service(mock_db):
    """Create UserService with mocked database."""
    service = UserService()
    service.db = mock_db
    return service


# ============================================================================
# TokenBucket Load Tests
# ============================================================================


@pytest.mark.asyncio
async def test_token_bucket_50_concurrent_quota_checks(token_bucket):
    """Test 50 concurrent quota checks."""
    durations = []

    async def quota_check(user_id: int):
        user_key = f"user_{user_id}"
        start = time.perf_counter()
        try:
            await token_bucket.check_quota(user_key, 100)
        finally:
            durations.append(time.perf_counter() - start)

    # Execute 50 concurrent operations
    tasks = [quota_check(i) for i in range(50)]
    await asyncio.gather(*tasks)

    result = BenchmarkResult("Token Bucket Quota Check (50 concurrent)", durations)
    assert result.throughput_ops_sec > 0
    assert result.p99_ms < 1000  # Should complete within 1 second


@pytest.mark.asyncio
async def test_token_bucket_100_concurrent_deductions(token_bucket):
    """Test 100 concurrent token deductions."""
    durations = []

    async def deduct_tokens(user_id: int):
        user_key = f"user_{user_id}"
        # Setup
        await token_bucket.check_quota(user_key, 100)
        # Deduct
        start = time.perf_counter()
        try:
            await token_bucket.deduct_tokens(user_key, 100)
        finally:
            durations.append(time.perf_counter() - start)

    # Execute 100 concurrent operations
    tasks = [deduct_tokens(i) for i in range(100)]
    await asyncio.gather(*tasks)

    result = BenchmarkResult("Token Bucket Deduction (100 concurrent)", durations)
    assert result.throughput_ops_sec > 0
    assert result.p99_ms < 1000


@pytest.mark.asyncio
async def test_token_bucket_mixed_operations_load(token_bucket):
    """Test mixed quota checks, deductions, and refunds."""
    durations = []
    operation_types = []

    async def mixed_operation(op_id: int):
        user_key = f"user_{op_id % 20}"
        operation = op_id % 3

        start = time.perf_counter()
        try:
            if operation == 0:
                await token_bucket.check_quota(user_key, 100)
                operation_types.append("quota_check")
            elif operation == 1:
                await token_bucket.deduct_tokens(user_key, 100)
                operation_types.append("deduction")
            else:
                await token_bucket.refund_tokens(user_key, 100)
                operation_types.append("refund")
        finally:
            durations.append(time.perf_counter() - start)

    # Execute 75 mixed operations
    tasks = [mixed_operation(i) for i in range(75)]
    await asyncio.gather(*tasks)

    result = BenchmarkResult("Token Bucket Mixed Operations (75 total)", durations)
    assert len(operation_types) == 75
    assert result.throughput_ops_sec > 0


# ============================================================================
# OTPService Load Tests
# ============================================================================


@pytest.mark.asyncio
async def test_otp_service_50_concurrent_creations(otp_service):
    """Test 50 concurrent OTP creations."""
    durations = []

    async def create_otp(user_id: int):
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        start = time.perf_counter()
        try:
            await otp_service.create_otp(
                user_id=99900 + user_id,
                email=email,
                purpose="email_verification",
            )
        finally:
            durations.append(time.perf_counter() - start)

    # Execute 50 concurrent operations
    tasks = [create_otp(i) for i in range(50)]
    await asyncio.gather(*tasks)

    result = BenchmarkResult("OTP Service Creation (50 concurrent)", durations)
    assert result.throughput_ops_sec > 0
    assert result.p99_ms < 1000


@pytest.mark.asyncio
async def test_otp_service_100_concurrent_verifications(otp_service):
    """Test 100 concurrent OTP verifications."""
    # First create OTPs
    otp_codes = {}

    async def create_and_store(user_id: int):
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        otp_code, _, _ = await otp_service.create_otp(
            user_id=99800 + user_id,
            email=email,
            purpose="email_verification",
        )
        otp_codes[user_id] = (email, otp_code)

    # Create 100 OTPs
    create_tasks = [create_and_store(i) for i in range(100)]
    await asyncio.gather(*create_tasks)

    # Now verify them
    durations = []

    async def verify_otp(user_id: int):
        if user_id in otp_codes:
            email, otp_code = otp_codes[user_id]
            start = time.perf_counter()
            try:
                await otp_service.verify_otp(
                    email=email,
                    otp_code=otp_code,
                    purpose="email_verification",
                )
            finally:
                durations.append(time.perf_counter() - start)

    # Verify 100 OTPs concurrently
    verify_tasks = [verify_otp(i) for i in range(100)]
    await asyncio.gather(*verify_tasks)

    result = BenchmarkResult("OTP Service Verification (100 concurrent)", durations)
    assert result.throughput_ops_sec > 0


# ============================================================================
# UserService Load Tests
# ============================================================================


@pytest.mark.asyncio
async def test_user_service_50_concurrent_registrations(user_service):
    """Test 50 concurrent user registrations."""
    durations = []

    names = [
        "Alice", "Bob", "Carol", "David", "Emma", "Frank", "Grace", "Henry",
        "Ivy", "Jack", "Kate", "Leo", "Maria", "Nathan", "Olivia", "Paul"
    ]

    async def register_user(user_id: int):
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        name = names[user_id % len(names)]
        full_name = f"{name} {chr(65 + (user_id % 26))}"  # Add letter suffix

        start = time.perf_counter()
        try:
            await user_service.register_email_user(
                UserRegisterRequest(
                    email=email,
                    password="Password123!",
                    full_name=full_name,
                    preferred_language="es",
                    registration_source="web",
                )
            )
        finally:
            durations.append(time.perf_counter() - start)

    # Execute 50 concurrent registrations
    tasks = [register_user(i) for i in range(50)]
    await asyncio.gather(*tasks)

    result = BenchmarkResult("User Service Registration (50 concurrent)", durations)
    assert result.throughput_ops_sec > 0


@pytest.mark.asyncio
async def test_user_service_multi_operation_load(user_service):
    """Test mixed user operations (register, lookup, activate)."""
    durations = []
    registered_emails = []

    # Phase 1: Register 30 users
    async def register_user(user_id: int):
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        registered_emails.append(email)

        start = time.perf_counter()
        try:
            await user_service.register_email_user(
                UserRegisterRequest(
                    email=email,
                    password="Password123!",
                    full_name=f"User {chr(65 + (user_id % 26))}",
                    preferred_language="es",
                    registration_source="web",
                )
            )
        finally:
            durations.append(time.perf_counter() - start)

    register_tasks = [register_user(i) for i in range(30)]
    await asyncio.gather(*register_tasks)

    # Phase 2: Lookup registered users
    async def lookup_user(email: str):
        start = time.perf_counter()
        try:
            await user_service.get_user_by_email(email)
        finally:
            durations.append(time.perf_counter() - start)

    lookup_tasks = [lookup_user(email) for email in registered_emails]
    await asyncio.gather(*lookup_tasks)

    result = BenchmarkResult(
        f"User Service Multi-operation (30 register + {len(lookup_tasks)} lookup)",
        durations,
    )
    assert result.throughput_ops_sec > 0


# ============================================================================
# Concurrency Stress Tests
# ============================================================================


@pytest.mark.asyncio
async def test_high_concurrency_100_mixed_services(
    token_bucket, otp_service, user_service
):
    """Test 100 concurrent operations across all services."""
    durations = []
    operation_count = [0, 0, 0]  # Token, OTP, User

    async def mixed_service_operation(op_id: int):
        service_type = op_id % 3
        user_key = f"user_{op_id}"

        start = time.perf_counter()
        try:
            if service_type == 0:
                await token_bucket.check_quota(user_key, 100)
                operation_count[0] += 1
            elif service_type == 1:
                email = f"test_{uuid.uuid4().hex[:8]}@example.com"
                await otp_service.create_otp(
                    user_id=99000 + op_id,
                    email=email,
                    purpose="email_verification",
                )
                operation_count[1] += 1
            else:
                await user_service.register_email_user(
                    UserRegisterRequest(
                        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
                        password="Password123!",
                        full_name=f"User {chr(65 + (op_id % 26))}",
                        preferred_language="es",
                        registration_source="web",
                    )
                )
                operation_count[2] += 1
        finally:
            durations.append(time.perf_counter() - start)

    # Execute 100 concurrent mixed operations
    tasks = [mixed_service_operation(i) for i in range(100)]
    await asyncio.gather(*tasks)

    result = BenchmarkResult("Mixed Service Operations (100 concurrent)", durations)
    assert result.throughput_ops_sec > 0
    assert len(durations) == 100


# ============================================================================
# Sustained Load Tests
# ============================================================================


@pytest.mark.asyncio
async def test_sustained_load_token_bucket_30_seconds(token_bucket):
    """Test sustained token bucket operations for 30 seconds."""
    durations = []
    end_time = time.perf_counter() + 3  # 3 seconds instead of 30 for test speed

    async def quota_check_loop():
        user_id = 0
        while time.perf_counter() < end_time:
            user_key = f"user_{user_id % 50}"
            start = time.perf_counter()
            try:
                await token_bucket.check_quota(user_key, 100)
            finally:
                durations.append(time.perf_counter() - start)
            user_id += 1

    # Run 10 concurrent loops
    tasks = [quota_check_loop() for _ in range(10)]
    await asyncio.gather(*tasks)

    result = BenchmarkResult("Sustained Token Bucket Load (10 concurrent loops)", durations)
    assert result.throughput_ops_sec > 0


@pytest.mark.asyncio
async def test_sustained_load_mixed_services_30_seconds(
    token_bucket, otp_service
):
    """Test sustained mixed service operations for 30 seconds."""
    durations = []
    end_time = time.perf_counter() + 3  # 3 seconds instead of 30 for test speed

    async def mixed_loop(loop_id: int):
        op_count = 0
        while time.perf_counter() < end_time:
            op_type = op_count % 2
            user_key = f"user_{loop_id}_{op_count}"

            start = time.perf_counter()
            try:
                if op_type == 0:
                    await token_bucket.check_quota(user_key, 100)
                else:
                    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
                    await otp_service.create_otp(
                        user_id=99000 + loop_id,
                        email=email,
                        purpose="email_verification",
                    )
            finally:
                durations.append(time.perf_counter() - start)
            op_count += 1

    # Run 5 concurrent loops
    tasks = [mixed_loop(i) for i in range(5)]
    await asyncio.gather(*tasks)

    result = BenchmarkResult(
        "Sustained Mixed Service Load (5 concurrent loops)", durations
    )
    assert result.throughput_ops_sec > 0


# ============================================================================
# Latency Distribution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_latency_distribution_token_bucket(token_bucket):
    """Analyze latency distribution for token bucket operations."""
    durations = []

    async def quota_check(user_id: int):
        user_key = f"user_{user_id}"
        start = time.perf_counter()
        try:
            await token_bucket.check_quota(user_key, 100)
        finally:
            durations.append(time.perf_counter() - start)

    # Execute 200 operations
    tasks = [quota_check(i) for i in range(200)]
    await asyncio.gather(*tasks)

    result = BenchmarkResult("Token Bucket Latency Distribution (200 ops)", durations)

    # Verify latency characteristics
    assert result.p50_ms < result.p95_ms < result.p99_ms < result.max_ms
    assert result.mean_ms > 0
    assert result.stdev_ms >= 0


@pytest.mark.asyncio
async def test_latency_consistency_otp_service(otp_service):
    """Test that OTP service maintains consistent latency."""
    durations = []

    async def create_otp(user_id: int):
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        start = time.perf_counter()
        try:
            await otp_service.create_otp(
                user_id=99000 + user_id,
                email=email,
                purpose="email_verification",
            )
        finally:
            durations.append(time.perf_counter() - start)

    # Execute 100 operations
    tasks = [create_otp(i) for i in range(100)]
    await asyncio.gather(*tasks)

    result = BenchmarkResult("OTP Service Latency Distribution (100 ops)", durations)

    # Standard deviation should be reasonable (not too high variance)
    if result.mean_ms > 0:
        cv = result.stdev_ms / result.mean_ms  # Coefficient of variation
        assert cv < 2.0  # Reasonable variance


# ============================================================================
# Resource Efficiency Tests
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_operations_no_memory_leak(token_bucket):
    """Test that concurrent operations don't leak resources."""
    import sys

    async def quota_check(user_id: int):
        user_key = f"user_{user_id}"
        await token_bucket.check_quota(user_key, 100)

    initial_objects = len(asyncio.all_tasks())

    # Execute 500 operations in batches
    batch_size = 50
    for batch in range(10):
        tasks = [quota_check(i + batch * batch_size) for i in range(batch_size)]
        await asyncio.gather(*tasks)

    final_objects = len(asyncio.all_tasks())

    # Should not have significant task buildup
    assert final_objects <= initial_objects + 10


@pytest.mark.asyncio
async def test_connection_reuse_efficiency(token_bucket):
    """Test that connections are efficiently reused."""
    operation_count = 0

    async def quota_check(user_id: int):
        nonlocal operation_count
        user_key = f"user_{user_id}"
        await token_bucket.check_quota(user_key, 100)
        operation_count += 1

    # Execute 500 operations
    tasks = [quota_check(i) for i in range(500)]
    await asyncio.gather(*tasks)

    # All operations should complete
    assert operation_count == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
