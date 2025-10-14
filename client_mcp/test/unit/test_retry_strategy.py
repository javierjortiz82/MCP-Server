"""Unit tests for RetryStrategy."""

import pytest

from strategies.retry import RetryConfig, RetryStrategy, retry_with_backoff


class TestRetryConfig:
    """Test suite for RetryConfig dataclass."""

    def test_default_values(self):
        """Test RetryConfig default values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.initial_delay_ms == 100.0
        assert config.max_delay_ms == 5000.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_values(self):
        """Test RetryConfig with custom values."""
        config = RetryConfig(
            max_attempts=5,
            initial_delay_ms=200.0,
            max_delay_ms=10000.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_attempts == 5
        assert config.initial_delay_ms == 200.0
        assert config.max_delay_ms == 10000.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


class TestRetryStrategy:
    """Test suite for RetryStrategy class."""

    def test_initialization_default(self):
        """Test RetryStrategy initialization with defaults."""
        strategy = RetryStrategy()

        assert strategy.config.max_attempts == 3
        assert strategy.logger is not None

    def test_initialization_custom_config(self):
        """Test RetryStrategy initialization with custom config."""
        config = RetryConfig(max_attempts=5)
        strategy = RetryStrategy(config)

        assert strategy.config.max_attempts == 5

    def test_initialization_custom_logger(self):
        """Test RetryStrategy initialization with custom logger."""
        import logging

        custom_logger = logging.getLogger("test")
        strategy = RetryStrategy(logger=custom_logger)

        assert strategy.logger == custom_logger

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_attempt(self):
        """Test successful execution on first attempt."""
        strategy = RetryStrategy()

        async def success_func():
            return "success"

        result = await strategy.execute_with_retry(success_func)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_retries(self):
        """Test successful execution after some retries."""
        config = RetryConfig(max_attempts=3, initial_delay_ms=10.0)
        strategy = RetryStrategy(config)

        attempts = {"count": 0}

        async def retry_then_success():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await strategy.execute_with_retry(retry_then_success)

        assert result == "success"
        assert attempts["count"] == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_all_attempts_fail(self):
        """Test all retry attempts fail."""
        config = RetryConfig(max_attempts=3, initial_delay_ms=10.0)
        strategy = RetryStrategy(config)

        async def always_fail():
            raise ValueError("Permanent error")

        with pytest.raises(ValueError, match="Permanent error"):
            await strategy.execute_with_retry(always_fail)

    @pytest.mark.asyncio
    async def test_execute_with_retry_non_retryable_exception(self):
        """Test non-retryable exception is raised immediately."""
        strategy = RetryStrategy()

        async def fail_with_type_error():
            raise TypeError("Type error")

        # Only retry on ValueError
        with pytest.raises(TypeError, match="Type error"):
            await strategy.execute_with_retry(
                fail_with_type_error, retryable_exceptions=(ValueError,)
            )

    @pytest.mark.asyncio
    async def test_execute_with_retry_respects_max_attempts(self):
        """Test retry respects max_attempts."""
        config = RetryConfig(max_attempts=2, initial_delay_ms=10.0)
        strategy = RetryStrategy(config)

        attempts = {"count": 0}

        async def count_attempts():
            attempts["count"] += 1
            raise ValueError("Error")

        with pytest.raises(ValueError):
            await strategy.execute_with_retry(count_attempts)

        assert attempts["count"] == 2

    def test_calculate_backoff_first_attempt(self):
        """Test backoff calculation for first attempt."""
        config = RetryConfig(initial_delay_ms=100.0, jitter=False)
        strategy = RetryStrategy(config)

        delay = strategy._calculate_backoff(1)

        assert delay == 100.0

    def test_calculate_backoff_exponential(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(initial_delay_ms=100.0, exponential_base=2.0, jitter=False)
        strategy = RetryStrategy(config)

        delay1 = strategy._calculate_backoff(1)
        delay2 = strategy._calculate_backoff(2)
        delay3 = strategy._calculate_backoff(3)

        assert delay1 == 100.0  # 100 * 2^0
        assert delay2 == 200.0  # 100 * 2^1
        assert delay3 == 400.0  # 100 * 2^2

    def test_calculate_backoff_capped_at_max(self):
        """Test backoff is capped at max_delay_ms."""
        config = RetryConfig(
            initial_delay_ms=100.0,
            max_delay_ms=500.0,
            exponential_base=2.0,
            jitter=False,
        )
        strategy = RetryStrategy(config)

        delay = strategy._calculate_backoff(10)  # Would be 51200 without cap

        assert delay == 500.0

    def test_calculate_backoff_with_jitter(self):
        """Test backoff with jitter adds randomness."""
        config = RetryConfig(initial_delay_ms=100.0, jitter=True)
        strategy = RetryStrategy(config)

        delays = [strategy._calculate_backoff(1) for _ in range(10)]

        # All delays should be different (with high probability)
        assert len(set(delays)) > 1
        # All delays should be within jitter range (75-125ms)
        assert all(75.0 <= d <= 125.0 for d in delays)

    def test_is_retryable_error_timeout(self):
        """Test timeout error is retryable."""
        strategy = RetryStrategy()

        error = Exception("Connection timeout occurred")
        assert strategy.is_retryable_error(error) is True

    def test_is_retryable_error_connection(self):
        """Test connection error is retryable."""
        strategy = RetryStrategy()

        error = Exception("Connection refused")
        assert strategy.is_retryable_error(error) is True

    def test_is_retryable_error_network(self):
        """Test network error is retryable."""
        strategy = RetryStrategy()

        error = Exception("Network error occurred")
        assert strategy.is_retryable_error(error) is True

    def test_is_retryable_error_temporary(self):
        """Test temporary error is retryable."""
        strategy = RetryStrategy()

        error = Exception("Temporary failure")
        assert strategy.is_retryable_error(error) is True

    def test_is_retryable_error_unavailable(self):
        """Test unavailable error is retryable."""
        strategy = RetryStrategy()

        error = Exception("Service unavailable")
        assert strategy.is_retryable_error(error) is True

    def test_is_retryable_error_not_retryable(self):
        """Test non-retryable error."""
        strategy = RetryStrategy()

        error = Exception("Invalid parameter")
        assert strategy.is_retryable_error(error) is False

    def test_is_retryable_error_case_insensitive(self):
        """Test error matching is case insensitive."""
        strategy = RetryStrategy()

        error = Exception("CONNECTION TIMEOUT")
        assert strategy.is_retryable_error(error) is True


class TestRetryWithBackoffFunction:
    """Test suite for retry_with_backoff convenience function."""

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """Test retry_with_backoff with successful execution."""

        async def success_func():
            return "result"

        result = await retry_with_backoff(success_func)

        assert result == "result"

    @pytest.mark.asyncio
    async def test_retry_with_backoff_with_retries(self):
        """Test retry_with_backoff retries on failure."""
        attempts = {"count": 0}

        async def retry_then_success():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise ValueError("Error")
            return "success"

        result = await retry_with_backoff(
            retry_then_success, max_attempts=3, initial_delay_ms=10.0
        )

        assert result == "success"
        assert attempts["count"] == 2

    @pytest.mark.asyncio
    async def test_retry_with_backoff_custom_params(self):
        """Test retry_with_backoff with custom parameters."""

        async def success_func():
            return "done"

        result = await retry_with_backoff(
            success_func,
            max_attempts=5,
            initial_delay_ms=50.0,
            max_delay_ms=1000.0,
        )

        assert result == "done"

    @pytest.mark.asyncio
    async def test_retry_with_backoff_all_fail(self):
        """Test retry_with_backoff when all attempts fail."""

        async def always_fail():
            raise RuntimeError("Failed")

        with pytest.raises(RuntimeError, match="Failed"):
            await retry_with_backoff(always_fail, max_attempts=2, initial_delay_ms=10.0)
