"""Webhook Routes.

Webhook endpoints for external service integrations (Clerk, etc.).

Author: Lab01-MCP Team
Created: 2025-11-10
Version: 1.0.0
"""

from typing import Any

from fastapi import APIRouter, Header, Request

from demo_agent.webhooks.clerk_webhooks import get_clerk_webhook_handler

router = APIRouter(prefix="/v1/webhooks", tags=["Webhooks"])


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    svix_id: str = Header(..., alias="svix-id"),
    svix_timestamp: str = Header(..., alias="svix-timestamp"),
    svix_signature: str = Header(..., alias="svix-signature"),
) -> dict[str, Any]:
    """Receive webhooks from Clerk Identity Provider.

    Processes user and session events:
    - user.created: New user registration
    - user.updated: User profile changes
    - user.deleted: User account deletion
    - session.created: New login session

    Headers Required:
    - svix-id: Webhook message ID
    - svix-timestamp: Event timestamp
    - svix-signature: HMAC-SHA256 signature for verification

    Security:
    - Verifies webhook signature to prevent spoofing
    - Rejects events older than 5 minutes (replay protection)

    Response (Success):
    ```json
    {
      "success": true,
      "message": "Event user.created processed successfully",
      "event_id": "msg_2abc..."
    }
    ```

    Response (Error):
    ```json
    {
      "success": false,
      "error": "Invalid webhook signature"
    }
    ```

    Args:
        request: FastAPI request object.
        svix_id: Webhook message ID.
        svix_timestamp: Event timestamp.
        svix_signature: HMAC-SHA256 signature.

    Returns:
        dict: Webhook processing result.
    """
    webhook_handler = get_clerk_webhook_handler()
    return await webhook_handler.handle_webhook(
        request=request,
        svix_id=svix_id,
        svix_timestamp=svix_timestamp,
        svix_signature=svix_signature,
    )
