"""Clerk Webhook Handler - Process Clerk Events.

Receives and processes webhooks from Clerk for user and session events.

Supported Events:
- user.created: New user registered via Clerk
- user.updated: User profile updated in Clerk
- user.deleted: User deleted in Clerk
- session.created: New session created (user logged in)

Security:
- Verifies webhook signatures using Svix library
- Rejects invalid signatures to prevent spoofing
- Uses Clerk webhook secret from environment

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.1.0
"""

import json
from typing import Any

from fastapi import Header, HTTPException, Request, status
from svix.webhooks import Webhook, WebhookVerificationError

from demo_agent.config.settings import config
from demo_agent.observability.metrics import get_metrics_collector
from demo_agent.observability.structured_logger import get_structured_logger
from demo_agent.services.clerk_service import get_clerk_service


class ClerkWebhookHandler:
    """Handler for Clerk webhook events.

    Processes user and session events from Clerk Identity Provider.
    Synchronizes user data to PostgreSQL for persistence.

    Webhook Signature Verification:
    - Clerk signs webhooks with HMAC SHA-256
    - Signature is sent in svix-signature header
    - Format: v1,<timestamp>,<signature>
    - Timestamp prevents replay attacks (max 5 min old)

    Event Types:
    - user.created: Sync new user to database
    - user.updated: Update user info in database
    - user.deleted: Soft delete user in database
    - session.created: Update session ID and last_login
    """

    def __init__(self):
        """Initialize Clerk webhook handler."""
        self.clerk_service = get_clerk_service()
        self.logger = get_structured_logger(__name__)
        self.metrics = get_metrics_collector()
        self.webhook_secret = config.CLERK_WEBHOOK_SECRET
        self.wh = Webhook(self.webhook_secret)
        self.logger.info("ClerkWebhookHandler initialized")

    def verify_webhook_signature(
        self,
        payload: bytes,
        headers: dict,
    ) -> None:
        """Verify Clerk webhook signature using Svix library.

        Clerk uses Svix for webhook delivery. This method uses the official
        Svix library to verify webhook signatures following the standard documented at:
        https://docs.svix.com/receiving/verifying-payloads/how

        SECURITY (CWE-345 fix): Raises exceptions instead of returning False
        to ensure signature verification failures are never silently ignored.

        Args:
            payload: Raw request body (bytes) - must be unmodified from request
            headers: Dict with svix-id, svix-timestamp, and svix-signature

        Raises:
            ValueError: If webhook secret is not configured
            WebhookVerificationError: If signature verification fails
            Exception: For other verification errors
        """
        if not self.webhook_secret:
            self.logger.error("Webhook secret not configured")
            raise ValueError("Webhook secret not configured - cannot verify signatures")

        # Verify using official Svix library
        # According to docs: wh.verify() accepts raw payload (bytes or string)
        # and headers dict directly from request
        # This will raise WebhookVerificationError if invalid
        self.wh.verify(payload, headers)

        self.logger.info("Webhook signature verified successfully")

    async def handle_webhook(
        self,
        request: Request,
        svix_id: str = Header(None, alias="svix-id"),
        svix_timestamp: str = Header(None, alias="svix-timestamp"),
        svix_signature: str = Header(None, alias="svix-signature"),
    ) -> dict[str, Any]:
        """Main webhook handler endpoint.

        Args:
            request: FastAPI request object
            svix_id: Webhook message ID (from header)
            svix_timestamp: Webhook timestamp (from header)
            svix_signature: Webhook signature (from header)

        Returns:
            Dict: Response with success status and message

        Raises:
            HTTPException: 400 if signature is invalid or event processing fails
        """
        # Read raw body for signature verification
        payload = await request.body()

        # Verify headers are present
        if not all([svix_id, svix_timestamp, svix_signature]):
            self.logger.error(
                "Missing Svix headers",
                has_id=bool(svix_id),
                has_timestamp=bool(svix_timestamp),
                has_signature=bool(svix_signature)
            )
            self.metrics.increment_counter("clerk_webhook_missing_headers")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required Svix headers"
            )

        # Verify signature using official Svix pattern (raises on failure)
        headers = {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        }

        try:
            self.verify_webhook_signature(payload, headers)
        except (WebhookVerificationError, ValueError) as e:
            self.logger.error(
                "Webhook signature verification failed",
                svix_id=svix_id,
                error=str(e)
            )
            self.metrics.increment_counter("clerk_webhook_invalid_signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            ) from e

        # Parse JSON payload
        try:
            event = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError as e:
            self.logger.error("Invalid JSON payload", error=str(e))
            self.metrics.increment_counter("clerk_webhook_invalid_json")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            ) from e

        # Extract event type and data
        event_type = event.get("type")
        event_data = event.get("data", {})

        self.logger.info(
            "Processing Clerk webhook",
            event_type=event_type,
            svix_id=svix_id
        )
        self.metrics.increment_counter(f"clerk_webhook_{event_type}")

        # Route to appropriate handler
        try:
            if event_type == "user.created":
                await self._handle_user_created(event_data)
            elif event_type == "user.updated":
                await self._handle_user_updated(event_data)
            elif event_type == "user.deleted":
                await self._handle_user_deleted(event_data)
            elif event_type == "session.created":
                await self._handle_session_created(event_data)
            else:
                self.logger.warning(f"Unhandled event type: {event_type}")
                self.metrics.increment_counter("clerk_webhook_unhandled_type")

            return {
                "success": True,
                "message": f"Event {event_type} processed successfully",
                "event_id": svix_id,
            }

        except Exception as e:
            self.logger.error(
                "Error processing webhook event",
                event_type=event_type,
                error=str(e)
            )
            self.metrics.increment_counter("clerk_webhook_processing_error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing event: {str(e)}"
            ) from e

    async def _handle_user_created(self, data: dict[str, Any]) -> None:
        """Handle user.created event.

        Creates new user record in PostgreSQL.

        Args:
            data: Clerk user object

        Data structure:
        {
            "id": "user_2abc...",
            "email_addresses": [{"email_address": "user@example.com", "id": "..."}],
            "first_name": "John",
            "last_name": "Doe",
            "public_metadata": {"company": "Acme"},
            "private_metadata": {},
            ...
        }
        """
        try:
            # Extract user info
            clerk_user_id = data.get("id")
            email_addresses = data.get("email_addresses", [])
            primary_email = email_addresses[0]["email_address"] if email_addresses else None

            if not clerk_user_id or not primary_email:
                self.logger.error("Missing required user data", data=data)
                return

            # Construct full name
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip() or primary_email.split("@")[0]

            # Extract metadata
            clerk_metadata = {
                "public_metadata": data.get("public_metadata", {}),
                "private_metadata": data.get("private_metadata", {}),
                "profile_image_url": data.get("profile_image_url"),
                "created_at": data.get("created_at"),
            }

            # Sync to database
            user_id, is_new, error = await self.clerk_service.sync_user_from_clerk(
                clerk_user_id=clerk_user_id,
                email=primary_email,
                full_name=full_name,
                clerk_metadata=clerk_metadata,
            )

            if error:
                self.logger.error("Failed to sync user", error=error)
                return

            self.logger.info(
                "User created successfully",
                user_id=user_id,
                email=primary_email,
                clerk_user_id=clerk_user_id
            )

        except Exception as e:
            self.logger.error("Error handling user.created event", error=str(e))
            raise

    async def _handle_user_updated(self, data: dict[str, Any]) -> None:
        """Handle user.updated event.

        Updates existing user record in PostgreSQL.

        Args:
            data: Clerk user object (same structure as user.created)
        """
        try:
            # Extract user info (same as user.created)
            clerk_user_id = data.get("id")
            email_addresses = data.get("email_addresses", [])
            primary_email = email_addresses[0]["email_address"] if email_addresses else None

            if not clerk_user_id or not primary_email:
                self.logger.error("Missing required user data", data=data)
                return

            # Construct full name
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip() or primary_email.split("@")[0]

            # Extract metadata
            clerk_metadata = {
                "public_metadata": data.get("public_metadata", {}),
                "private_metadata": data.get("private_metadata", {}),
                "profile_image_url": data.get("profile_image_url"),
                "updated_at": data.get("updated_at"),
            }

            # Sync to database (upsert will update existing user)
            user_id, is_new, error = await self.clerk_service.sync_user_from_clerk(
                clerk_user_id=clerk_user_id,
                email=primary_email,
                full_name=full_name,
                clerk_metadata=clerk_metadata,
            )

            if error:
                self.logger.error("Failed to update user", error=error)
                return

            self.logger.info(
                "User updated successfully",
                user_id=user_id,
                email=primary_email,
                clerk_user_id=clerk_user_id
            )

        except Exception as e:
            self.logger.error("Error handling user.updated event", error=str(e))
            raise

    async def _handle_user_deleted(self, data: dict[str, Any]) -> None:
        """Handle user.deleted event.

        Soft deletes user in PostgreSQL (sets is_deleted=true).

        Args:
            data: Clerk user object with minimal info

        Data structure:
        {
            "id": "user_2abc...",
            "deleted": true,
            ...
        }
        """
        try:
            clerk_user_id = data.get("id")

            if not clerk_user_id:
                self.logger.error("Missing user ID in delete event", data=data)
                return

            # Soft delete user
            success = await self.clerk_service.soft_delete_user(clerk_user_id)

            if success:
                self.logger.info("User deleted successfully", clerk_user_id=clerk_user_id)
            else:
                self.logger.error("Failed to delete user", clerk_user_id=clerk_user_id)

        except Exception as e:
            self.logger.error("Error handling user.deleted event", error=str(e))
            raise

    async def _handle_session_created(self, data: dict[str, Any]) -> None:
        """Handle session.created event.

        Updates user's session ID and last_login timestamp.

        Args:
            data: Clerk session object

        Data structure:
        {
            "id": "sess_xyz123",
            "user_id": "user_2abc...",
            "created_at": 1699999999,
            ...
        }
        """
        try:
            session_id = data.get("id")
            clerk_user_id = data.get("user_id")

            if not session_id or not clerk_user_id:
                self.logger.error("Missing session or user ID", data=data)
                return

            # Update session in database
            success = await self.clerk_service.update_session(clerk_user_id, session_id)

            if success:
                self.logger.info(
                    "Session updated successfully",
                    clerk_user_id=clerk_user_id,
                    session_id=session_id
                )
            else:
                self.logger.error(
                    "Failed to update session",
                    clerk_user_id=clerk_user_id,
                    session_id=session_id
                )

        except Exception as e:
            self.logger.error("Error handling session.created event", error=str(e))
            raise


# Singleton instance
_clerk_webhook_handler: ClerkWebhookHandler | None = None


def get_clerk_webhook_handler() -> ClerkWebhookHandler:
    """Get singleton instance of ClerkWebhookHandler.

    Returns:
        ClerkWebhookHandler: Singleton instance

    Usage:
        handler = get_clerk_webhook_handler()
        response = await handler.handle_webhook(request, ...)
    """
    global _clerk_webhook_handler
    if _clerk_webhook_handler is None:
        _clerk_webhook_handler = ClerkWebhookHandler()
    return _clerk_webhook_handler
