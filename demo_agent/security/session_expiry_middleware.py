"""Session Expiration Middleware for FastAPI.

Validates that user sessions haven't expired based on:
- Idle timeout: Inactivity period
- TTL (Time-To-Live): Total session duration
- Absolute timeout: Maximum lifetime regardless of activity

Features:
- Automatic session expiration check on each request
- Activity timestamp updates
- Expired session invalidation
- Detailed expiration reasons in error responses

Author: Lab01-MCP Team
Created: 2025-11-18
Version: 1.0.0
"""

from collections.abc import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware

from demo_agent.config.settings import config
from demo_agent.db.models import DemoSession
from demo_agent.logger import logger
from demo_agent.services.session_service import SessionService


class SessionExpiryMiddleware(BaseHTTPMiddleware):
    """Middleware for checking session expiration.

    Validates that user sessions are still valid before processing requests.
    Updates activity timestamp on each request and invalidates expired sessions.

    Public routes (exempt from session validation):
    - /health
    - /metrics
    - /docs, /redoc, /openapi.json
    - /v1/auth/* (authentication endpoints)
    - /v1/webhooks/* (webhook receivers)
    - /v1/contact (public endpoints)
    - /v1/booking (public endpoints)
    """

    # Public routes exempt from session validation
    PUBLIC_PATHS: set[str] = {
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/v1/auth/register",
        "/v1/auth/register/oauth",
        "/v1/auth/verify-otp",
        "/v1/auth/resend-otp",
        "/v1/auth/login",
        "/v1/auth/logout",
        "/v1/webhooks/clerk",
        "/v1/contact",
        "/v1/booking",
    }

    def __init__(self, app):
        """Initialize session expiry middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)
        # Create database engine
        self.engine = create_engine(config.DATABASE_URL, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info("SessionExpiryMiddleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and validate session expiration.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response: Either error response (401) if expired, or result from next handler

        Process:
        1. Check if route is public (bypass session check)
        2. Get session from request headers
        3. Check if session exists in database
        4. Verify if session has expired
        5. Update activity timestamp if still valid
        6. Invalidate expired sessions
        """
        # Get request path
        path = request.url.path

        # Skip session validation for public routes
        if path in self.PUBLIC_PATHS or path.startswith("/_"):
            return await call_next(request)

        # Skip session validation for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Get session ID from headers (can be in X-Session-ID or Authorization)
        session_id = request.headers.get("X-Session-ID") or request.headers.get("X-Session")

        if not session_id:
            logger.debug(f"No session ID in headers for protected route: {path}")
            # Don't require session ID here - let Clerk middleware handle auth
            # Session validation is optional for Clerk-authenticated users
            return await call_next(request)

        # Query session from database
        db = None
        try:
            db = self.SessionLocal()
            session: DemoSession = db.query(DemoSession).filter(
                DemoSession.session_id == session_id
            ).first()

            if not session:
                logger.warning(f"Session not found: {session_id}")
                return self._unauthorized_response(
                    "Session not found",
                    "session_not_found"
                )

            # Check if session has expired
            if SessionService.is_session_expired(session):
                expiry_reason = SessionService.get_expiration_reason(session)
                logger.warning(
                    "Session expired",
                    session_id=session_id,
                    reason=expiry_reason,
                    path=path
                )

                # Invalidate the expired session
                SessionService.invalidate_session(db, session)

                return self._unauthorized_response(
                    f"Session expired ({expiry_reason}). Please log in again.",
                    expiry_reason or "session_expired"
                )

            # Session is valid - update activity timestamp
            SessionService.update_session_activity(db, session)

            # Attach session to request for downstream handlers
            request.state.session = session
            request.state.session_id = session_id

            logger.debug(
                "Session validated and activity updated",
                session_id=session_id,
                path=path
            )

        except Exception as e:
            logger.error(f"Error validating session: {str(e)}", exc_info=True)
            # On error, still allow request to proceed (fail open)
            return await call_next(request)

        finally:
            if db:
                db.close()

        # Proceed to next handler
        return await call_next(request)

    def _unauthorized_response(self, detail: str, reason: str = "session_expired") -> JSONResponse:
        """Generate 401 Unauthorized response for expired session.

        Args:
            detail: Error message describing the expiration
            reason: Machine-readable reason code

        Returns:
            JSONResponse: 401 response with session expiration details
        """
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "error": "SessionExpired",
                "message": detail,
                "reason": reason,
                "action": "login",
                "hint": "Your session has expired. Please log in again with OTP verification.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_session_from_request(request: Request) -> DemoSession | None:
    """Extract session from request state.

    Helper function for route handlers to access the validated session.

    Args:
        request: FastAPI request object

    Returns:
        DemoSession | None: Session if validated, None otherwise
    """
    if not hasattr(request.state, "session"):
        return None

    return request.state.session


def get_session_id_from_request(request: Request) -> str | None:
    """Extract session ID from request state.

    Args:
        request: FastAPI request object

    Returns:
        str | None: Session ID if present, None otherwise
    """
    if not hasattr(request.state, "session_id"):
        return None

    return request.state.session_id
