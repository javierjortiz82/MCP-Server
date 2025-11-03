"""Demo Agent Main Entry Point.

FastAPI application for demo agent with token-bucket rate limiting.

FIX 3.2: Async database integration
- Updated lifespan to initialize async connection pool
- Updated all service initialization for async operations

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.1.0 (Async)
"""

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from demo_agent.agent import DemoAgent
from demo_agent.config.settings import config
from demo_agent.db.connection import close_db, get_db, init_db
from demo_agent.logger import logger
from demo_agent.models.requests import DemoRequest
from demo_agent.models.responses import DemoResponse
from demo_agent.models.user import (
    OAuthRegisterRequest,
    OTPPurpose,
    RegisterResponse,
    ResendOTPRequest,
    ResendOTPResponse,
    UserRegisterRequest,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from demo_agent.services.email_integration import EmailIntegrationService
from demo_agent.services.otp_service import OTPService
from demo_agent.services.user_service import UserService
from demo_agent import auth_endpoints

# ============================================================================
# Global State
# ============================================================================

demo_agent: DemoAgent | None = None
user_service: UserService | None = None
otp_service: OTPService | None = None
email_service: EmailIntegrationService | None = None


# ============================================================================
# Lifespan Events
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    global demo_agent, user_service, otp_service, email_service

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

        # Initialize services
        demo_agent = DemoAgent()
        logger.info("✅ Demo Agent initialized")

        user_service = UserService()
        logger.info("✅ User Service initialized")

        otp_service = OTPService()
        logger.info("✅ OTP Service initialized")

        email_service = EmailIntegrationService()
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
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Demo Agent API",
        description="FAQ-based demo agent with token-bucket rate limiting",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ========================================================================
    # Health Check Endpoint
    # ========================================================================

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for Docker healthcheck."""
        return {
            "status": "ok",
            "service": "demo_agent",
            "version": "1.0.0",
        }

    # ========================================================================
    # Root Information Endpoint
    # ========================================================================

    @app.get("/", tags=["Info"])
    async def root():
        """API information endpoint."""
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
    # Authentication Endpoints
    # ========================================================================

    @app.post(
        "/v1/auth/register",
        response_model=RegisterResponse,
        tags=["Authentication"],
    )
    async def register(request_data: UserRegisterRequest, request: Request):
        """Register new user with email/password.

        Creates user account and sends OTP verification email.

        Request:
        ```json
        {
          "email": "user@example.com",
          "full_name": "John Doe",
          "password": "SecurePassword123",
          "preferred_language": "es",
          "registration_source": "web"
        }
        ```

        Response:
        ```json
        {
          "success": true,
          "message": "Registration successful! Check your email.",
          "user": { ... },
          "requires_verification": true,
          "verification_sent": true
        }
        ```
        """
        global user_service, otp_service, email_service
        if not user_service or not otp_service or not email_service:
            raise HTTPException(status_code=500, detail="Services not initialized")

        return await auth_endpoints.register_email(
            request_data=request_data,
            client_request=request,
            user_service=user_service,
            otp_service=otp_service,
            email_service=email_service,
        )

    @app.post(
        "/v1/auth/register/oauth",
        response_model=RegisterResponse,
        tags=["Authentication"],
    )
    async def register_with_oauth(
        request_data: OAuthRegisterRequest, request: Request
    ):
        """Register new user with OAuth provider (Google, Apple).

        OAuth users are automatically verified (email verified by provider).

        Request:
        ```json
        {
          "email": "user@gmail.com",
          "full_name": "John Doe",
          "auth_provider": "google",
          "oauth_provider_id": "1234567890",
          "preferred_language": "es",
          "registration_source": "web"
        }
        ```

        Response:
        ```json
        {
          "success": true,
          "message": "Registration successful! Your account is now active.",
          "user": { ... },
          "requires_verification": false,
          "verification_sent": false
        }
        ```
        """
        global user_service
        if not user_service:
            raise HTTPException(status_code=500, detail="User service not initialized")

        return await auth_endpoints.register_oauth(
            request_data=request_data,
            client_request=request,
            user_service=user_service,
        )

    @app.post(
        "/v1/auth/verify-otp",
        response_model=VerifyOTPResponse,
        tags=["Authentication"],
    )
    async def verify_otp_code(request_data: VerifyOTPRequest):
        """Verify OTP code and activate user account.

        Request:
        ```json
        {
          "email": "user@example.com",
          "otp_code": "123456",
          "purpose": "email_verification"
        }
        ```

        Response (Success):
        ```json
        {
          "success": true,
          "message": "Email verified successfully!",
          "is_active": true,
          "user": { ... }
        }
        ```

        Response (Invalid):
        ```json
        {
          "success": false,
          "message": "Invalid code. 2 attempts remaining.",
          "is_active": false
        }
        ```
        """
        global user_service, otp_service
        if not user_service or not otp_service:
            raise HTTPException(status_code=500, detail="Services not initialized")

        return await auth_endpoints.verify_otp(
            request_data=request_data,
            user_service=user_service,
            otp_service=otp_service,
        )

    @app.post(
        "/v1/auth/resend-otp",
        response_model=ResendOTPResponse,
        tags=["Authentication"],
    )
    async def resend_otp_code(request_data: ResendOTPRequest, request: Request):
        """Resend OTP verification email.

        Request:
        ```json
        {
          "email": "user@example.com",
          "purpose": "email_verification"
        }
        ```

        Response (Success):
        ```json
        {
          "success": true,
          "message": "Verification code sent!",
          "expires_at": "2025-11-01T12:00:00Z"
        }
        ```

        Response (Rate Limited):
        ```json
        {
          "success": false,
          "message": "Please wait 45 seconds before requesting a new code.",
          "cooldown_seconds": 45
        }
        ```
        """
        global user_service, otp_service, email_service
        if not user_service or not otp_service or not email_service:
            raise HTTPException(status_code=500, detail="Services not initialized")

        return await auth_endpoints.resend_otp(
            request_data=request_data,
            client_request=request,
            user_service=user_service,
            otp_service=otp_service,
            email_service=email_service,
        )

    # ========================================================================
    # Demo Query Endpoint
    # ========================================================================

    @app.post("/v1/demo", response_model=DemoResponse, tags=["Demo"])
    async def demo_query(request: DemoRequest):
        """Process a demo query with token-bucket rate limiting.

        Request:
        ```json
        {
          "user_id": "user_123",
          "session_id": "sess_abc",
          "input": "¿Cuánto cuesta un laptop?",
          "language": "es",
          "metadata": {
            "ip": "203.0.113.42",
            "user_agent": "Mozilla/5.0...",
            "fingerprint": "hash123"
          }
        }
        ```

        Response (Success):
        ```json
        {
          "success": true,
          "response": "Los laptops varían entre $500 y $3000...",
          "tokens_used": 250,
          "tokens_remaining": 4750,
          "warning": {
            "is_warning": false,
            "message": null,
            "percentage_used": 5
          },
          "session_id": "sess_abc",
          "created_at": "2025-10-31T12:30:45Z"
        }
        ```

        Response (Quota Exceeded - 429):
        ```json
        {
          "success": false,
          "error": "demo_quota_exceeded",
          "message": "Demo bloqueada. Límite de 5,000 tokens alcanzado...",
          "retry_after_seconds": 64800,
          "blocked_until": "2025-11-01T12:30:45Z"
        }
        ```
        """
        try:
            global demo_agent, user_service
            if not demo_agent or not user_service:
                logger.error("Services not initialized")
                raise HTTPException(
                    status_code=500,
                    detail="Services not initialized",
                )

            # STEP 1: Validate user exists and is active
            # FIX: Lookup by user_id (not email) for security
            # Users should only access their own quota, verified via token
            user_query = """
                SELECT id, email, is_active, is_email_verified, is_suspended, is_deleted
                FROM :SCHEMA_NAME.demo_users
                WHERE id = %s
            """
            user_result = user_service.db.execute_one(user_query, (request.user_id,))

            if not user_result:
                logger.warning(f"User ID {request.user_id} not found")
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "error": "user_not_found",
                        "message": "User account not found. Please register first.",
                    },
                )

            # Check if user is active and verified
            if not user_result.get("is_active"):
                logger.warning(f"User ID {request.user_id} is not active")
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "error": "account_not_active",
                        "message": (
                            "Your account is not active. "
                            "Please verify your email address first."
                        ),
                    },
                )

            if not user_result.get("is_email_verified"):
                logger.warning(f"User ID {request.user_id} email not verified")
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "error": "email_not_verified",
                        "message": "Please verify your email address first.",
                    },
                )

            if user_result.get("is_suspended"):
                logger.warning(f"User ID {request.user_id} is suspended")
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "error": "account_suspended",
                        "message": "Your account has been suspended.",
                    },
                )

            if user_result.get("is_deleted"):
                logger.warning(f"User ID {request.user_id} is deleted")
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "error": "account_deleted",
                        "message": "Your account has been deleted.",
                    },
                )

            # STEP 2: Use user_id as user_key for token tracking
            user_key = str(request.user_id)
            user_email = user_result.get("email")

            # Generate session_id if not provided
            session_id = request.session_id or str(uuid4())

            logger.info(f"Demo query from active user: {user_email} (ID: {request.user_id})")

            # Process query
            response_text, tokens_used, warning, error_msg = (
                await demo_agent.process_query(
                    user_input=request.input,
                    user_key=user_key,
                    language=request.language or "es",
                    ip_address=request.metadata.ip,
                    user_agent=request.metadata.user_agent,
                    client_fingerprint=request.metadata.fingerprint,
                )
            )

            # If query was blocked, return error response
            if error_msg:
                status_code = 429 if "quota" in error_msg else 403
                return JSONResponse(
                    status_code=status_code,
                    content={
                        "success": False,
                        "error": (
                            "demo_quota_exceeded"
                            if "quota" in error_msg
                            else "suspicious_behavior_detected"
                        ),
                        "message": error_msg,
                        "retry_after_seconds": 86400 if "quota" in error_msg else 300,
                    },
                )

            # Return successful response
            from datetime import datetime, timezone

            return DemoResponse(
                success=True,
                response=response_text,
                tokens_used=tokens_used,
                tokens_remaining=await get_tokens_remaining(user_key),
                warning=warning,
                session_id=session_id,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error in demo_query: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # ========================================================================
    # Quota Status Endpoint
    # ========================================================================

    @app.get("/v1/demo/status", tags=["Demo"])
    async def demo_status(
        user_id: str | None = Query(None, description="Authenticated user ID"),
        session_id: str | None = Query(None, description="Anonymous session ID"),
        fingerprint: str | None = Query(None, description="Client fingerprint"),
    ):
        """Get user's current quota status.

        Query Parameters:
        - `user_id`: Authenticated user ID (or)
        - `session_id`: Anonymous session ID (or)
        - `fingerprint`: Client fingerprint

        Response:
        ```json
        {
          "tokens_used": 1250,
          "tokens_remaining": 3750,
          "percentage_used": 25,
          "requests_count": 5,
          "is_blocked": false,
          "blocked_until": null,
          "last_reset": "2025-10-31T00:00:00Z",
          "next_reset": "2025-11-01T00:00:00Z"
        }
        ```
        """
        try:
            global demo_agent
            if not demo_agent:
                raise HTTPException(
                    status_code=500,
                    detail="Demo agent not initialized",
                )

            # Generate user_key from available identifiers
            user_key = user_id or session_id or fingerprint
            if not user_key:
                raise HTTPException(
                    status_code=400,
                    detail="Provide user_id, session_id, or fingerprint",
                )

            # Get quota status
            status = await demo_agent.get_user_status(user_key)
            return status

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error in demo_status: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # ========================================================================
    # CAPTCHA Verification Endpoint
    # ========================================================================

    @app.post("/v1/demo/verify-captcha", tags=["Security"])
    async def verify_captcha(
        token: str = Query(..., description="reCAPTCHA v3 response token"),
        user_id: str | None = Query(None, description="Authenticated user ID"),
        session_id: str | None = Query(None, description="Anonymous session ID"),
        remote_ip: str | None = Query(None, description="Client IP address"),
    ):
        """Verify reCAPTCHA v3 token.

        Query Parameters:
        - `token` (required): reCAPTCHA response token from client
        - `user_id` or `session_id`: User identifier
        - `remote_ip` (optional): Client IP for verification

        Response (Success):
        ```json
        {
          "success": true,
          "score": 0.9,
          "risk_level": "low",
          "recommendation": "allow",
          "message": "Verification successful"
        }
        ```

        Response (Bot Detected):
        ```json
        {
          "success": false,
          "score": 0.2,
          "risk_level": "high",
          "recommendation": "block",
          "message": "Likely bot - request blocked"
        }
        ```
        """
        try:
            global demo_agent
            if not demo_agent:
                raise HTTPException(
                    status_code=500,
                    detail="Demo agent not initialized",
                )

            # Verify token with Google
            verification_result = await demo_agent.captcha_handler.verify_token(
                token=token,
                remote_ip=remote_ip,
            )

            if not verification_result.get("success"):
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error_codes": verification_result.get("error_codes", []),
                        "message": "CAPTCHA verification failed",
                    },
                )

            # Evaluate score
            score = verification_result.get("score", 0.0)
            evaluation = demo_agent.captcha_handler.evaluate_score(score)

            # Log verification result
            user_key = user_id or session_id or "unknown"
            logger.info(
                f"CAPTCHA verified: {user_key} -> "
                f"score={score:.2f}, risk={evaluation['risk_level']}"
            )

            return {
                "success": True,
                "score": score,
                "action": verification_result.get("action"),
                "risk_level": evaluation["risk_level"],
                "recommendation": evaluation["recommendation"],
                "message": evaluation["message"],
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error in verify_captcha: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # ========================================================================
    # Helper Functions
    # ========================================================================

    async def get_tokens_remaining(user_key: str) -> int:
        """Get remaining tokens for user."""
        try:
            global demo_agent
            if demo_agent:
                status = await demo_agent.get_user_status(user_key)
                return status.get("tokens_remaining", 0)
        except Exception as e:
            logger.error(f"Error getting tokens_remaining: {e}")
        return 0

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
