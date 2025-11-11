"""Rate Limit Response Headers Middleware.

Adds standard HTTP rate limiting headers to API responses to inform clients
about their quota usage and remaining capacity.

SECURITY (CWE-770 mitigation - Defense in Depth): Transparent rate limit
information helps legitimate clients manage their usage and avoid quota
exhaustion, while also deterring potential abuse.

Standard Headers:
- X-RateLimit-Limit: Maximum tokens allowed per period
- X-RateLimit-Remaining: Tokens remaining in current period
- X-RateLimit-Reset: Unix timestamp when quota resets
- X-RateLimit-Used: Tokens consumed in current period
- Retry-After: Seconds until quota reset (429 responses only)

References:
- RFC 6585 (Additional HTTP Status Codes)
- IETF Draft: RateLimit Header Fields for HTTP
- GitHub API Rate Limiting
- Twitter API Rate Limiting

Author: Lab01-MCP Team
Created: 2025-11-07
Version: 1.0.0 (Security-Hardened - Phase 4)
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from demo_agent.config.settings import config
from demo_agent.logger import logger


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds rate limiting headers to API responses.

    SECURITY: Provides transparent quota information to clients, helping
    them manage usage and avoid triggering rate limits.

    Headers Added:
    - X-RateLimit-Limit: Max tokens per day
    - X-RateLimit-Remaining: Tokens remaining
    - X-RateLimit-Reset: Unix timestamp of next reset
    - X-RateLimit-Used: Tokens consumed
    - Retry-After: Seconds until reset (429 only)

    The middleware reads rate limit information from the request state
    (set by the demo_query endpoint) and adds appropriate headers.
    """

    def __init__(self, app: ASGIApp, max_tokens: int = 5000):
        """Initialize rate limit headers middleware.

        Args:
            app: ASGI application.
            max_tokens: Maximum tokens allowed per period.
        """
        super().__init__(app)
        self.max_tokens = max_tokens
        logger.info(f"RateLimitHeadersMiddleware initialized: max_tokens={max_tokens}")

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add rate limit headers to response.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware in chain.

        Returns:
            Response with rate limit headers added.
        """
        # Call next middleware/endpoint
        response = await call_next(request)

        # Only add rate limit headers to /v1/demo endpoint responses
        # (avoid adding to health checks, webhooks, etc.)
        if not request.url.path.startswith("/v1/demo"):
            return response

        # ====================================================================
        # Extract Rate Limit Information from Request State
        # ====================================================================
        # The demo_query endpoint should set these values in request.state
        # If not set, we use conservative defaults

        tokens_remaining = getattr(request.state, "rate_limit_remaining", None)
        tokens_used = getattr(request.state, "rate_limit_used", None)
        next_reset_timestamp = getattr(request.state, "rate_limit_reset", None)

        # ====================================================================
        # Add Rate Limit Headers
        # ====================================================================

        # 1. X-RateLimit-Limit: Maximum tokens allowed per period
        # This is constant for all users (configured via DEMO_MAX_TOKENS)
        response.headers["X-RateLimit-Limit"] = str(self.max_tokens)

        # 2. X-RateLimit-Remaining: Tokens remaining in current period
        # Clients should monitor this to avoid hitting quota
        if tokens_remaining is not None:
            response.headers["X-RateLimit-Remaining"] = str(max(0, tokens_remaining))
        else:
            # Conservative default: assume quota available
            response.headers["X-RateLimit-Remaining"] = str(self.max_tokens)

        # 3. X-RateLimit-Used: Tokens consumed in current period
        # Helps clients track their usage
        if tokens_used is not None:
            response.headers["X-RateLimit-Used"] = str(tokens_used)
        else:
            response.headers["X-RateLimit-Used"] = "0"

        # 4. X-RateLimit-Reset: Unix timestamp when quota resets
        # Clients can use this to schedule retries
        if next_reset_timestamp:
            # Convert ISO timestamp to Unix epoch
            try:
                if isinstance(next_reset_timestamp, str):
                    reset_dt = datetime.fromisoformat(next_reset_timestamp.replace("Z", "+00:00"))
                elif isinstance(next_reset_timestamp, datetime):
                    reset_dt = next_reset_timestamp
                else:
                    # Fallback: 24 hours from now
                    reset_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                    from datetime import timedelta
                    reset_dt += timedelta(days=1)

                reset_unix = int(reset_dt.timestamp())
                response.headers["X-RateLimit-Reset"] = str(reset_unix)

                # 5. Retry-After: Seconds until quota reset (for 429 responses only)
                # SECURITY: Helps clients implement exponential backoff correctly
                if response.status_code == 429:
                    seconds_until_reset = max(0, int((reset_dt - datetime.now(timezone.utc)).total_seconds()))
                    response.headers["Retry-After"] = str(seconds_until_reset)

            except (ValueError, AttributeError) as e:
                logger.warning(f"Error parsing reset timestamp: {e}")
                # Fallback: 24 hours from now
                from datetime import timedelta
                fallback_reset = datetime.now(timezone.utc) + timedelta(days=1)
                response.headers["X-RateLimit-Reset"] = str(int(fallback_reset.timestamp()))

        # ====================================================================
        # Additional Security Headers for Rate Limited Responses
        # ====================================================================

        # For 429 (Too Many Requests) responses, add additional guidance
        if response.status_code == 429:
            logger.info(
                f"Rate limit exceeded: "
                f"used={tokens_used}, "
                f"remaining={tokens_remaining}, "
                f"path={request.url.path}"
            )

        return response
