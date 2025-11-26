"""User Service - User Registration and Authentication Logic.

Handles user creation, authentication, and account management with PostgreSQL persistence.

FIX 3.2: Async database operations
- All db calls converted to async/await

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.1.0 (Async)
"""

from datetime import datetime, timezone

import bcrypt

from demo_agent.config.settings import config
from demo_agent.db.connection import get_db
from demo_agent.models.user import (
    AuthProvider,
    OAuthRegisterRequest,
    UserDB,
    UserRegisterRequest,
)
from demo_agent.observability.metrics import get_metrics_collector
from demo_agent.observability.structured_logger import get_structured_logger


class UserService:
    """Service for user management and authentication.

    Handles:
    - User registration (email/password + OAuth)
    - Password hashing with BCrypt
    - Email uniqueness validation
    - Account activation after OTP verification
    - User lookup and status management

    All passwords are hashed with BCrypt (salt rounds: 12).
    OAuth users have no password_hash (null).
    """

    def __init__(self):
        """Initialize UserService with database connection."""
        self.db = get_db()
        self.logger = get_structured_logger(__name__)
        self.metrics = get_metrics_collector()
        self.logger.info("UserService initialized")

    async def register_email_user(
        self,
        data: UserRegisterRequest,
        ip_address: str | None = None,
    ) -> tuple[UserDB | None, str | None]:
        """Register new user with email/password authentication.

        Args:
            data: User registration data (email, password, full_name).
            ip_address: Client IP address for audit trail.

        Returns:
            Tuple[UserDB | None, error_message | None]:
            - UserDB: Created user record (if success)
            - error: Error message (if failure)

        Process:
        1. Check if email already exists
        2. Hash password with BCrypt (salt rounds: 12)
        3. Insert user record (is_active=false, is_email_verified=false)
        4. Return user record

        Raises:
            Exception: Database errors are logged but not raised.
        """
        try:
            self.logger.info(
                "Registering email user",
                email=data.email,
                source=data.registration_source
            )

            # Step 1: Check if email already exists
            existing_user = await self.get_user_by_email(data.email)
            if existing_user:
                if existing_user.is_deleted:
                    error_msg = (
                        "This email was previously deleted. "
                        "Contact support to reactivate."
                    )
                    self.metrics.increment_counter("registration_email_deleted_account")
                elif not existing_user.is_email_verified:
                    error_msg = (
                        "This email is already registered but not verified. "
                        "Please check your email for verification code."
                    )
                    self.metrics.increment_counter("registration_email_unverified")
                else:
                    error_msg = "This email is already registered."
                    self.metrics.increment_counter("registration_email_exists")

                self.logger.warning(
                    "Email already exists",
                    email=data.email
                )
                return None, error_msg

            # Step 2: Hash password with BCrypt (salt rounds: 12)
            password_hash = bcrypt.hashpw(
                data.password.encode("utf-8"), bcrypt.gensalt(rounds=12)
            ).decode("utf-8")

            # Step 3: Insert user record
            query = f"""
                INSERT INTO {config.SCHEMA_NAME}.demo_users
                (email, full_name, auth_provider, password_hash,
                 preferred_language, registration_source, registration_ip,
                 is_active, is_email_verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s::inet, %s, %s)
                RETURNING id, email, full_name, display_name, auth_provider,
                          password_hash, oauth_provider_id,
                          is_email_verified, email_verified_at,
                          is_active, is_suspended, is_deleted,
                          suspended_at, suspended_reason, deleted_at,
                          preferred_language, timezone,
                          registration_source, registration_ip,
                          last_login_at, last_login_ip,
                          created_at, updated_at
            """

            result = await self.db.execute_one(
                query,
                (
                    data.email,
                    data.full_name,
                    AuthProvider.EMAIL.value,
                    password_hash,
                    data.preferred_language,
                    data.registration_source,
                    ip_address,
                    False,  # is_active (activated after OTP verification)
                    False,  # is_email_verified
                ),
            )

            if not result:
                self.logger.error(
                    "Failed to insert user",
                    email=data.email
                )
                self.metrics.increment_counter("registration_email_insert_errors")
                return None, "Failed to create user account. Please try again."

            user = UserDB(**result)
            self.logger.info(
                "Email user created successfully",
                email=user.email,
                user_id=user.id,
                status="pending_verification"
            )
            self.metrics.increment_counter("registrations_email_successful")
            return user, None

        except Exception:
            self.logger.exception(
                "Error in register_email_user",
                email=data.email
            )
            self.metrics.increment_counter("registration_email_errors")
            return None, "An error occurred during registration. Please try again."

    async def register_oauth_user(
        self,
        data: OAuthRegisterRequest,
        ip_address: str | None = None,
    ) -> tuple[UserDB | None, str | None]:
        """Register new user with OAuth provider (Google, Apple).

        Args:
            data: OAuth registration data (email, provider, provider_id).
            ip_address: Client IP address for audit trail.

        Returns:
            Tuple[UserDB | None, error_message | None]:
            - UserDB: Created user record (if success)
            - error: Error message (if failure)

        Process:
        1. Check if OAuth user already exists (provider + provider_id)
        2. Check if email exists with different provider
        3. Insert user record (is_active=true, is_email_verified=true for OAuth)
        4. Return user record

        Note:
            OAuth users are automatically verified (email ownership proven by provider).
            Account is activated immediately (is_active=true).
        """
        try:
            self.logger.info(
                "Registering OAuth user",
                email=data.email,
                provider=data.auth_provider.value,
                source=data.registration_source
            )

            # Step 1: Check if OAuth user already exists
            existing_oauth = await self.get_user_by_oauth(
                data.auth_provider, data.oauth_provider_id
            )
            if existing_oauth:
                self.logger.warning(
                    "OAuth user already exists",
                    provider=data.auth_provider.value,
                    provider_id=data.oauth_provider_id
                )
                self.metrics.increment_counter("registration_oauth_duplicate")
                return None, "This account is already registered."

            # Step 2: Check if email exists with different provider
            existing_email = await self.get_user_by_email(data.email)
            if existing_email:
                if existing_email.auth_provider != data.auth_provider.value:
                    error_msg = (
                        f"This email is already registered with {existing_email.auth_provider}. "
                        f"Please use {existing_email.auth_provider} to sign in."
                    )
                    self.logger.warning(
                        "Email exists with different provider",
                        email=data.email,
                        existing_provider=existing_email.auth_provider,
                        requested_provider=data.auth_provider.value
                    )
                    self.metrics.increment_counter("registration_oauth_email_mismatch")
                    return None, error_msg

            # Step 3: Insert OAuth user (auto-verified and active)
            query = f"""
                INSERT INTO {config.SCHEMA_NAME}.demo_users
                (email, full_name, auth_provider, oauth_provider_id,
                 preferred_language, registration_source, registration_ip,
                 is_active, is_email_verified, email_verified_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s::inet, %s, %s, %s)
                RETURNING id, email, full_name, display_name, auth_provider,
                          password_hash, oauth_provider_id,
                          is_email_verified, email_verified_at,
                          is_active, is_suspended, is_deleted,
                          suspended_at, suspended_reason, deleted_at,
                          preferred_language, timezone,
                          registration_source, registration_ip,
                          last_login_at, last_login_ip,
                          created_at, updated_at
            """

            now = datetime.now(timezone.utc)
            result = await self.db.execute_one(
                query,
                (
                    data.email,
                    data.full_name,
                    data.auth_provider.value,
                    data.oauth_provider_id,
                    data.preferred_language,
                    data.registration_source,
                    ip_address,
                    True,  # is_active (OAuth users are immediately active)
                    True,  # is_email_verified (verified by OAuth provider)
                    now,  # email_verified_at
                ),
            )

            if not result:
                self.logger.error(
                    "Failed to insert OAuth user",
                    email=data.email,
                    provider=data.auth_provider.value
                )
                self.metrics.increment_counter("registration_oauth_insert_errors")
                return None, "Failed to create user account. Please try again."

            user = UserDB(**result)
            self.logger.info(
                "OAuth user created successfully",
                email=user.email,
                user_id=user.id,
                provider=data.auth_provider.value,
                status="active_verified"
            )
            self.metrics.increment_counter("registrations_oauth_successful")
            return user, None

        except Exception:
            self.logger.exception(
                "Error in register_oauth_user",
                email=data.email,
                provider=data.auth_provider.value if hasattr(data, 'auth_provider') else None
            )
            self.metrics.increment_counter("registration_oauth_errors")
            return None, "An error occurred during registration. Please try again."

    async def get_user_by_email(self, email: str) -> UserDB | None:
        """Get user by email address (case-insensitive).

        Args:
            email: User email address.

        Returns:
            UserDB: User record (or None if not found).
        """
        try:
            query = f"""
                SELECT id, email, full_name, display_name, auth_provider,
                       password_hash, oauth_provider_id,
                       is_email_verified, email_verified_at,
                       is_active, is_suspended, is_deleted,
                       suspended_at, suspended_reason, deleted_at,
                       preferred_language, timezone,
                       registration_source, registration_ip,
                       last_login_at, last_login_ip,
                       created_at, updated_at
                FROM {config.SCHEMA_NAME}.demo_users
                WHERE LOWER(email) = LOWER(%s)
            """
            result = await self.db.execute_one(query, (email,))

            if result:
                self.metrics.increment_counter("user_lookup_email_found")
                return UserDB(**result)

            self.metrics.increment_counter("user_lookup_email_not_found")
            return None

        except Exception:
            self.logger.exception("Error in get_user_by_email", email=email)
            self.metrics.increment_counter("user_lookup_email_errors")
            return None

    async def get_user_by_oauth(
        self, auth_provider: AuthProvider, oauth_provider_id: str
    ) -> UserDB | None:
        """Get user by OAuth provider and provider ID.

        Args:
            auth_provider: OAuth provider (google, apple, etc.).
            oauth_provider_id: Provider's unique user ID.

        Returns:
            UserDB: User record (or None if not found).
        """
        try:
            query = f"""
                SELECT id, email, full_name, display_name, auth_provider,
                       password_hash, oauth_provider_id,
                       is_email_verified, email_verified_at,
                       is_active, is_suspended, is_deleted,
                       suspended_at, suspended_reason, deleted_at,
                       preferred_language, timezone,
                       registration_source, registration_ip,
                       last_login_at, last_login_ip,
                       created_at, updated_at
                FROM {config.SCHEMA_NAME}.demo_users
                WHERE auth_provider = %s
                  AND oauth_provider_id = %s
            """
            result = await self.db.execute_one(
                query, (auth_provider.value, oauth_provider_id)
            )

            if result:
                self.metrics.increment_counter("user_lookup_oauth_found")
                return UserDB(**result)

            self.metrics.increment_counter("user_lookup_oauth_not_found")
            return None

        except Exception:
            self.logger.exception(
                "Error in get_user_by_oauth",
                provider=auth_provider.value
            )
            self.metrics.increment_counter("user_lookup_oauth_errors")
            return None

    async def activate_user(self, user_id: int) -> bool:
        """Activate user account after email verification.

        Args:
            user_id: User ID to activate.

        Returns:
            bool: True if activation successful.

        Updates:
            - is_active = true
            - is_email_verified = true
            - email_verified_at = NOW()
        """
        try:
            query = f"""
                UPDATE {config.SCHEMA_NAME}.demo_users
                SET is_active = true,
                    is_email_verified = true,
                    email_verified_at = %s,
                    updated_at = %s
                WHERE id = %s
                  AND is_active = false
                RETURNING id
            """

            now = datetime.now(timezone.utc)
            result = await self.db.execute_one(query, (now, now, user_id))

            if result:
                self.logger.info(
                    "User activated successfully",
                    user_id=user_id
                )
                self.metrics.increment_counter("user_activations_successful")
                return True

            self.logger.warning(
                "Failed to activate user",
                user_id=user_id,
                reason="already_active"
            )
            self.metrics.increment_counter("user_activations_already_active")
            return False

        except Exception:
            self.logger.exception("Error in activate_user", user_id=user_id)
            self.metrics.increment_counter("user_activation_errors")
            return False

    async def verify_password(self, user: UserDB, password: str) -> bool:
        """Verify password against stored hash.

        Args:
            user: User record with password_hash.
            password: Plain-text password to verify.

        Returns:
            bool: True if password matches hash.

        Note:
            Uses BCrypt's constant-time comparison to prevent timing attacks.
        """
        try:
            if not user.password_hash:
                self.logger.warning(
                    "User has no password (OAuth user?)",
                    user_id=user.id,
                    email=user.email
                )
                self.metrics.increment_counter("password_verify_no_hash")
                return False

            is_valid = bcrypt.checkpw(
                password.encode("utf-8"), user.password_hash.encode("utf-8")
            )

            if is_valid:
                self.metrics.increment_counter("password_verify_success")
            else:
                self.logger.warning(
                    "Password verification failed",
                    user_id=user.id
                )
                self.metrics.increment_counter("password_verify_failed")

            return is_valid

        except Exception:
            self.logger.exception("Error in verify_password", user_id=user.id)
            self.metrics.increment_counter("password_verify_errors")
            return False

    async def update_last_login(
        self, user_id: int, ip_address: str | None = None
    ) -> bool:
        """Update user's last login timestamp and IP.

        Args:
            user_id: User ID.
            ip_address: Client IP address.

        Returns:
            bool: True if update successful.
        """
        try:
            query = f"""
                UPDATE {config.SCHEMA_NAME}.demo_users
                SET last_login_at = %s,
                    last_login_ip = %s::inet,
                    updated_at = %s
                WHERE id = %s
            """

            now = datetime.now(timezone.utc)
            await self.db.execute(query, (now, ip_address, now, user_id))
            self.logger.debug(
                "Updated last login",
                user_id=user_id,
                ip_address=ip_address
            )
            self.metrics.increment_counter("user_logins_recorded")
            return True

        except Exception:
            self.logger.exception("Error in update_last_login", user_id=user_id)
            self.metrics.increment_counter("user_login_update_errors")
            return False
