"""User and Authentication Models for Demo Agent.

Pydantic models for user registration, authentication, and OTP verification.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator

# SECURITY: Import ReDoS-safe validators
from demo_agent.utils.validators import (
    sanitize_email,
    validate_email_safe,
    validate_otp_code_safe,
    validate_password_strength,
)


class AuthProvider(str, Enum):
    """Authentication provider types."""

    EMAIL = "email"
    GOOGLE = "google"
    APPLE = "apple"
    FACEBOOK = "facebook"
    GITHUB = "github"


class OTPPurpose(str, Enum):
    """OTP verification purposes."""

    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_RECOVERY = "account_recovery"
    LOGIN_2FA = "login_2fa"


class UserStatus(str, Enum):
    """User account status."""

    PENDING_VERIFICATION = "pending_verification"  # Registered, not verified
    ACTIVE = "active"  # Email verified and active
    SUSPENDED = "suspended"  # Temporarily suspended
    DELETED = "deleted"  # Soft deleted


# ============================================================================
# Request Models (Input)
# ============================================================================


class UserRegisterRequest(BaseModel):
    """User registration request (email/password).

    Attributes:
        email: User email address (validated format).
        full_name: User's full name (3-100 chars).
        password: Password (8-100 chars, hashed before storage).
        preferred_language: UI language preference (default: es).
        registration_source: Source of registration (web, mobile, api).
    """

    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=3, max_length=100, description="Full name")
    password: str = Field(
        ..., min_length=8, max_length=100, description="Password (8-100 chars)"
    )
    preferred_language: str = Field(
        default="es", description="Preferred language (es, en)"
    )
    registration_source: str = Field(
        default="web", description="Registration source (web, mobile, api)"
    )

    @field_validator("email")
    @classmethod
    def validate_email_redos_safe(cls, v: str) -> str:
        """Validate email with ReDoS protection.

        SECURITY (CWE-1333 fix): Additional validation beyond Pydantic's EmailStr
        to ensure ReDoS resistance and prevent email-based attacks.
        """
        is_valid, error_msg = validate_email_safe(v)
        if not is_valid:
            raise ValueError(error_msg)
        return sanitize_email(v)

    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language code."""
        allowed = {"es", "en", "fr", "de", "it", "pt"}
        if v not in allowed:
            raise ValueError(f"Language must be one of {allowed}")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Validate full name (no numbers, min 3 chars)."""
        if not v or len(v.strip()) < 3:
            raise ValueError("Full name must be at least 3 characters")
        if any(char.isdigit() for char in v):
            raise ValueError("Full name cannot contain numbers")
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength.

        SECURITY: Uses hardened password validation to prevent common
        weak passwords and enforce strong password policy.
        """
        is_valid, error_msg = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class OAuthRegisterRequest(BaseModel):
    """OAuth provider registration request (Google, Apple).

    Attributes:
        email: User email from OAuth provider.
        full_name: User's full name from OAuth profile.
        auth_provider: OAuth provider (google, apple).
        oauth_provider_id: Provider's unique user ID.
        preferred_language: UI language preference.
        registration_source: Source of registration.
    """

    email: EmailStr = Field(..., description="Email from OAuth provider")
    full_name: str = Field(..., min_length=3, max_length=100, description="Full name")
    auth_provider: AuthProvider = Field(..., description="OAuth provider")
    oauth_provider_id: str = Field(..., description="Provider's user ID")
    preferred_language: str = Field(default="es", description="Preferred language")
    registration_source: str = Field(default="web", description="Registration source")

    @field_validator("auth_provider")
    @classmethod
    def validate_provider(cls, v: AuthProvider) -> AuthProvider:
        """Validate auth provider is OAuth (not email)."""
        if v == AuthProvider.EMAIL:
            raise ValueError("Use UserRegisterRequest for email registration")
        return v


