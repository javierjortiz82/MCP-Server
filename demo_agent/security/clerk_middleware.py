"""Clerk Authentication Middleware for FastAPI.

Validates Clerk JWT tokens and attaches user info to request state.

Features:
- Bearer token extraction from Authorization header
- JWT validation using Clerk public keys
- User attachment to request.state for protected routes
- Public routes exemption (no auth required)
- Detailed error responses for unauthorized requests

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

from typing import Callable, Set

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from demo_agent.config.settings import config
from demo_agent.logger import logger
from demo_agent.observability.metrics import get_metrics_collector
from demo_agent.observability.structured_logger import get_structured_logger
from demo_agent.services.clerk_service import get_clerk_service


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for Clerk JWT authentication.

    Validates Clerk session tokens on protected routes.
    Attaches user information to request.state for downstream handlers.

    Public routes (no auth required):
    - /health
    - /metrics
    - /docs, /redoc, /openapi.json
    - /v1/auth/register (legacy)
    - /v1/auth/verify-otp (legacy)
    - /v1/auth/resend-otp (legacy)
    - /v1/webhooks/clerk (webhook receiver)
    - /v1/contact (public contact form)
    - /v1/booking (public demo booking form)

    Protected routes (auth required):
    - /v1/demo
    - /v1/auth/me
    - Any other /v1/* endpoints

    Request State After Authentication:
    - request.state.user: Dict with user info from JWT claims
      {
          "user_id": "user_2abc...",  # Clerk user ID
          "email": "user@example.com",
          "email_verified": true,
          "db_user_id": 123,  # PostgreSQL user.id (if exists)
          "is_authenticated": true
      }
    - request.state.is_authenticated: bool
    """

    # Public routes that don't require authentication
    PUBLIC_PATHS: Set[str] = {
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/v1/auth/register",
        "/v1/auth/register/oauth",
        "/v1/auth/verify-otp",
        "/v1/auth/resend-otp",
        "/v1/webhooks/clerk",
        "/v1/auth/check-migration",  # For legacy user migration checks
        "/v1/contact",  # Public contact form endpoint
        "/v1/booking",  # Public demo booking form endpoint
    }

    def __init__(self, app):
        """Initialize Clerk authentication middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)
        self.clerk_service = get_clerk_service()
        self.logger = get_structured_logger(__name__)
        self.metrics = get_metrics_collector()
        self.logger.info("ClerkAuthMiddleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through Clerk authentication.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response: Either error response (401) or result from next handler

        Process:
        1. Check if route is public (bypass auth)
        2. Extract Authorization header
        3. Validate Bearer token with Clerk
        4. Fetch user from database by clerk_user_id
        5. Attach user to request.state
        6. Call next handler
        """
        # Check if Clerk auth is enabled
        if not config.ENABLE_CLERK_AUTH:
            self.logger.debug("Clerk auth disabled, bypassing middleware")
            request.state.is_authenticated = False
            return await call_next(request)

        # Get request path
        path = request.url.path

        # Allow public routes without authentication
        if path in self.PUBLIC_PATHS or path.startswith("/_"):
            self.logger.debug(f"Public route accessed: {path}")
            request.state.is_authenticated = False
            return await call_next(request)

        # Allow OPTIONS requests without authentication (CORS preflight)
        # OPTIONS requests are sent by browsers before actual requests
        # Let it pass through so CORSMiddleware can add proper headers
        if request.method == "OPTIONS":
            self.logger.debug(f"OPTIONS request bypassed: {path}")
            request.state.is_authenticated = False
            return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            self.logger.warning(
                "Missing Authorization header",
                path=path,
                method=request.method
            )
            self.metrics.increment_counter("clerk_auth_missing_header")
            return self._unauthorized_response("Missing Authorization header")

        # Validate Bearer token format
        if not auth_header.startswith("Bearer "):
            self.logger.warning(
                "Invalid Authorization header format",
                auth_header=auth_header[:20]
            )
            self.metrics.increment_counter("clerk_auth_invalid_format")
            return self._unauthorized_response(
                "Invalid Authorization header format. Expected: Bearer <token>"
            )

        # Extract token
        token = auth_header.split("Bearer ", 1)[1].strip()

        if not token:
            self.logger.warning("Empty Bearer token")
            self.metrics.increment_counter("clerk_auth_empty_token")
            return self._unauthorized_response("Empty Bearer token")

        # Verify token with Clerk
        claims, error = await self.clerk_service.verify_token(token)

        if error or not claims:
            self.logger.warning(
                "Token verification failed",
                error=error,
                path=path
            )
            self.metrics.increment_counter("clerk_auth_verification_failed")
            return self._unauthorized_response(f"Authentication failed: {error}")

        # Extract user info from claims
        clerk_user_id = claims.get("sub")  # Clerk user ID
        email = claims.get("email")
        email_verified = claims.get("email_verified", False)

        if not clerk_user_id:
            self.logger.error("Token missing 'sub' claim", claims=claims)
            self.metrics.increment_counter("clerk_auth_missing_sub")
            return self._unauthorized_response("Invalid token: missing user ID")

        # If email not in JWT claims, fetch from Clerk API
        # This handles cases where JWT template doesn't include email claim
        if not email:
            self.logger.info(
                "Email not in JWT claims, fetching from Clerk API",
                clerk_user_id=clerk_user_id
            )
            clerk_user_data = await self.clerk_service.fetch_user_from_clerk_api(clerk_user_id)
            if clerk_user_data:
                email = clerk_user_data.get("email")
                self.logger.info(f"Email fetched from Clerk API: {email}")

        # Fetch user from database (optional - may not exist yet)
        # Pass email as fallback in case clerk_user_id changed
        db_user = await self.clerk_service.get_user_by_clerk_id(
            clerk_user_id,
            fallback_email=email
        )

        # Attach user info to request state
        request.state.user = {
            "clerk_user_id": clerk_user_id,
            "email": email,
            "email_verified": email_verified,
            "db_user_id": db_user["id"] if db_user else None,
            "full_name": db_user["full_name"] if db_user else claims.get("name"),
            "is_active": db_user["is_active"] if db_user else True,
            "clerk_metadata": db_user.get("clerk_metadata", {}) if db_user else {},
            "preferred_language": db_user.get("preferred_language", "es") if db_user else "es",
            "is_authenticated": True,
        }
        request.state.is_authenticated = True

        self.logger.info(
            "User authenticated successfully",
            clerk_user_id=clerk_user_id,
            email=email,
            db_user_id=request.state.user["db_user_id"],
            path=path
        )
        self.metrics.increment_counter("clerk_auth_success")

        # Check if user is active (if exists in DB)
        if db_user and not db_user["is_active"]:
            self.logger.warning(
                "Inactive user attempted access",
                user_id=db_user["id"],
                email=email
            )
            self.metrics.increment_counter("clerk_auth_inactive_user")
            return self._forbidden_response(
                "Account is inactive. Contact support for assistance."
            )

        # Proceed to next handler
        return await call_next(request)

    def _unauthorized_response(self, detail: str) -> JSONResponse:
        """Generate 401 Unauthorized response.

        Args:
            detail: Error message describing why auth failed

        Returns:
            JSONResponse: 401 response with error details
        """
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "error": "Unauthorized",
                "message": detail,
                "hint": "Include a valid Bearer token in the Authorization header",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _forbidden_response(self, detail: str) -> JSONResponse:
        """Generate 403 Forbidden response.

        Args:
            detail: Error message describing why access is forbidden

        Returns:
            JSONResponse: 403 response with error details
        """
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "success": False,
                "error": "Forbidden",
                "message": detail,
            },
        )


