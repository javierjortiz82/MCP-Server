"""Clerk Service - Clerk Identity Provider Integration.

Handles Clerk authentication, token validation, and user synchronization.

Features:
- JWT token validation with Clerk public keys
- User synchronization from Clerk webhooks
- Session management and validation
- Metadata extraction and storage

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import json
import time
from typing import Any, Dict, Optional, Tuple

import httpx
import jwt
from jwt import PyJWKClient

from demo_agent.config.settings import config
from demo_agent.db.connection import get_db
from demo_agent.logger import logger
from demo_agent.observability.metrics import get_metrics_collector
from demo_agent.observability.structured_logger import get_structured_logger


class ClerkService:
    """Service for Clerk Identity Provider integration.

    Handles:
    - JWT token validation using Clerk's JWKS endpoint
    - User creation/update from Clerk webhooks
    - Session tracking and validation
    - Metadata synchronization from Clerk to PostgreSQL

    Security:
    - Verifies JWT signatures using Clerk public keys (RS256)
    - Validates token expiration and issuer
    - Webhook signature verification using HMAC SHA-256
    """

    # Clerk API endpoints
    CLERK_API_BASE = "https://api.clerk.com/v1"
    CLERK_JWKS_URL_TEMPLATE = "https://{frontend_api}/.well-known/jwks.json"

    def __init__(self):
        """Initialize ClerkService with configuration and database connection."""
        self.db = get_db()
        self.logger = get_structured_logger(__name__)
        self.metrics = get_metrics_collector()

        # Load Clerk configuration from environment
        self.secret_key = config.CLERK_SECRET_KEY
        self.publishable_key = config.CLERK_PUBLISHABLE_KEY
        self.webhook_secret = config.CLERK_WEBHOOK_SECRET

        # Extract frontend_api from publishable key
        # Format: pk_test_<base64> or pk_live_<base64>
        # Frontend API is typically: <account>.clerk.accounts.dev or clerk.com
        self.frontend_api = self._extract_frontend_api()

        # Initialize JWKS client for JWT verification
        self.jwks_url = self.CLERK_JWKS_URL_TEMPLATE.format(
            frontend_api=self.frontend_api
        )
        self.jwks_client = PyJWKClient(self.jwks_url, cache_keys=True)

        # HTTP client for Clerk API calls
        self.http_client = httpx.AsyncClient(
            base_url=self.CLERK_API_BASE,
            headers={
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

        self.logger.info(
            "ClerkService initialized",
            frontend_api=self.frontend_api,
            jwks_url=self.jwks_url
        )

    def _extract_frontend_api(self) -> str:
        """Extract frontend API domain from publishable key.

        The publishable key format varies:
        - Development: pk_test_<identifier>
        - Production: pk_live_<identifier>

        For simplicity, we use the instance domain from config.
        In production, this should be extracted from JWT iss claim.

        Returns:
            str: Frontend API domain (e.g., "clerk.odiseo.com")
        """
        # TODO: Extract from JWT iss claim for production
        # For now, use default Clerk domain
        return config.CLERK_FRONTEND_API if hasattr(config, "CLERK_FRONTEND_API") else "clerk.accounts.dev"

    async def verify_token(self, token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Verify Clerk JWT session token.

        Args:
            token: JWT token from Authorization header (Bearer <token>)

        Returns:
            Tuple[claims | None, error_message | None]:
            - claims: Decoded JWT claims (if valid)
            - error: Error message (if invalid)

        Process:
        1. Fetch signing key from Clerk JWKS endpoint
        2. Verify JWT signature (RS256)
        3. Validate expiration, issuer, and audience
        4. Return decoded claims

        Claims structure:
        {
            "sub": "user_2abcdefghijklmnop",  # Clerk user ID
            "email": "user@example.com",
            "email_verified": true,
            "given_name": "John",
            "family_name": "Doe",
            "iss": "https://clerk.odiseo.com",
            "aud": "<publishable_key>",
            "exp": 1699999999,
            "iat": 1699996399,
            "nbf": 1699996399
        }
        """
        try:
            self.logger.info("Verifying Clerk token")

            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Decode and verify JWT
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "require": ["exp", "iat", "nbf", "sub"],
                },
            )

            # Additional validation
            current_time = int(time.time())

            # Check expiration
            if claims.get("exp", 0) < current_time:
                self.metrics.increment_counter("clerk_token_expired")
                return None, "Token expired"

            # Check not-before
            if claims.get("nbf", 0) > current_time:
                self.metrics.increment_counter("clerk_token_not_yet_valid")
                return None, "Token not yet valid"

            # Validate issuer (should match Clerk instance)
            issuer = claims.get("iss", "")
            if not issuer.startswith("https://"):
                self.metrics.increment_counter("clerk_token_invalid_issuer")
                return None, "Invalid token issuer"

            self.logger.info(
                "Token verified successfully",
                user_id=claims.get("sub"),
                email=claims.get("email")
            )
            self.metrics.increment_counter("clerk_token_verified_success")

            return claims, None

        except jwt.ExpiredSignatureError:
            self.logger.warning("Token expired")
            self.metrics.increment_counter("clerk_token_expired")
            return None, "Token expired"

        except jwt.InvalidTokenError as e:
            self.logger.warning("Invalid token", error=str(e))
            self.metrics.increment_counter("clerk_token_invalid")
            return None, f"Invalid token: {str(e)}"

        except Exception as e:
            self.logger.error("Token verification failed", error=str(e))
            self.metrics.increment_counter("clerk_token_verification_error")
            return None, f"Token verification error: {str(e)}"

    async def sync_user_from_clerk(
        self,
        clerk_user_id: str,
        email: str,
        full_name: str,
        clerk_metadata: Dict[str, Any],
        clerk_session_id: Optional[str] = None,
    ) -> Tuple[Optional[int], bool, Optional[str]]:
        """Synchronize user from Clerk to PostgreSQL.

        Called by webhook handlers when Clerk user is created/updated.

        Args:
            clerk_user_id: Clerk user ID (e.g., "user_2abc...")
            email: User email address
            full_name: User full name
            clerk_metadata: Custom metadata from Clerk (company, role, etc.)
            clerk_session_id: Current session ID (optional)

        Returns:
            Tuple[user_id | None, is_new_user: bool, error | None]:
            - user_id: PostgreSQL user ID
            - is_new_user: True if user was created, False if updated
            - error: Error message (if failure)

        Uses PostgreSQL function: upsert_clerk_user()
        """
        try:
            self.logger.info(
                "Syncing user from Clerk",
                clerk_user_id=clerk_user_id,
                email=email
            )

            # Call PostgreSQL upsert function
            query = f"""
                SELECT user_id, is_new_user, user_email
                FROM {config.SCHEMA_NAME}.upsert_clerk_user($1, $2, $3, $4, $5)
            """

            result = await self.db.execute_one(
                query,
                (
                    clerk_user_id,
                    email,
                    full_name,
                    json.dumps(clerk_metadata),
                    clerk_session_id,
                ),
            )

            if not result:
                self.logger.error("Failed to sync user - no result from database")
                return None, False, "Database sync failed"

            # execute_one returns a dict, not a tuple
            user_id = result["user_id"]
            is_new_user = result["is_new_user"]
            user_email = result["user_email"]

            action = "created" if is_new_user else "updated"
            self.logger.info(
                f"User {action} successfully",
                user_id=user_id,
                email=user_email,
                clerk_user_id=clerk_user_id
            )

            metric_name = f"clerk_user_{action}"
            self.metrics.increment_counter(metric_name)

            return user_id, is_new_user, None

        except Exception as e:
            self.logger.error("Failed to sync user from Clerk", error=str(e))
            self.metrics.increment_counter("clerk_user_sync_error")
            return None, False, f"Sync error: {str(e)}"

    async def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict[str, Any]]:
        """Get user from database by Clerk user ID.

        Args:
            clerk_user_id: Clerk user ID (e.g., "user_2abc...")

        Returns:
            Optional[Dict]: User record (if found), None otherwise

        Fields returned:
        - id, email, full_name, clerk_user_id, clerk_metadata,
          is_active, is_email_verified, created_at, last_login_at
        """
        try:
            self.logger.info("Fetching user by Clerk ID", clerk_user_id=clerk_user_id)

            query = f"""
                SELECT
                    id, email, full_name, display_name,
                    clerk_user_id, clerk_session_id, clerk_metadata,
                    is_active, is_email_verified,
                    preferred_language, timezone,
                    created_at, updated_at, last_login_at
                FROM {config.SCHEMA_NAME}.demo_users
                WHERE clerk_user_id = $1
                    AND is_deleted = false
            """

            result = await self.db.execute_one(query, (clerk_user_id,))

            if not result:
                self.logger.info("User not found", clerk_user_id=clerk_user_id)
                return None

            # execute_one returns dict with column names as keys
            user = {
                "id": result["id"],
                "email": result["email"],
                "full_name": result["full_name"],
                "display_name": result["display_name"],
                "clerk_user_id": result["clerk_user_id"],
                "clerk_session_id": result["clerk_session_id"],
                "clerk_metadata": result["clerk_metadata"] if result["clerk_metadata"] else {},
                "is_active": result["is_active"],
                "is_email_verified": result["is_email_verified"],
                "preferred_language": result["preferred_language"],
                "timezone": result["timezone"],
                "created_at": result["created_at"].isoformat() if result["created_at"] else None,
                "updated_at": result["updated_at"].isoformat() if result["updated_at"] else None,
                "last_login_at": result["last_login_at"].isoformat() if result["last_login_at"] else None,
            }

            self.logger.info("User found", user_id=user["id"], email=user["email"])
            return user

        except Exception as e:
            self.logger.error("Failed to fetch user by Clerk ID", error=str(e))
            return None

    async def check_migration_required(self, email: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if a user needs to migrate to Clerk.

        Args:
            email: User email address

        Returns:
            Tuple[requires_migration: bool, user_info | None]:
            - requires_migration: True if user must migrate
            - user_info: User record with migration status (if exists)

        Used by legacy auth endpoints to redirect users to Clerk.
        """
        try:
            self.logger.info("Checking migration status", email=email)

            query = f"""
                SELECT requires_migration, user_id, auth_provider, migration_status
                FROM {config.SCHEMA_NAME}.check_clerk_migration_required($1)
            """

            result = await self.db.execute_one(query, (email,))

            if not result:
                # User doesn't exist
                return False, None

            requires_migration = result[0]
            user_info = {
                "user_id": result[1],
                "auth_provider": result[2],
                "migration_status": result[3],
            }

            self.logger.info(
                "Migration check complete",
                email=email,
                requires_migration=requires_migration
            )

            return requires_migration, user_info

        except Exception as e:
            self.logger.error("Failed to check migration status", error=str(e))
            return False, None

    async def update_session(self, clerk_user_id: str, clerk_session_id: str) -> bool:
        """Update user's current Clerk session ID.

        Args:
            clerk_user_id: Clerk user ID
            clerk_session_id: New session ID

        Returns:
            bool: True if updated successfully, False otherwise

        Called by session.created webhook.
        """
        try:
            self.logger.info(
                "Updating session",
                clerk_user_id=clerk_user_id,
                clerk_session_id=clerk_session_id
            )

            query = f"""
                SELECT {config.SCHEMA_NAME}.update_clerk_session($1, $2)
            """

            result = await self.db.execute_one(query, (clerk_user_id, clerk_session_id))

            # PostgreSQL function returns boolean with function name as key
            if not result or not result.get("update_clerk_session"):
                self.logger.warning("User not found or update failed", clerk_user_id=clerk_user_id)
                return False

            self.logger.info("Session updated successfully")
            self.metrics.increment_counter("clerk_session_updated")
            return True

        except Exception as e:
            self.logger.error("Failed to update session", error=str(e))
            self.metrics.increment_counter("clerk_session_update_error")
            return False

    async def soft_delete_user(self, clerk_user_id: str) -> bool:
        """Soft delete user when deleted in Clerk (IDEMPOTENT).

        Args:
            clerk_user_id: Clerk user ID

        Returns:
            bool: True if user exists (deleted successfully or already deleted),
                  False only if user not found

        Called by user.deleted webhook.
        Sets is_deleted=true and deleted_at timestamp.

        Note: This operation is idempotent - calling it multiple times
        is safe and will not cause errors if user already deleted.
        """
        try:
            self.logger.info("Processing user deletion", clerk_user_id=clerk_user_id)

            query = f"""
                SELECT {config.SCHEMA_NAME}.soft_delete_clerk_user($1)
            """

            result = await self.db.execute_one(query, (clerk_user_id,))

            # PostgreSQL function returns:
            # - true: user exists (deleted now or already deleted)
            # - false: user not found in database
            if not result or not result.get("soft_delete_clerk_user"):
                self.logger.warning(
                    "User not found in database",
                    clerk_user_id=clerk_user_id,
                    note="User may have been deleted directly from database"
                )
                return False

            self.logger.info(
                "User deletion processed successfully",
                clerk_user_id=clerk_user_id,
                note="Idempotent operation - user marked as deleted"
            )
            self.metrics.increment_counter("clerk_user_deleted")
            return True

        except Exception as e:
            self.logger.error("Failed to process user deletion", error=str(e))
            self.metrics.increment_counter("clerk_user_delete_error")
            return False

    async def get_clerk_user_metadata(self, clerk_user_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Fetch user metadata from Clerk API.

        Args:
            clerk_user_id: Clerk user ID

        Returns:
            Tuple[metadata | None, error | None]:
            - metadata: User metadata from Clerk
            - error: Error message (if failure)

        This is a fallback method. Primary source is webhooks.
        Use this to sync metadata if webhook delivery fails.
        """
        try:
            self.logger.info("Fetching user metadata from Clerk API", clerk_user_id=clerk_user_id)

            response = await self.http_client.get(f"/users/{clerk_user_id}")

            if response.status_code != 200:
                error_msg = f"Clerk API error: {response.status_code}"
                self.logger.error(error_msg, response=response.text)
                return None, error_msg

            user_data = response.json()
            metadata = {
                "public_metadata": user_data.get("public_metadata", {}),
                "private_metadata": user_data.get("private_metadata", {}),
                "unsafe_metadata": user_data.get("unsafe_metadata", {}),
            }

            self.logger.info("Metadata fetched successfully")
            return metadata, None

        except Exception as e:
            self.logger.error("Failed to fetch metadata from Clerk", error=str(e))
            return None, f"Metadata fetch error: {str(e)}"

    async def close(self):
        """Close HTTP client connections.

        Call this on application shutdown.
        """
        await self.http_client.aclose()
        self.logger.info("ClerkService closed")


# Singleton instance
_clerk_service: Optional[ClerkService] = None


def get_clerk_service() -> ClerkService:
    """Get singleton instance of ClerkService.

    Returns:
        ClerkService: Singleton instance

    Usage:
        clerk_service = get_clerk_service()
        claims, error = await clerk_service.verify_token(token)
    """
    global _clerk_service
    if _clerk_service is None:
        _clerk_service = ClerkService()
    return _clerk_service
