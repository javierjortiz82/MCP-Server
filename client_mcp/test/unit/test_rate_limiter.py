"""Unit tests for RateLimiter."""

import asyncio

import pytest

# Try to import, skip tests if aiolimiter not available
pytest.importorskip("aiolimiter", reason="aiolimiter not installed")

from core.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test suite for RateLimiter class."""

    def test_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(rpm_limit=15, rpd_limit=1500, max_concurrent=3)

        assert limiter.rpm_limit == 15
        assert limiter.rpd_limit == 1500
        assert limiter.max_concurrent == 3
        assert limiter.total_requests == 0
        assert limiter.requests_today == 0

    @pytest.mark.asyncio
    async def test_acquire_basic(self):
        """Test basic rate limiter acquire."""
        limiter = RateLimiter(rpm_limit=100, rpd_limit=1000, max_concurrent=5)

        async with limiter.acquire():
            # Inside the context, we should have acquired the slot
            pass

        # After context, request should be counted
        assert limiter.total_requests == 1
        assert limiter.requests_today == 1

    @pytest.mark.asyncio
    async def test_multiple_requests(self):
        """Test multiple sequential requests."""
        limiter = RateLimiter(rpm_limit=100, rpd_limit=1000, max_concurrent=5)

        for i in range(5):
            async with limiter.acquire():
                pass

        assert limiter.total_requests == 5
        assert limiter.requests_today == 5

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test concurrent requests respect semaphore."""
        limiter = RateLimiter(rpm_limit=100, rpd_limit=1000, max_concurrent=2)

        async def make_request():
            async with limiter.acquire():
                await asyncio.sleep(0.1)

        # This should work fine (2 concurrent)
        await asyncio.gather(make_request(), make_request())

        assert limiter.total_requests == 2

    def test_get_current_rpm(self):
        """Test get_current_rpm method."""
        limiter = RateLimiter(rpm_limit=15, rpd_limit=1500, max_concurrent=3)

        # Initial state
        assert limiter.get_current_rpm() == 0

        # After some requests
        limiter.total_requests = 10
        current_rpm = limiter.get_current_rpm()
        assert current_rpm == 10

    def test_get_remaining_daily_quota(self):
        """Test get_remaining_daily_quota method."""
        limiter = RateLimiter(rpm_limit=15, rpd_limit=1500, max_concurrent=3)

        # Initial state
        assert limiter.get_remaining_daily_quota() == 1500

        # After some requests
        limiter.requests_today = 100
        assert limiter.get_remaining_daily_quota() == 1400

    def test_is_approaching_daily_limit(self):
        """Test is_approaching_daily_limit method."""
        limiter = RateLimiter(rpm_limit=15, rpd_limit=1000, max_concurrent=3)

        # Not approaching (10%)
        limiter.requests_today = 100
        assert limiter.is_approaching_daily_limit(threshold=0.9) is False

        # Approaching (91%)
        limiter.requests_today = 910
        assert limiter.is_approaching_daily_limit(threshold=0.9) is True

        # Exceeded
        limiter.requests_today = 1000
        assert limiter.is_approaching_daily_limit(threshold=0.9) is True

    def test_reset_daily_counter(self):
        """Test reset_daily_counter method."""
        limiter = RateLimiter(rpm_limit=15, rpd_limit=1500, max_concurrent=3)

        # Set some requests
        limiter.requests_today = 500
        old_reset = limiter.last_reset

        # Reset
        limiter.reset_daily_counter()

        assert limiter.requests_today == 0
        assert limiter.last_reset > old_reset

    def test_get_stats(self):
        """Test get_stats method."""
        limiter = RateLimiter(rpm_limit=15, rpd_limit=1500, max_concurrent=3)

        limiter.total_requests = 100
        limiter.requests_today = 50
        limiter.total_wait_time_ms = 1000.0

        stats = limiter.get_stats()

        assert stats["total_requests"] == 100
        assert stats["requests_today"] == 50
        assert stats["remaining_daily_quota"] == 1450
        assert stats["avg_wait_time_ms"] == 10.0  # 1000/100
        assert stats["rpm_limit"] == 15
        assert stats["rpd_limit"] == 1500
        assert stats["max_concurrent"] == 3
        assert "last_reset" in stats

    def test_get_stats_zero_requests(self):
        """Test get_stats with zero requests."""
        limiter = RateLimiter(rpm_limit=15, rpd_limit=1500, max_concurrent=3)

        stats = limiter.get_stats()

        assert stats["total_requests"] == 0
        assert stats["avg_wait_time_ms"] == 0.0


class TestRateLimiterGlobalInstance:
    """Test global rate limiter instance functions."""

    def test_get_rate_limiter(self):
        """Test get_rate_limiter creates instance."""
        from core.rate_limiter import get_rate_limiter, reset_rate_limiter

        # Reset first
        reset_rate_limiter()

        # Get instance
        limiter1 = get_rate_limiter()
        assert limiter1 is not None

        # Should return same instance
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2

    def test_reset_rate_limiter(self):
        """Test reset_rate_limiter resets global instance."""
        from core.rate_limiter import get_rate_limiter, reset_rate_limiter

        limiter1 = get_rate_limiter()
        reset_rate_limiter()
        limiter2 = get_rate_limiter()

        # Should be different instances
        assert limiter1 is not limiter2
