"""Authentication Endpoints for Demo Agent.

FastAPI endpoints for user registration, OTP verification, and resend.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from demo_agent.logger import logger
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


async def register_email(
    request_data: UserRegisterRequest,
    client_request: Request,
    user_service: UserService,
    otp_service: OTPService,
    email_service: EmailIntegrationService,
) -> RegisterResponse | JSONResponse:
    """Register new user with email/password.

    Endpoint: POST /v1/auth/register

    Process:
    1. Validate email/password strength
    2. Create user record (is_active=false)
    3. Generate 6-digit OTP code
    4. Send OTP via email
    5. Return success response

    Args:
        request_data: User registration data.
        client_request: FastAPI Request object (for IP extraction).
        user_service: UserService instance.
        otp_service: OTPService instance.
        email_service: EmailIntegrationService instance.

    Returns:
        RegisterResponse: Registration result with user data.
    """
    try:
        logger.info(f"Email registration request: {request_data.email}")

        # Extract client IP
        client_ip = client_request.client.host if client_request.client else None

        # Step 1: Create user
        user, error = await user_service.register_email_user(
            data=request_data, ip_address=client_ip
        )

        if error:
            logger.warning(f"Registration failed: {error}")
            return RegisterResponse(
                success=False,
                message=error,
                requires_verification=True,
                verification_sent=False,
            )

        if not user:
            logger.error("User creation returned None without error")
            return RegisterResponse(
                success=False,
                message="Registration failed. Please try again.",
                requires_verification=True,
                verification_sent=False,
            )

        # Step 2: Generate OTP
        otp_code, otp_record, otp_error = await otp_service.create_otp(
            user_id=user.id,
            email=user.email,
            purpose=OTPPurpose.EMAIL_VERIFICATION,
            ip_address=client_ip,
            user_agent=client_request.headers.get("user-agent"),
        )

        if otp_error:
            logger.error(f"OTP generation failed: {otp_error}")
            return RegisterResponse(
                success=True,  # User created successfully
                message=(
                    "Account created but verification email failed. "
                    "Please request a new code."
                ),
                user=user.to_response(),
                requires_verification=True,
                verification_sent=False,
            )

        # Step 3: Send OTP email
        email_sent, email_msg = await email_service.send_otp_email(
            recipient_email=user.email,
            recipient_name=user.full_name,
            otp_code=otp_code,
            expires_at=otp_record.expires_at,
            language=user.preferred_language,
        )

        if not email_sent:
            logger.error(f"Email sending failed: {email_msg}")
            return RegisterResponse(
                success=True,  # User created successfully
                message=(
                    "Account created but verification email failed. "
                    "Please request a new code."
                ),
                user=user.to_response(),
                requires_verification=True,
                verification_sent=False,
            )

        # Success!
        logger.info(
            f"User registered successfully: {user.email} (ID: {user.id}), OTP sent"
        )
        return RegisterResponse(
            success=True,
            message=(
                "Registration successful! Please check your email for "
                "the verification code."
            ),
            user=user.to_response(),
            requires_verification=True,
            verification_sent=True,
        )

    except Exception as e:
        logger.exception(f"Error in register_email: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An error occurred during registration.",
            },
        )


async def register_oauth(
    request_data: OAuthRegisterRequest,
    client_request: Request,
    user_service: UserService,
) -> RegisterResponse | JSONResponse:
    """Register new user with OAuth provider (Google, Apple).

    Endpoint: POST /v1/auth/register/oauth

    Process:
    1. Validate OAuth token with provider (external service)
    2. Create user record (is_active=true, email verified by provider)
    3. Return success response

    Note:
        OAuth users skip OTP verification (email verified by provider).
        Account is immediately active.

    Args:
        request_data: OAuth registration data.
        client_request: FastAPI Request object.
        user_service: UserService instance.

    Returns:
        RegisterResponse: Registration result with user data.
    """
    try:
        logger.info(
            f"OAuth registration request: {request_data.email} "
            f"(provider: {request_data.auth_provider})"
        )

        # Extract client IP
        client_ip = client_request.client.host if client_request.client else None

        # Create OAuth user
        user, error = await user_service.register_oauth_user(
            data=request_data, ip_address=client_ip
        )

        if error:
            logger.warning(f"OAuth registration failed: {error}")
            return RegisterResponse(
                success=False,
                message=error,
                requires_verification=False,  # OAuth users don't need email verification
                verification_sent=False,
            )

        if not user:
            logger.error("OAuth user creation returned None without error")
            return RegisterResponse(
                success=False,
                message="Registration failed. Please try again.",
                requires_verification=False,
                verification_sent=False,
            )

        # Success! OAuth user is immediately active
        logger.info(
            f"OAuth user registered: {user.email} (ID: {user.id}, "
            f"provider: {request_data.auth_provider})"
        )
        return RegisterResponse(
            success=True,
            message="Registration successful! Your account is now active.",
            user=user.to_response(),
            requires_verification=False,  # Already verified by OAuth provider
            verification_sent=False,
        )

    except Exception as e:
        logger.exception(f"Error in register_oauth: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An error occurred during OAuth registration.",
            },
        )


async def verify_otp(
    request_data: VerifyOTPRequest,
    user_service: UserService,
    otp_service: OTPService,
) -> VerifyOTPResponse | JSONResponse:
    """Verify OTP code and activate user account.

    Endpoint: POST /v1/auth/verify-otp

    Process:
    1. Validate OTP code against database hash
    2. If valid: activate user account (is_active=true)
    3. Return success response with user data

    Args:
        request_data: OTP verification data (email, code).
        user_service: UserService instance.
        otp_service: OTPService instance.

    Returns:
        VerifyOTPResponse: Verification result.
    """
    try:
        logger.info(f"OTP verification request: {request_data.email}")

        # Verify OTP code
        is_valid, user_id, message = await otp_service.verify_otp(
            email=request_data.email,
            otp_code=request_data.otp_code,
            purpose=request_data.purpose,
        )

        if not is_valid:
            logger.warning(f"OTP verification failed for {request_data.email}: {message}")
            return VerifyOTPResponse(
                success=False, message=message, is_active=False
            )

        # Activate user account
        if user_id:
            activated = await user_service.activate_user(user_id)
            if not activated:
                logger.error(f"Failed to activate user ID {user_id}")
                return VerifyOTPResponse(
                    success=False,
                    message="Verification successful but activation failed.",
                    is_active=False,
                )

            # Get updated user data
            user = await user_service.get_user_by_email(request_data.email)
            if user:
                logger.info(
                    f"User activated successfully: {request_data.email} (ID: {user_id})"
                )
                return VerifyOTPResponse(
                    success=True,
                    message="Email verified successfully! Your account is now active.",
                    is_active=True,
                    user=user.to_response(),
                )

        return VerifyOTPResponse(
            success=False,
            message="Verification failed. Please try again.",
            is_active=False,
        )

    except Exception as e:
        logger.exception(f"Error in verify_otp: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An error occurred during verification.",
            },
        )


async def resend_otp(
    request_data: ResendOTPRequest,
    client_request: Request,
    user_service: UserService,
    otp_service: OTPService,
    email_service: EmailIntegrationService,
) -> ResendOTPResponse | JSONResponse:
    """Resend OTP verification email.

    Endpoint: POST /v1/auth/resend-otp

    Process:
    1. Check rate limiting (1 OTP per minute)
    2. Check user exists and not already active
    3. Generate new OTP
    4. Send via email
    5. Return success response

    Args:
        request_data: Resend request data (email).
        client_request: FastAPI Request object.
        user_service: UserService instance.
        otp_service: OTPService instance.
        email_service: EmailIntegrationService instance.

    Returns:
        ResendOTPResponse: Resend result.
    """
    try:
        logger.info(f"Resend OTP request: {request_data.email}")

        # Check if user exists
        user = await user_service.get_user_by_email(request_data.email)
        if not user:
            logger.warning(f"Resend OTP failed: user not found ({request_data.email})")
            return ResendOTPResponse(
                success=False,
                message="No account found with this email address.",
            )

        # Check if user is already active
        if user.is_active:
            logger.warning(f"Resend OTP failed: user already active ({request_data.email})")
            return ResendOTPResponse(
                success=False, message="Your account is already active."
            )

        # Check rate limiting
        can_request, cooldown_remaining = await otp_service.can_request_otp(
            email=request_data.email, purpose=request_data.purpose
        )

        if not can_request:
            logger.warning(
                f"Resend OTP rate limited: {request_data.email} "
                f"({cooldown_remaining}s remaining)"
            )
            return ResendOTPResponse(
                success=False,
                message=(
                    f"Please wait {cooldown_remaining} seconds before "
                    "requesting a new code."
                ),
                cooldown_seconds=cooldown_remaining,
            )

        # Generate new OTP
        client_ip = client_request.client.host if client_request.client else None
        otp_code, otp_record, otp_error = await otp_service.create_otp(
            user_id=user.id,
            email=user.email,
            purpose=request_data.purpose,
            ip_address=client_ip,
            user_agent=client_request.headers.get("user-agent"),
        )

        if otp_error:
            logger.error(f"Resend OTP generation failed: {otp_error}")
            return ResendOTPResponse(success=False, message=otp_error)

        # Send OTP email
        email_sent, email_msg = await email_service.send_otp_email(
            recipient_email=user.email,
            recipient_name=user.full_name,
            otp_code=otp_code,
            expires_at=otp_record.expires_at,
            language=user.preferred_language,
        )

        if not email_sent:
            logger.error(f"Resend OTP email failed: {email_msg}")
            return ResendOTPResponse(success=False, message=email_msg)

        # Success!
        logger.info(f"OTP resent successfully: {user.email}")
        return ResendOTPResponse(
            success=True,
            message="Verification code sent! Please check your email.",
            expires_at=otp_record.expires_at.isoformat(),
        )

    except Exception as e:
        logger.exception(f"Error in resend_otp: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An error occurred while resending the code.",
            },
        )