def get_current_user(request: Request) -> dict | None:
    """Extract current authenticated user from request state.

    Helper function for route handlers to access authenticated user.

    Args:
        request: FastAPI request object

    Returns:
        dict | None: User info if authenticated, None otherwise

    Usage in route handlers:
    ```python
    @app.post("/v1/protected")
    async def protected_route(request: Request):
        user = get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        user_id = user["db_user_id"]
        email = user["email"]
        # ... rest of handler
    ```
    """
    if not hasattr(request.state, "user"):
        return None

    if not request.state.is_authenticated:
        return None

    return request.state.user


def require_auth(request: Request) -> dict:
    """Require authentication and return user info.

    Raises HTTPException 401 if user is not authenticated.

    Args:
        request: FastAPI request object

    Returns:
        dict: Authenticated user info

    Raises:
        HTTPException: 401 if not authenticated

    Usage in route handlers:
    ```python
    from fastapi import HTTPException, Request
    from demo_agent.security.clerk_middleware import require_auth

    @app.post("/v1/protected")
    async def protected_route(request: Request):
        user = require_auth(request)  # Raises 401 if not authenticated
        user_id = user["db_user_id"]
        # ... rest of handler
    ```
    """
    from fastapi import HTTPException

    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_user_id(request: Request) -> int | None:
    """Get database user ID from authenticated user.

    Args:
        request: FastAPI request object

    Returns:
        int | None: Database user ID if authenticated and user exists in DB

    Usage:
    ```python
    user_id = get_user_id(request)
    if user_id:
        # User is authenticated and exists in database
        pass
    ```
    """
    user = get_current_user(request)
    if not user:
        return None

    return user.get("db_user_id")


def get_clerk_user_id(request: Request) -> str | None:
    """Get Clerk user ID from authenticated user.

    Args:
        request: FastAPI request object

    Returns:
        str | None: Clerk user ID (e.g., "user_2abc...") if authenticated

    Usage:
    ```python
    clerk_id = get_clerk_user_id(request)
    if clerk_id:
        # User is authenticated via Clerk
        pass
    ```
    """
    user = get_current_user(request)
    if not user:
        return None

    return user.get("clerk_user_id")
