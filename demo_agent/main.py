"""Demo Agent Main Entry Point.

FastAPI application for demo agent with token-bucket rate limiting.

FIX 3.2: Async database integration
- Updated lifespan to initialize async connection pool
- Updated all service initialization for async operations

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.1.0 (Async)
Refactored: 2025-11-10 (Modular routes)
"""

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from demo_agent.agent import DemoAgent
from demo_agent.config.settings import config
from demo_agent.db.connection import close_db, init_db
from demo_agent.logger import logger
from demo_agent.middleware.api_version import APIVersionMiddleware
from demo_agent.middleware.rate_limit_headers import RateLimitHeadersMiddleware
from demo_agent.middleware.request_size_limit import RequestSizeLimitMiddleware
from demo_agent.middleware.security_headers import SecurityHeadersMiddleware
from demo_agent.observability.context import (
    clear_request_context,
    create_request_context,
)
from demo_agent.observability.correlation import CorrelationID
from demo_agent.observability.metrics import get_metrics_collector
from demo_agent.security.clerk_middleware import ClerkAuthMiddleware
from demo_agent.security.session_expiry_middleware import SessionExpiryMiddleware
from demo_agent.services.email_integration import EmailIntegrationService
from demo_agent.services.otp_service import OTPService
from demo_agent.services.user_service import UserService

# Import modular routers
from demo_agent.routes import (
    auth_router,
    demo_router,
    forms_router,
    health_router,
    webhooks_router,
)


