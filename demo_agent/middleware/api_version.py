"""API Version Headers Middleware.

Adds API version information to all HTTP responses to help clients track
compatibility, manage deprecations, and debug issues.

SECURITY (Defense-in-Depth): Version transparency helps:
- Clients detect breaking changes and adapt
- Support teams diagnose client-side issues
- Deprecation management for security patches
- Audit trails for API evolution

Headers Added:
- X-API-Version: Current API version (e.g., "1.0.0")
- X-API-Deprecated: Deprecation warning (if applicable)
- X-API-Sunset: Sunset date for deprecated endpoints
- X-Min-Client-Version: Minimum supported client version

References:
- RFC 8594: The Sunset HTTP Header Field
- Semantic Versioning 2.0.0
- API Versioning Best Practices (Microsoft, Google, Stripe)

Author: Lab01-MCP Team
Created: 2025-11-07
Version: 1.0.0 (Security-Hardened - Phase 4)
"""

from datetime import datetime
from typing import Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from demo_agent.logger import logger


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware that adds API version headers to responses.

    SECURITY: Transparent version information helps clients manage
    breaking changes, deprecations, and security updates.

    Versioning Strategy:
    - Semantic Versioning (MAJOR.MINOR.PATCH)
    - MAJOR: Breaking changes (require client updates)
    - MINOR: New features (backward compatible)
    - PATCH: Bug fixes (backward compatible)

    Deprecation Strategy:
    - Warnings added 90 days before sunset
    - Sunset date announced in advance
    - Graceful migration path provided
    """

    # Current API version (Semantic Versioning)
    API_VERSION = "1.0.0"

    # Minimum client version required (enforce compatibility)
    MIN_CLIENT_VERSION = "1.0.0"

    # Deprecated endpoints with sunset dates
    DEPRECATED_ENDPOINTS: Dict[str, str] = {
        # Example: "/v1/old-endpoint": "2025-12-31"
    }

    def __init__(
        self,
        app: ASGIApp,
        api_version: Optional[str] = None,
        min_client_version: Optional[str] = None,
        deprecated_endpoints: Optional[Dict[str, str]] = None,
    ):
        """Initialize API version middleware.

        Args:
            app: ASGI application.
            api_version: Current API version (Semantic Versioning).
            min_client_version: Minimum supported client version.
            deprecated_endpoints: Dict of path -> sunset date (ISO 8601).
        """
        super().__init__(app)
        self.api_version = api_version or self.API_VERSION
        self.min_client_version = min_client_version or self.MIN_CLIENT_VERSION
        self.deprecated_endpoints = deprecated_endpoints or self.DEPRECATED_ENDPOINTS

        logger.info(
            f"APIVersionMiddleware initialized: "
            f"version={self.api_version}, "
            f"min_client={self.min_client_version}, "
            f"deprecated_count={len(self.deprecated_endpoints)}"
        )

    def is_endpoint_deprecated(self, path: str) -> tuple[bool, Optional[str]]:
        """Check if endpoint is deprecated and get sunset date.

        Args:
            path: Request URL path.

        Returns:
            Tuple of (is_deprecated, sunset_date)
        """
        # Check exact match
        if path in self.deprecated_endpoints:
            return True, self.deprecated_endpoints[path]

        # Check prefix match (e.g., /v1/old/* matches /v1/old/endpoint)
        for deprecated_path, sunset_date in self.deprecated_endpoints.items():
            if path.startswith(deprecated_path):
                return True, sunset_date

        return False, None

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add version headers to response.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware in chain.

        Returns:
            Response with version headers added.
        """
        # Call next middleware/endpoint
        response = await call_next(request)

        # ====================================================================
        # Add API Version Headers
        # ====================================================================

        # 1. X-API-Version: Current API version
        # Clients can use this to adapt behavior based on server version
        response.headers["X-API-Version"] = self.api_version

        # 2. X-Min-Client-Version: Minimum required client version
        # Clients older than this MUST upgrade to continue using API
        response.headers["X-Min-Client-Version"] = self.min_client_version

        # ====================================================================
        # Check for Deprecated Endpoints
        # ====================================================================

        is_deprecated, sunset_date = self.is_endpoint_deprecated(request.url.path)

        if is_deprecated and sunset_date:
            # 3. X-API-Deprecated: Deprecation warning
            # Warn clients that this endpoint will be removed
            response.headers["X-API-Deprecated"] = "true"

            # 4. Sunset: RFC 8594 header indicating when endpoint will be removed
            # Format: HTTP-date (e.g., "Sat, 31 Dec 2025 23:59:59 GMT")
            try:
                sunset_dt = datetime.fromisoformat(sunset_date)
                # Format as HTTP-date (RFC 7231)
                sunset_http_date = sunset_dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
                response.headers["Sunset"] = sunset_http_date
            except ValueError:
                logger.error(f"Invalid sunset date format: {sunset_date}")

            # 5. Warning: HTTP Warning header (RFC 7234)
            # Provides human-readable deprecation message
            days_until_sunset = self._days_until_sunset(sunset_date)
            if days_until_sunset is not None:
                if days_until_sunset > 0:
                    warning_msg = (
                        f'299 - "This endpoint is deprecated and will be removed '
                        f'on {sunset_date} ({days_until_sunset} days remaining). '
                        f'Please migrate to the new API."'
                    )
                else:
                    warning_msg = (
                        f'299 - "This endpoint is deprecated and scheduled for removal. '
                        f'Please migrate to the new API immediately."'
                    )

                response.headers["Warning"] = warning_msg

            # Log deprecation usage
            logger.warning(
                f"Deprecated endpoint accessed: "
                f"path={request.url.path}, "
                f"sunset={sunset_date}, "
                f"days_remaining={days_until_sunset}"
            )

        # ====================================================================
        # Validate Client Version (if provided)
        # ====================================================================

        client_version = request.headers.get("X-Client-Version")
        if client_version:
            # Validate client version is not too old
            if not self._is_version_compatible(client_version, self.min_client_version):
                logger.warning(
                    f"Outdated client version: "
                    f"client={client_version}, "
                    f"required={self.min_client_version}, "
                    f"path={request.url.path}"
                )

                # Add warning header (don't block, just warn)
                response.headers["X-Client-Version-Warning"] = (
                    f"Your client version {client_version} is outdated. "
                    f"Minimum required: {self.min_client_version}. "
                    f"Please upgrade to ensure compatibility."
                )

        return response

    def _days_until_sunset(self, sunset_date: str) -> Optional[int]:
        """Calculate days remaining until sunset date.

        Args:
            sunset_date: ISO 8601 date string.

        Returns:
            Number of days until sunset, or None if parse fails.
        """
        try:
            sunset_dt = datetime.fromisoformat(sunset_date)
            now = datetime.now(sunset_dt.tzinfo)
            delta = sunset_dt - now
            return delta.days
        except (ValueError, AttributeError):
            return None

    def _is_version_compatible(self, client_version: str, min_version: str) -> bool:
        """Check if client version meets minimum requirements.

        Args:
            client_version: Client's version string (e.g., "1.2.3").
            min_version: Minimum required version (e.g., "1.0.0").

        Returns:
            True if client version >= min version.

        Note:
            Simple version comparison. For production, use packaging.version.
        """
        try:
            # Parse semantic versions (MAJOR.MINOR.PATCH)
            client_parts = [int(x) for x in client_version.split(".")]
            min_parts = [int(x) for x in min_version.split(".")]

            # Pad to 3 parts if needed
            while len(client_parts) < 3:
                client_parts.append(0)
            while len(min_parts) < 3:
                min_parts.append(0)

            # Compare major.minor.patch
            return tuple(client_parts) >= tuple(min_parts)

        except (ValueError, AttributeError):
            # If version parsing fails, assume compatible (lenient)
            return True


def create_api_version_middleware(
    api_version: Optional[str] = None,
    min_client_version: Optional[str] = None,
    deprecated_endpoints: Optional[Dict[str, str]] = None,
) -> APIVersionMiddleware:
    """Factory function to create API version middleware.

    Args:
        api_version: Current API version.
        min_client_version: Minimum required client version.
        deprecated_endpoints: Dict of deprecated paths with sunset dates.

    Returns:
        Configured APIVersionMiddleware instance.

    Example:
        ```python
        app.add_middleware(
            APIVersionMiddleware,
            api_version="2.0.0",
            min_client_version="1.5.0",
            deprecated_endpoints={
                "/v1/old-endpoint": "2025-12-31"
            }
        )
        ```
    """
    return APIVersionMiddleware(
        api_version=api_version,
        min_client_version=min_client_version,
        deprecated_endpoints=deprecated_endpoints,
    )