class VerifyOTPRequest(BaseModel):
    """OTP verification request.

    Attributes:
        email: User email address.
        otp_code: 6-digit OTP code from email.
        purpose: Verification purpose (default: email_verification).
    """

    email: EmailStr = Field(..., description="User email address")
    otp_code: str = Field(
        ..., min_length=6, max_length=6, description="6-digit OTP code"
    )
    purpose: OTPPurpose = Field(
        default=OTPPurpose.EMAIL_VERIFICATION, description="OTP purpose"
    )

    @field_validator("otp_code")
    @classmethod
    def validate_otp_code(cls, v: str) -> str:
        """Validate OTP code is 6 digits.

        SECURITY: Uses safe validator to prevent unicode digit attacks
        and ensure only ASCII digits 0-9 are accepted.
        """
        is_valid, error_msg = validate_otp_code_safe(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class ResendOTPRequest(BaseModel):
    """Resend OTP request.

    Attributes:
        email: User email address.
        purpose: OTP purpose (default: email_verification).
    """

    email: EmailStr = Field(..., description="User email address")
    purpose: OTPPurpose = Field(
        default=OTPPurpose.EMAIL_VERIFICATION, description="OTP purpose"
    )


# ============================================================================
# Response Models (Output)
# ============================================================================


class UserResponse(BaseModel):
    """User data response (safe for API).

    Attributes:
        id: User ID.
        email: User email.
        full_name: Full name.
        display_name: Display name (optional).
        auth_provider: Authentication provider.
        is_email_verified: Email verification status.
        is_active: Account active status.
        preferred_language: Language preference.
        created_at: Registration timestamp.
    """

    id: int = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name")
    display_name: str | None = Field(None, description="Display name")
    auth_provider: str = Field(..., description="Auth provider")
    is_email_verified: bool = Field(..., description="Email verified")
    is_active: bool = Field(..., description="Account active")
    preferred_language: str = Field(..., description="Language preference")
    created_at: str = Field(..., description="Registration timestamp (ISO 8601)")

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    """Registration response.

    Attributes:
        success: Registration success flag.
        message: Human-readable message.
        user: User data (if success).
        requires_verification: Whether email verification is required.
        verification_sent: Whether OTP was sent.
    """

    success: bool = Field(..., description="Registration success")
    message: str = Field(..., description="Human-readable message")
    user: UserResponse | None = Field(None, description="User data")
    requires_verification: bool = Field(True, description="Requires email verification")
    verification_sent: bool = Field(
        False, description="OTP verification email sent"
    )


class VerifyOTPResponse(BaseModel):
    """OTP verification response.

    Attributes:
        success: Verification success flag.
        message: Human-readable message.
        is_active: Whether user is now active.
        user: User data (if success).
    """

    success: bool = Field(..., description="Verification success")
    message: str = Field(..., description="Human-readable message")
    is_active: bool = Field(False, description="Account is active")
    user: UserResponse | None = Field(None, description="User data")


class ResendOTPResponse(BaseModel):
    """Resend OTP response.

    Attributes:
        success: Resend success flag.
        message: Human-readable message.
        cooldown_seconds: Seconds remaining before next resend allowed.
        expires_at: OTP expiration timestamp.
    """

    success: bool = Field(..., description="Resend success")
    message: str = Field(..., description="Human-readable message")
    cooldown_seconds: int | None = Field(
        None, description="Cooldown remaining (seconds)"
    )
    expires_at: str | None = Field(None, description="OTP expiration timestamp")


# ============================================================================
# Database Models (Internal)
# ============================================================================


class UserDB(BaseModel):
    """User model (from database).

    Full user record including sensitive fields (internal use only).
    Never return this model directly to API clients.
    """

    id: int
    email: str
    full_name: str
    display_name: str | None
    auth_provider: str
    oauth_provider_id: str | None
    password_hash: str | None
    is_email_verified: bool
    email_verified_at: datetime | None
    is_active: bool
    is_suspended: bool
    is_deleted: bool
    suspended_at: datetime | None
    suspended_reason: str | None
    deleted_at: datetime | None
    preferred_language: str
    timezone: str
    registration_source: str
    registration_ip: str | None
    last_login_at: datetime | None
    last_login_ip: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    def to_response(self) -> UserResponse:
        """Convert DB model to safe API response model."""
        return UserResponse(
            id=self.id,
            email=self.email,
            full_name=self.full_name,
            display_name=self.display_name,
            auth_provider=self.auth_provider,
            is_email_verified=self.is_email_verified,
            is_active=self.is_active,
            preferred_language=self.preferred_language,
            created_at=self.created_at.isoformat(),
        )


class OTPDB(BaseModel):
    """OTP code model (from database).

    Internal model for OTP records. Never expose code_hash to clients.
    """

    id: int
    user_id: int
    email: str
    code_hash: str  # SHA-256 hash (never plain text)
    purpose: str
    expires_at: datetime
    attempts_count: int
    max_attempts: int
    is_used: bool
    used_at: datetime | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
