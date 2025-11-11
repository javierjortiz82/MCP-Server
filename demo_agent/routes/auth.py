"""Authentication Routes.

All authentication endpoints including registration, OTP verification, and user management.

Author: Lab01-MCP Team
Created: 2025-11-10
Version: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from demo_agent import auth_endpoints
from demo_agent.logger import logger
from demo_agent.models.user import (
    OAuthRegisterRequest,
    RegisterResponse,
    ResendOTPRequest,
    ResendOTPResponse,
    UserRegisterRequest,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from demo_agent.services.clerk_service import get_clerk_service
from demo_agent.security.clerk_middleware import require_auth

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


def get_services(request: Request):
    """Get service instances from app state.

    Args:
        request: FastAPI request object.

    Returns:
        tuple: (user_service, otp_service, email_service)

    Raises:
        HTTPException: If services are not initialized.
    """
    user_service = request.app.state.user_service
    otp_service = request.app.state.otp_service
    email_service = request.app.state.email_service

    if not user_service or not otp_service or not email_service:
        raise HTTPException(status_code=500, detail="Services not initialized")

    return user_service, otp_service, email_service


@router.post("/register", response_model=RegisterResponse)
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

    Args:
        request_data: User registration data.
        request: FastAPI request object.

    Returns:
        RegisterResponse: Registration result with user data.
    """
    user_service, otp_service, email_service = get_services(request)

    return await auth_endpoints.register_email(
        request_data=request_data,
        client_request=request,
        user_service=user_service,
        otp_service=otp_service,
        email_service=email_service,
    )


@router.post("/register/oauth", response_model=RegisterResponse)
async def register_with_oauth(request_data: OAuthRegisterRequest, request: Request):
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

    Args:
        request_data: OAuth registration data.
        request: FastAPI request object.

    Returns:
        RegisterResponse: Registration result with user data.
    """
    user_service, _, _ = get_services(request)

    return await auth_endpoints.register_oauth(
        request_data=request_data,
        client_request=request,
        user_service=user_service,
    )


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp_code(request_data: VerifyOTPRequest, request: Request):
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

    Args:
        request_data: OTP verification data.
        request: FastAPI request object.

    Returns:
        VerifyOTPResponse: Verification result.
    """
    user_service, otp_service, _ = get_services(request)

    return await auth_endpoints.verify_otp(
        request_data=request_data,
        user_service=user_service,
        otp_service=otp_service,
    )


@router.post("/resend-otp", response_model=ResendOTPResponse)
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

    Args:
        request_data: Resend OTP request data.
        request: FastAPI request object.

    Returns:
        ResendOTPResponse: Resend result.
    """
    user_service, otp_service, email_service = get_services(request)

    return await auth_endpoints.resend_otp(
        request_data=request_data,
        client_request=request,
        user_service=user_service,
        otp_service=otp_service,
        email_service=email_service,
    )


@router.get("/me")
async def get_current_user_info(request: Request):
    """Get current authenticated user information.

    Requires: Valid Clerk Bearer token in Authorization header

    Request Headers:
    ```
    Authorization: Bearer <clerk_token>
    ```

    Response (Success):
    ```json
    {
      "success": true,
      "user": {
        "clerk_user_id": "user_2abc...",
        "email": "user@example.com",
        "full_name": "John Doe",
        "email_verified": true,
        "db_user_id": 123,
        "is_active": true,
        "clerk_metadata": {
          "public_metadata": {"company": "Acme"},
          "private_metadata": {},
          "profile_image_url": "https://..."
        },
        "preferred_language": "es",
        "created_at": "2025-11-03T10:30:00Z",
        "last_login_at": "2025-11-03T14:25:00Z"
      }
    }
    ```

    Response (Error - Not Authenticated):
    ```json
    {
      "success": false,
      "error": "Unauthorized",
      "message": "Missing Authorization header"
    }
    ```

    Args:
        request: FastAPI request object.

    Returns:
        dict: User information or error response.
    """
    # require_auth will raise 401 if not authenticated
    user = require_auth(request)

    # Fetch full user details from database if db_user_id exists
    clerk_service = get_clerk_service()
    full_user = None

    if user.get("clerk_user_id"):
        full_user = await clerk_service.get_user_by_clerk_id(user["clerk_user_id"])

    return {
        "success": True,
        "user": full_user if full_user else user,
    }


@router.post("/check-migration")
async def check_migration_status(request: Request):
    """Check if a legacy user needs to migrate to Clerk.

    Used by legacy auth endpoints to redirect users to Clerk login.

    Request:
    ```json
    {
      "email": "user@example.com"
    }
    ```

    Response (Migration Required):
    ```json
    {
      "success": true,
      "requires_migration": true,
      "user_id": 123,
      "auth_provider": "email",
      "migration_status": "pending",
      "message": "Please log in with Clerk to migrate your account"
    }
    ```

    Response (No Migration Required):
    ```json
    {
      "success": true,
      "requires_migration": false,
      "message": "User already migrated or does not exist"
    }
    ```

    Args:
        request: FastAPI request object.

    Returns:
        dict: Migration status information.

    Raises:
        HTTPException: 400 if email is not provided, 500 on server error.
    """
    try:
        body = await request.json()
        email = body.get("email")

        if not email:
            raise HTTPException(status_code=400, detail="Email is required")

        clerk_service = get_clerk_service()
        requires_migration, user_info = await clerk_service.check_migration_required(
            email
        )

        if requires_migration and user_info:
            return {
                "success": True,
                "requires_migration": True,
                "user_id": user_info["user_id"],
                "auth_provider": user_info["auth_provider"],
                "migration_status": user_info["migration_status"],
                "message": "Please log in with Clerk to migrate your account",
            }
        else:
            return {
                "success": True,
                "requires_migration": False,
                "message": "User already migrated or does not exist",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error checking migration status: {str(e)}"
        )
