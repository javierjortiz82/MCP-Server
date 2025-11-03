"""OTP Service - One-Time Password Generation and Validation.

Handles OTP code generation, SHA-256 hashing, validation, and rate limiting.

FIX 3.2: Async database operations
- All db calls converted to async/await
- Non-blocking database I/O

Best Practices (2025):
- 6-digit codes (balance security vs UX)
- 10-minute expiration (NIST/OWASP compliant)
- SHA-256 hashing (never store plain-text)
- Max 3 verification attempts (prevent brute force)
- Rate limiting: 1 OTP per minute per email
- Auto-cleanup of expired codes

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.1.0 (Async)
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Tuple

from demo_agent.config.settings import config
from demo_agent.db.connection import get_db
from demo_agent.logger import logger
from demo_agent.models.user import OTPDB, OTPPurpose
from demo_agent.observability.metrics import get_metrics_collector
from demo_agent.observability.structured_logger import get_structured_logger


class OTPService:
    """Service for OTP generation, validation, and lifecycle management.

    Features:
    - Cryptographically secure 6-digit OTP generation
    - SHA-256 hashing for secure storage
    - Rate limiting (1 OTP per minute per email)
    - Max 3 verification attempts per OTP
    - 24-hour expiration (configurable)
    - Automatic cleanup of expired codes

    Security:
    - Codes are hashed with SHA-256 before storage
    - Constant-time comparison prevents timing attacks
    - Rate limiting prevents spam/abuse
    - Attempt limiting prevents brute force
    """

    def __init__(self):
        """Initialize OTPService with database connection and configurable settings."""
        from demo_agent.config.settings import config

        self.db = get_db()
        self.otp_length = 6
        self.logger = get_structured_logger(__name__)
        self.metrics = get_metrics_collector()

        # Load from config (environment variables or .env file)
        # FIX: Changed from 24 hours to configurable minutes (NIST/OWASP compliant)
        # Industry standard for OTP: 5-15 minutes
        # 24 hours would enable brute force attacks
        self.expiration_minutes = config.OTP_EXPIRATION_MINUTES
        self.cooldown_seconds = config.OTP_RATE_LIMIT_COOLDOWN_SECONDS
        self.max_attempts = config.OTP_MAX_ATTEMPTS

        self.logger.info(
            "OTPService initialized",
            expiration_minutes=self.expiration_minutes,
            cooldown_seconds=self.cooldown_seconds,
            max_attempts=self.max_attempts
        )

    def generate_otp_code(self) -> str:
        """Generate cryptographically secure 6-digit OTP code.

        Uses secrets module (cryptographically secure random).

        Returns:
            str: 6-digit OTP code (e.g., "123456").

        Example:
            >>> otp = service.generate_otp_code()
            >>> print(otp)  # "847291"
        """
        # Generate 6-digit number (000000-999999)
        code = secrets.randbelow(1000000)
        return str(code).zfill(self.otp_length)

    def hash_otp_code(self, code: str) -> str:
        """Hash OTP code with SHA-256.

        Args:
            code: Plain-text OTP code (6 digits).

        Returns:
            str: SHA-256 hash (64 hex chars).

        Note:
            Never store plain-text OTP codes in database.
        """
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def verify_otp_hash(self, code: str, code_hash: str) -> bool:
        """Verify OTP code against stored hash (constant-time comparison).

        Args:
            code: Plain-text OTP code to verify.
            code_hash: Stored SHA-256 hash.

        Returns:
            bool: True if code matches hash.

        Security:
            Uses secrets.compare_digest() for constant-time comparison
            to prevent timing attacks.
        """
        computed_hash = self.hash_otp_code(code)
        return secrets.compare_digest(computed_hash, code_hash)

    async def can_request_otp(
        self, email: str, purpose: OTPPurpose = OTPPurpose.EMAIL_VERIFICATION
    ) -> Tuple[bool, int]:
        """Check if user can request new OTP (rate limiting).

        Args:
            email: User email address.
            purpose: OTP purpose (default: email_verification).

        Returns:
            Tuple[bool, int]: (can_request, cooldown_seconds_remaining)
            - can_request: True if user can request OTP
            - cooldown_seconds_remaining: Seconds until next OTP allowed (0 if can request)

        Rate Limit:
            1 OTP per minute per email (prevents spam).
        """
        try:
            async with self.metrics.record_latency_async(
                "otp_service.can_request_otp",
                tags={"email": email, "purpose": purpose.value}
            ):
                # Call PostgreSQL function for rate limiting check
                query = f"""
                    SELECT {config.SCHEMA_NAME}.can_request_otp(%s, %s, %s)
                """
                result = await self.db.execute_one(
                    query, (email, purpose.value, self.cooldown_seconds)
                )

                if not result:
                    self.metrics.increment_counter("otp_rate_limit_checks_allowed")
                    return True, 0

                can_request = result.get("can_request_otp", False)

                if not can_request:
                    # Get last OTP creation time to calculate remaining cooldown
                    last_otp_query = f"""
                        SELECT created_at
                        FROM {config.SCHEMA_NAME}.demo_otp_codes
                        WHERE email = %s
                          AND purpose = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                    """
                    last_otp = await self.db.execute_one(last_otp_query, (email, purpose.value))

                    if last_otp:
                        last_created = last_otp["created_at"]
                        elapsed = (datetime.now(timezone.utc) - last_created).total_seconds()
                        remaining = max(0, self.cooldown_seconds - int(elapsed))
                        self.logger.warning(
                            "OTP rate limit exceeded",
                            email=email,
                            remaining_seconds=remaining
                        )
                        self.metrics.increment_counter("otp_rate_limit_exceeded")
                        return False, remaining
                else:
                    self.metrics.increment_counter("otp_rate_limit_checks_allowed")

                return can_request, 0

        except Exception as e:
            self.logger.exception("Error in can_request_otp", email=email)
            self.metrics.increment_counter("otp_rate_limit_errors")
            # Fail open: allow request but log error
            return True, 0

    async def create_otp(
        self,
        user_id: int,
        email: str,
        purpose: OTPPurpose = OTPPurpose.EMAIL_VERIFICATION,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Tuple[str | None, OTPDB | None, str | None]:
        """Create new OTP code for user.

        Args:
            user_id: User ID.
            email: User email address.
            purpose: OTP purpose (default: email_verification).
            ip_address: Client IP address.
            user_agent: Client User-Agent.

        Returns:
            Tuple[otp_code, otp_record, error_message]:
            - otp_code: Plain-text 6-digit code (for email sending)
            - otp_record: OTPDB record (for metadata)
            - error_message: Error string (if failure)

        Process:
        1. Check rate limiting (1 OTP per minute)
        2. Invalidate previous unused OTPs for same purpose
        3. Generate new 6-digit OTP code
        4. Hash code with SHA-256
        5. Insert record with 10-minute expiration (NIST/OWASP compliant)
        6. Return plain-text code (for email) and record

        Security:
            Plain-text code is only returned once (for email).
            Database stores SHA-256 hash only.
        """
        try:
            self.logger.info(
                "Creating OTP",
                email=email,
                purpose=purpose.value,
                user_id=user_id
            )

            # Step 1: Check rate limiting
            can_request, cooldown_remaining = await self.can_request_otp(email, purpose)
            if not can_request:
                error_msg = (
                    f"Please wait {cooldown_remaining} seconds before requesting a new code."
                )
                self.logger.warning(
                    "OTP rate limit exceeded",
                    email=email,
                    cooldown_remaining=cooldown_remaining
                )
                self.metrics.increment_counter("otp_creation_rate_limited")
                return None, None, error_msg

            # Step 2: Invalidate previous unused OTPs (mark as used)
            invalidate_query = f"""
                UPDATE {config.SCHEMA_NAME}.demo_otp_codes
                SET is_used = true,
                    updated_at = %s
                WHERE user_id = %s
                  AND purpose = %s
                  AND is_used = false
            """
            now = datetime.now(timezone.utc)
            await self.db.execute(invalidate_query, (now, user_id, purpose.value))

            # Step 3: Generate new OTP code
            otp_code = self.generate_otp_code()

            # Step 4: Hash code
            code_hash = self.hash_otp_code(otp_code)

            # Step 5: Insert OTP record
            # FIX: Use minutes instead of hours for NIST/OWASP compliance (10 min)
            expires_at = now + timedelta(minutes=self.expiration_minutes)

            insert_query = f"""
                INSERT INTO {config.SCHEMA_NAME}.demo_otp_codes
                (user_id, email, code_hash, purpose, expires_at,
                 max_attempts, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s::inet, %s)
                RETURNING id, user_id, email, code_hash, purpose,
                          expires_at, attempts_count, max_attempts,
                          is_used, used_at, ip_address, user_agent,
                          created_at, updated_at
            """

            result = await self.db.execute_one(
                insert_query,
                (
                    user_id,
                    email,
                    code_hash,
                    purpose.value,
                    expires_at,
                    self.max_attempts,
                    ip_address,
                    user_agent,
                ),
            )

            if not result:
                self.logger.error(
                    "Failed to insert OTP",
                    email=email,
                    user_id=user_id
                )
                self.metrics.increment_counter("otp_creation_failures")
                return None, None, "Failed to generate verification code."

            otp_record = OTPDB(**result)

            self.logger.info(
                "OTP created successfully",
                email=email,
                otp_id=otp_record.id,
                user_id=user_id,
                expires_at=expires_at.isoformat()
            )
            self.metrics.increment_counter("otp_codes_created")

            # Return plain-text code (for email) and record
            return otp_code, otp_record, None

        except Exception as e:
            self.logger.exception(
                "Error in create_otp",
                email=email,
                user_id=user_id
            )
            self.metrics.increment_counter("otp_creation_errors")
            return None, None, "Failed to generate verification code."

    async def verify_otp(
        self,
        email: str,
        otp_code: str,
        purpose: OTPPurpose = OTPPurpose.EMAIL_VERIFICATION,
    ) -> Tuple[bool, int | None, str]:
        """Verify OTP code for email.

        Args:
            email: User email address.
            otp_code: Plain-text 6-digit code from user.
            purpose: OTP purpose (default: email_verification).

        Returns:
            Tuple[is_valid, user_id, message]:
            - is_valid: True if code is valid
            - user_id: User ID (if valid)
            - message: Success/error message

        Process:
        1. Find active OTP for email (not used, not expired)
        2. Check if max attempts exceeded
        3. Verify code against hash
        4. If valid: mark as used, return success
        5. If invalid: increment attempts, return failure

        Security:
            - Constant-time hash comparison (prevent timing attacks)
            - Max 3 attempts per OTP (prevent brute force)
            - Auto-invalidate after expiration
        """
        try:
            logger.debug(f"Verifying OTP for {email} (purpose: {purpose.value})")

            # Step 1: Find active OTP
            query = f"""
                SELECT id, user_id, email, code_hash, purpose,
                       expires_at, attempts_count, max_attempts,
                       is_used, used_at, ip_address, user_agent,
                       created_at, updated_at
                FROM {config.SCHEMA_NAME}.demo_otp_codes
                WHERE email = %s
                  AND purpose = %s
                  AND is_used = false
                  AND expires_at > %s
                ORDER BY created_at DESC
                LIMIT 1
            """

            now = datetime.now(timezone.utc)
            result = await self.db.execute_one(query, (email, purpose.value, now))

            if not result:
                logger.warning(f"No active OTP found for {email}")
                return (
                    False,
                    None,
                    "Invalid or expired verification code. Please request a new one.",
                )

            otp_record = OTPDB(**result)

            # Step 2: Check if max attempts exceeded
            if otp_record.attempts_count >= otp_record.max_attempts:
                logger.warning(
                    f"Max OTP attempts exceeded for {email} (OTP ID: {otp_record.id})"
                )
                return (
                    False,
                    None,
                    "Maximum verification attempts exceeded. Please request a new code.",
                )

            # Step 3: Verify code against hash
            is_valid = self.verify_otp_hash(otp_code, otp_record.code_hash)

            if is_valid:
                # Step 4: Mark OTP as used
                update_query = f"""
                    UPDATE {config.SCHEMA_NAME}.demo_otp_codes
                    SET is_used = true,
                        used_at = %s,
                        updated_at = %s
                    WHERE id = %s
                """
                await self.db.execute(update_query, (now, now, otp_record.id))

                logger.info(
                    f"OTP verified successfully for {email} (OTP ID: {otp_record.id})"
                )
                return True, otp_record.user_id, "Email verified successfully!"

            else:
                # Step 5: Increment attempts
                new_attempts = otp_record.attempts_count + 1
                update_query = f"""
                    UPDATE {config.SCHEMA_NAME}.demo_otp_codes
                    SET attempts_count = %s,
                        updated_at = %s
                    WHERE id = %s
                """
                await self.db.execute(update_query, (new_attempts, now, otp_record.id))

                remaining_attempts = otp_record.max_attempts - new_attempts
                logger.warning(
                    f"Invalid OTP for {email} ({remaining_attempts} attempts remaining)"
                )

                if remaining_attempts > 0:
                    return (
                        False,
                        None,
                        f"Invalid verification code. {remaining_attempts} attempts remaining.",
                    )
                else:
                    return (
                        False,
                        None,
                        "Invalid code. Maximum attempts exceeded. Please request a new code.",
                    )

        except Exception as e:
            logger.exception(f"Error in verify_otp: {e}")
            return False, None, "An error occurred during verification."

    async def cleanup_expired_otps(self) -> int:
        """Delete expired OTP codes (older than 48 hours).

        Returns:
            int: Number of OTP codes deleted.

        Note:
            Should be called periodically (e.g., daily cron job).
        """
        try:
            query = f"SELECT {config.SCHEMA_NAME}.cleanup_expired_otp_codes()"
            result = await self.db.execute_one(query)

            deleted_count = result.get("cleanup_expired_otp_codes", 0) if result else 0

            logger.info(f"Cleaned up {deleted_count} expired OTP codes")
            return deleted_count

        except Exception as e:
            logger.exception(f"Error in cleanup_expired_otps: {e}")
            return 0

    async def get_active_otp(
        self, user_id: int, purpose: OTPPurpose = OTPPurpose.EMAIL_VERIFICATION
    ) -> OTPDB | None:
        """Get active OTP for user (if exists).

        Args:
            user_id: User ID.
            purpose: OTP purpose.

        Returns:
            OTPDB: Active OTP record (or None).

        Note:
            Returns most recent active OTP only.
        """
        try:
            query = f"""
                SELECT id, user_id, email, code_hash, purpose,
                       expires_at, attempts_count, max_attempts,
                       is_used, used_at, ip_address, user_agent,
                       created_at, updated_at
                FROM {config.SCHEMA_NAME}.demo_otp_codes
                WHERE user_id = %s
                  AND purpose = %s
                  AND is_used = false
                  AND expires_at > %s
                ORDER BY created_at DESC
                LIMIT 1
            """

            now = datetime.now(timezone.utc)
            result = await self.db.execute_one(query, (user_id, purpose.value, now))

            if result:
                return OTPDB(**result)
            return None

        except Exception as e:
            logger.exception(f"Error in get_active_otp: {e}")
            return None
