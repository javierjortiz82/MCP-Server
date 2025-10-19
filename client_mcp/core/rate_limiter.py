"""Rate Limiter for Gemini API Calls.

This module implements rate limiting for Google Gemini API using aiolimiter
to comply with free tier limits: 15 RPM (Requests Per Minute) and 1500 RPD
(Requests Per Day).

Implements Leaky Bucket algorithm for smooth traffic control.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from aiolimiter import AsyncLimiter

from client_mcp.config.settings import settings
from client_mcp.utils.logger import get_logger


class RateLimiter:
    """Rate limiter for Gemini API calls.

    Uses aiolimiter (Leaky Bucket algorithm) to enforce:
    - RPM (Requests Per Minute) limit
    - RPD (Requests Per Day) limit
    - Concurrent request limit

    Example:
        rate_limiter = RateLimiter(
            rpm_limit=15,
            rpd_limit=1500,
            max_concurrent=3
        )

        async with rate_limiter.acquire():
            response = await api_call()
    """

    def __init__(
        self,
        rpm_limit: int = settings.GEMINI_RPM_LIMIT,
        rpd_limit: int = settings.GEMINI_RPD_LIMIT,
        max_concurrent: int = settings.MAX_CONCURRENT_REQUESTS,
    ):
        """Initialize rate limiter with tier-specific limits.

        Args:
            rpm_limit: Maximum requests per minute
            rpd_limit: Maximum requests per day
            max_concurrent: Maximum concurrent requests
        """
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.max_concurrent = max_concurrent
        self.logger = get_logger("RateLimiter")

        # RPM limiter (15 requests per 60 seconds)
        self.rpm_limiter = AsyncLimiter(max_rate=rpm_limit, time_period=60.0)

        # RPD limiter (1500 requests per 86400 seconds = 24 hours)
        self.rpd_limiter = AsyncLimiter(max_rate=rpd_limit, time_period=86400.0)

        # Concurrent request semaphore
        self.semaphore = asyncio.Semaphore(max_concurrent)

        # Metrics
        self.total_requests = 0
        self.total_wait_time_ms = 0.0
        self.requests_today = 0
        self.last_reset = datetime.now(UTC)

        self.logger.info(f"🚦 Rate Limiter initialized: {rpm_limit} RPM, {rpd_limit} RPD")
        self.logger.info(f"🔢 Max concurrent requests: {max_concurrent}")

    @asynccontextmanager
    async def acquire(self):
        """Async context manager to acquire rate limit slot.

        Usage:
            async with rate_limiter.acquire():
                # Your API call here
                response = await api_call()

        This will:
        1. Wait for RPM limit slot
        2. Wait for RPD limit slot
        3. Acquire semaphore for concurrent requests
        """
        start_time = time.time()

        # Wait for both RPM and RPD limits, and acquire concurrency semaphore
        async with self.rpm_limiter, self.rpd_limiter, self.semaphore:
            # Track metrics
            wait_time_ms = (time.time() - start_time) * 1000
            self.total_wait_time_ms += wait_time_ms
            self.total_requests += 1
            self.requests_today += 1

            if wait_time_ms > 100:  # Log if wait was significant
                self.logger.debug(
                    f"⏱️  Rate limit wait: {wait_time_ms:.0f}ms (RPM: {self.get_current_rpm()}/{self.rpm_limit})"
                )

            try:
                yield
            finally:
                # Cleanup happens automatically when context exits
                pass

    def get_current_rpm(self) -> int:
        """Get estimated current RPM.

        Returns:
            Approximate requests per minute in last 60 seconds
        """
        # This is an approximation - actual tracking would need a sliding window
        return min(self.total_requests, self.rpm_limit)

    def get_remaining_daily_quota(self) -> int:
        """Get remaining requests for today.

        Returns:
            Number of requests remaining in daily quota
        """
        return max(0, self.rpd_limit - self.requests_today)

    def reset_daily_counter(self) -> None:
        """Reset daily request counter (called at midnight UTC)."""
        self.requests_today = 0
        self.last_reset = datetime.now(UTC)
        self.logger.info("🔄 Daily rate limit counter reset")

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics.

        Returns:
            Dictionary with rate limiting metrics
        """
        return {
            "total_requests": self.total_requests,
            "requests_today": self.requests_today,
            "remaining_daily_quota": self.get_remaining_daily_quota(),
            "avg_wait_time_ms": (self.total_wait_time_ms / self.total_requests if self.total_requests > 0 else 0.0),
            "rpm_limit": self.rpm_limit,
            "rpd_limit": self.rpd_limit,
            "max_concurrent": self.max_concurrent,
            "last_reset": self.last_reset.isoformat(),
        }

    def is_approaching_daily_limit(self, threshold: float = 0.9) -> bool:
        """Check if approaching daily rate limit.

        Args:
            threshold: Percentage threshold (0.0-1.0) to consider as "approaching"

        Returns:
            True if current usage >= threshold * daily limit
        """
        return self.requests_today >= (self.rpd_limit * threshold)

    async def wait_for_quota_reset(self) -> None:
        """Wait until daily quota resets (midnight UTC).

        This is a blocking operation that should only be used in emergency scenarios
        when daily quota is exhausted.
        """
        now = datetime.now(UTC)
        next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # If it's already past midnight today, next reset is tomorrow
        if now >= next_midnight:
            next_midnight = next_midnight.replace(day=next_midnight.day + 1)

        wait_seconds = (next_midnight - now).total_seconds()

        self.logger.warning(f"⏳ Daily quota exhausted. Waiting {wait_seconds / 3600:.1f}h until reset...")

        await asyncio.sleep(wait_seconds)
        self.reset_daily_counter()


# Global rate limiter instance
rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance.

    Returns:
        RateLimiter instance configured from settings
    """
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = RateLimiter(
            settings.GEMINI_RPM_LIMIT,
            settings.GEMINI_RPD_LIMIT,
            settings.MAX_CONCURRENT_REQUESTS,
        )
    return rate_limiter


def reset_rate_limiter() -> None:
    """Reset global rate limiter instance.

    Used for testing or when configuration changes.
    """
    global rate_limiter
    rate_limiter = None