# ============================================================================
# Lifespan Events
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events.

    Initializes all services and database connections on startup,
    and properly closes them on shutdown.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control to the application.
    """
    # Startup
    logger.info(
        f"🚀 Demo Agent starting on {config.DEMO_AGENT_HOST}:{config.DEMO_AGENT_PORT}"
    )
    logger.info(
        f"📊 Demo Config: {config.DEMO_MAX_TOKENS} tokens/day, {config.DEMO_COOLDOWN_HOURS}h cooldown"
    )
    logger.info(
        f"🔐 Security: CAPTCHA={config.ENABLE_CAPTCHA}, Fingerprint={config.ENABLE_FINGERPRINT}"
    )

    try:
        # FIX 3.2: Initialize async database connection pool
        await init_db()
        logger.info("✅ Database connection pool initialized (asyncpg)")

        # Initialize services and store in app state
        app.state.demo_agent = DemoAgent()
        logger.info("✅ Demo Agent initialized")

        app.state.user_service = UserService()
        logger.info("✅ User Service initialized")

        app.state.otp_service = OTPService()
        logger.info("✅ OTP Service initialized")

        app.state.email_service = EmailIntegrationService()
        logger.info("✅ Email Integration Service initialized")

    except Exception as e:
        logger.exception(f"Failed to initialize demo agent: {e}")
        raise RuntimeError(f"Demo Agent startup failed: {e}") from e

    yield

    # Shutdown
    logger.info("🛑 Demo Agent shutting down...")
    await close_db()
    logger.info("✅ Database connection pool closed")


# ============================================================================
# FastAPI Application
# ============================================================================


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Sets up all middleware, routers, and observability components.

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Demo Agent API",
        description="FAQ-based demo agent with token-bucket rate limiting",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ========================================================================
    # Middleware Configuration (Order matters: first added = last executed)
    # ========================================================================

    # Request Size Limit (Phase 4 - LOW Priority)
    # SECURITY (CWE-400 fix): Prevent DoS via oversized request payloads
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size=50 * 1024,  # 50 KB default
        endpoint_limits={
            "/v1/demo": 10 * 1024,  # 10 KB for user queries
            "/v1/webhooks/clerk": 100 * 1024,  # 100 KB for webhooks
            "/v1/auth/register": 10 * 1024,  # 10 KB for registration
        },
    )
    logger.info("Request size limit middleware registered")

    # CORS Middleware (SECURITY HARDENED)
    # SECURITY (CWE-942 fix): Validate and restrict CORS configuration
    cors_origins_raw = [origin.strip() for origin in config.CORS_ALLOW_ORIGINS.split(",")]
    cors_origins = []

    for origin in cors_origins_raw:
        if not origin:
            continue

        # SECURITY: Reject wildcard origins in production
        if "*" in origin:
            logger.error(
                f"SECURITY ERROR: Wildcard origin '{origin}' is not allowed. "
                "Specify exact origins (e.g., https://app.example.com)"
            )
            raise ValueError(
                f"Wildcard CORS origin '{origin}' is forbidden for security. "
                "Use exact origins instead."
            )

        # SECURITY: Validate origin is a valid URL
        if not origin.startswith(("http://", "https://")):
            logger.error(
                f"SECURITY ERROR: Invalid origin '{origin}' must start with http:// or https://"
            )
            raise ValueError(f"Invalid CORS origin '{origin}' - must be a complete URL")

        cors_origins.append(origin)

    if not cors_origins:
        logger.warning(
            "No CORS origins configured. API will reject all cross-origin requests. "
            "Set CORS_ALLOW_ORIGINS in environment variables."
        )

    # SECURITY (CWE-942 fix): Restrict methods if credentials are allowed
    if config.CORS_ALLOW_METHODS == "*":
        if config.CORS_ALLOW_CREDENTIALS:
            logger.warning(
                "SECURITY WARNING: CORS allows all methods (*) with credentials. "
                "This is acceptable for development but should be restricted in production."
            )
        cors_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    else:
        cors_methods = [
            method.strip().upper() for method in config.CORS_ALLOW_METHODS.split(",")
        ]

    # SECURITY (CWE-942 fix): Restrict headers if credentials are allowed
    if config.CORS_ALLOW_HEADERS == "*":
        if config.CORS_ALLOW_CREDENTIALS:
            logger.warning(
                "SECURITY WARNING: CORS allows all headers (*) with credentials. "
                "For production, restrict to: Authorization, Content-Type, X-Request-ID"
            )
        cors_headers = [
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Request-ID",
            "X-Correlation-ID",
            "User-Agent",
        ]
    else:
        cors_headers = [
            header.strip() for header in config.CORS_ALLOW_HEADERS.split(",")
        ]

    logger.info(
        f"CORS configured: origins={len(cors_origins)}, "
        f"methods={len(cors_methods)}, "
        f"headers={len(cors_headers)}, "
        f"credentials={config.CORS_ALLOW_CREDENTIALS}"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=config.CORS_ALLOW_CREDENTIALS,
        allow_methods=cors_methods,
        allow_headers=cors_headers,
    )

    # Security Headers Middleware
    # SECURITY (CWE-1021 fix): Add OWASP recommended security headers
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=True,  # Enforce HTTPS (only applied on HTTPS requests)
        hsts_max_age=31536000,  # 1 year
        enable_csp=True,  # Content Security Policy
        csp_report_only=False,  # Block violations (set True for testing)
    )
    logger.info("Security headers middleware registered")

    # Rate Limit Headers Middleware (Phase 4 - LOW Priority)
    # SECURITY (CWE-770 defense-in-depth): Add rate limit headers to responses
    app.add_middleware(RateLimitHeadersMiddleware, max_tokens=config.DEMO_MAX_TOKENS)
    logger.info("Rate limit headers middleware registered")

    # API Version Headers Middleware (Phase 4 - LOW Priority)
    app.add_middleware(
        APIVersionMiddleware,
        api_version="1.0.0",
        min_client_version="1.0.0",
        deprecated_endpoints={},  # No deprecated endpoints yet
    )
    logger.info("API version headers middleware registered")

    # Clerk Authentication Middleware
    # IMPORTANT: Added AFTER CORSMiddleware so it executes BEFORE CORS
    app.add_middleware(ClerkAuthMiddleware)
    logger.info("✅ Clerk authentication middleware registered")

    # Session Expiration Middleware (NEW - SECURITY)
    # SECURITY: Validates session expiration on protected routes
    # Implements OWASP three-tier session expiration logic:
    # 1. Idle timeout: Expires if inactive
    # 2. TTL (Time-To-Live): Expires after total duration
    # 3. Absolute timeout: Never expires longer than max lifetime
    app.add_middleware(SessionExpiryMiddleware)
    logger.info(
        f"✅ Session expiration middleware registered "
        f"(TTL={config.SESSION_TTL_MINUTES}m, "
        f"Idle={config.SESSION_IDLE_TIMEOUT_MINUTES}m, "
        f"Absolute={config.SESSION_ABSOLUTE_TIMEOUT_MINUTES}m)"
    )

    logger.info(f"✅ CORS configured: {len(cors_origins)} allowed origins")
    logger.debug(f"   Origins: {cors_origins}")

    # ========================================================================
    # Observability Middleware
    # ========================================================================

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        """Middleware for request-level observability and context management.

        Provides:
        - Correlation ID generation/extraction
        - Request context creation
        - Request latency metrics
        - Automatic context cleanup

        Args:
            request: FastAPI request object.
            call_next: Next middleware/handler in chain.

        Returns:
            Response: HTTP response with observability headers.
        """
        # 1. Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        CorrelationID.set(correlation_id)

        # 2. Create request context
        user_key = request.headers.get("X-User-Key")
        ctx = create_request_context(
            user_key=user_key,
            ip_address=request.client.host if request.client else None,
            method=request.method,
            path=request.url.path,
        )

        # 3. Track request with metrics
        metrics = get_metrics_collector()

        try:
            # Record operation latency
            async with metrics.record_latency_async(
                "http_request", tags={"method": request.method, "path": request.url.path}
            ):
                response = await call_next(request)

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            metrics.increment_counter("http_requests_successful")
            return response

        except Exception as e:
            logger.exception("Error in request", extra={"correlation_id": correlation_id})
            metrics.increment_counter("http_requests_errors")
            raise

        finally:
            # 4. Clean up context
            clear_request_context()
            CorrelationID.clear()

    # ========================================================================
    # Root Information Endpoint
    # ========================================================================

    @app.get("/", tags=["Info"])
    async def root():
        """API information endpoint.

        Returns:
            dict: Service information and available endpoints.
        """
        return {
            "service": "Demo Agent API",
            "version": "2.0.0",
            "description": "FAQ-based demo with token-bucket rate limiting and user authentication",
            "endpoints": {
                "health": "/health",
                "register": "/v1/auth/register (POST)",
                "register_oauth": "/v1/auth/register/oauth (POST)",
                "verify_otp": "/v1/auth/verify-otp (POST)",
                "resend_otp": "/v1/auth/resend-otp (POST)",
                "demo_query": "/v1/demo (POST)",
                "quota_status": "/v1/demo/status (GET)",
            },
        }

    # ========================================================================
    # Register Modular Routers
    # ========================================================================

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(webhooks_router)
    app.include_router(demo_router)
    app.include_router(forms_router)

    logger.info("✅ All routers registered successfully")

    return app


# ============================================================================
# Application Instance
# ============================================================================

app = create_app()


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "demo_agent.main:app",
        host=config.DEMO_AGENT_HOST,
        port=config.DEMO_AGENT_PORT,
        reload=config.DEBUG_MODE,
        log_level=config.LOG_LEVEL.lower(),
    )
