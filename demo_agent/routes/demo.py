"""Demo Agent Routes.

Demo query endpoints with token-bucket rate limiting and quota management.

Author: Lab01-MCP Team
Created: 2025-11-10
Version: 1.0.0
"""

import json
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from demo_agent.logger import logger
from demo_agent.models.requests import DemoRequest
from demo_agent.models.responses import DemoResponse
from demo_agent.security.clerk_middleware import get_current_user
from demo_agent.services.client_ip_service import extract_client_ip
from demo_agent.utils.sanitizers import (
    sanitize_error_message,
    sanitize_html,
    sanitize_user_input,
)
from demo_agent.utils.validators import validate_session_id

router = APIRouter(prefix="/v1/demo", tags=["Demo"])


def get_services(request: Request):
    """Get service instances from app state.

    Args:
        request: FastAPI request object.

    Returns:
        tuple: (demo_agent, user_service)

    Raises:
        HTTPException: If services are not initialized.
    """
    demo_agent = request.app.state.demo_agent
    user_service = request.app.state.user_service

    if not demo_agent or not user_service:
        raise HTTPException(status_code=500, detail="Services not initialized")

    return demo_agent, user_service


@router.post("", response_model=DemoResponse)
async def demo_query(request_data: DemoRequest, request: Request):
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

    Args:
        request_data: Demo query request data.
        request: FastAPI request object.

    Returns:
        DemoResponse: Query result with token usage information.

    Raises:
        HTTPException: 401 if not authenticated, 500 on server error.
    """
    try:
        demo_agent, user_service = get_services(request)

        # STEP 1: Get authenticated user from Clerk middleware
        # SECURITY: Only Clerk authentication is allowed (CWE-862 fix)
        authenticated_user = get_current_user(request)

        if not authenticated_user or not authenticated_user.get("db_user_id"):
            # No Clerk authentication found - reject request
            logger.error("Authentication required: No valid Clerk session found")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "authentication_required",
                    "message": "Please log in with Clerk to use this endpoint.",
                },
            )

        # User authenticated via Clerk - use db_user_id from middleware
        user_id = authenticated_user["db_user_id"]
        logger.info(f"Clerk-authenticated user: {user_id}")

        # STEP 2: Validate user exists and is active
        user_query = """
            SELECT id, email, is_active, is_email_verified, is_suspended, is_deleted
            FROM :SCHEMA_NAME.demo_users
            WHERE id = %s
        """
        user_result = await user_service.db.execute_one(user_query, (user_id,))

        if not user_result:
            logger.warning(f"User ID {user_id} not found")
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
            logger.warning(f"User ID {user_id} is not active")
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
            logger.warning(f"User ID {user_id} email not verified")
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": "email_not_verified",
                    "message": "Please verify your email address first.",
                },
            )

        if user_result.get("is_suspended"):
            logger.warning(f"User ID {user_id} is suspended")
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": "account_suspended",
                    "message": "Your account has been suspended.",
                },
            )

        if user_result.get("is_deleted"):
            logger.warning(f"User ID {user_id} is deleted")
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": "account_deleted",
                    "message": "Your account has been deleted.",
                },
            )

        # STEP 3: Use user_id as user_key for token tracking
        user_key = str(user_id)
        user_email = user_result.get("email")

        # SECURITY (CWE-384 fix): Validate or generate session_id
        if request_data.session_id:
            # Validate provided session_id is a valid UUID v4
            is_valid, error_msg = validate_session_id(request_data.session_id)
            if not is_valid:
                logger.warning(
                    f"Invalid session_id format from user {user_id}: {error_msg}"
                )
                # Generate new secure session_id instead of using invalid one
                session_id = str(uuid4())
            else:
                session_id = request_data.session_id
        else:
            # Generate new secure session_id
            session_id = str(uuid4())

        logger.info(f"Demo query from active user: {user_email} (ID: {user_id})")

        # SECURITY: Extract client IP using secure service
        # This validates trusted proxies and prevents IP spoofing
        client_ip = extract_client_ip(request)

        # Extract other metadata fields safely
        user_agent = (
            request_data.metadata.user_agent if request_data.metadata else None
        )
        fingerprint = (
            request_data.metadata.fingerprint if request_data.metadata else None
        )
        user_timezone = (
            request_data.metadata.timezone if request_data.metadata else None
        )

        logger.debug(
            f"Request metadata: ip={client_ip}, "
            f"user_agent={user_agent[:50] if user_agent else None}..., "
            f"timezone={user_timezone}"
        )

        # SECURITY (CWE-79 fix): Sanitize user input before processing
        sanitized_input = sanitize_user_input(request_data.input, max_length=10000)

        if not sanitized_input:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "invalid_input",
                    "message": "Please provide a valid question.",
                },
            )

        # Process query and measure response time
        start_time = time.time()

        response_text, tokens_used, warning, error_msg = (
            await demo_agent.process_query(
                user_input=sanitized_input,
                user_key=user_key,
                language=request_data.language or "es",
                ip_address=client_ip,
                user_agent=user_agent,
                client_fingerprint=fingerprint,
                user_timezone=user_timezone,
            )
        )

        # Calculate response time in milliseconds
        response_time_ms = int((time.time() - start_time) * 1000)

        # If query was blocked, return error response
        if error_msg:
            status_code = 429 if "quota" in error_msg else 403

            # SECURITY (Phase 4): Set rate limit info for error responses
            # This ensures rate limit headers are added even for blocked requests
            try:
                user_status = await demo_agent.get_user_status(user_key)
                request.state.rate_limit_remaining = user_status.get(
                    "tokens_remaining", 0
                )
                request.state.rate_limit_used = user_status.get("tokens_used", 0)
                request.state.rate_limit_reset = user_status.get("next_reset")
            except Exception as e:
                logger.warning(f"Failed to get rate limit info for error response: {e}")

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

        # SECURITY (CWE-79 fix): Sanitize AI response to prevent XSS
        # While Gemini shouldn't generate malicious content, defense-in-depth
        # requires sanitizing all user-facing output
        sanitized_response = sanitize_html(response_text)

        # Get user status for rate limit headers
        user_status = await demo_agent.get_user_status(user_key)
        tokens_remaining_val = user_status.get("tokens_remaining", 0)
        tokens_used_val = user_status.get("tokens_used", 0)
        next_reset = user_status.get("next_reset")

        # SECURITY (Phase 4): Set rate limit info in request state
        # The RateLimitHeadersMiddleware will read these values and add headers
        request.state.rate_limit_remaining = tokens_remaining_val
        request.state.rate_limit_used = tokens_used_val
        request.state.rate_limit_reset = next_reset

        # ================================================================
        # CONVERSATION HISTORY STORAGE
        # ================================================================
        # Store user message and AI response in conversation_messages table
        # for chat history persistence and reload on page refresh
        try:
            # Step 1: Upsert conversation session
            # Create new session or update last_activity_at if exists
            session_upsert_query = """
                INSERT INTO :SCHEMA_NAME.conversation_sessions
                    (id, customer_email, session_id, last_activity_at, metadata, created_at, updated_at)
                VALUES
                    (gen_random_uuid(), %s, %s, NOW(), %s, NOW(), NOW())
                ON CONFLICT (session_id)
                DO UPDATE SET
                    last_activity_at = NOW(),
                    updated_at = NOW(),
                    customer_email = COALESCE(EXCLUDED.customer_email, conversation_sessions.customer_email),
                    metadata = COALESCE(EXCLUDED.metadata, conversation_sessions.metadata)
                RETURNING id
            """
            session_metadata = {
                "language": request_data.language or "es",
                "user_id": user_id,
            }
            session_result = await user_service.db.execute_one(
                session_upsert_query,
                (user_email, session_id, json.dumps(session_metadata)),
            )

            if not session_result:
                logger.warning(f"Failed to upsert conversation session: {session_id}")
            else:
                session_uuid = session_result["id"]
                logger.debug(
                    f"Session upserted: {session_uuid} for session_id: {session_id}"
                )

                # Step 2: Insert user message (with user_id for cross-device sync)
                user_msg_query = """
                    INSERT INTO :SCHEMA_NAME.conversation_messages
                        (session_id, user_id, role, message_text, token_count, created_at)
                    VALUES
                        (%s, %s, 'user', %s, 0, NOW())
                """
                await user_service.db.execute(
                    user_msg_query, (session_uuid, user_id, sanitized_input)
                )
                logger.debug(
                    f"User message stored for user_id: {user_id}, session: {session_id}"
                )

                # Step 3: Insert AI response (with user_id for cross-device sync and performance metrics)
                ai_msg_query = """
                    INSERT INTO :SCHEMA_NAME.conversation_messages
                        (session_id, user_id, role, agent_name, message_text, token_count, response_time_ms, created_at)
                    VALUES
                        (%s, %s, 'model', %s, %s, %s, %s, NOW())
                """
                await user_service.db.execute(
                    ai_msg_query,
                    (
                        session_uuid,
                        user_id,
                        "demo",
                        sanitized_response,
                        tokens_used,
                        response_time_ms,
                    ),
                )
                logger.debug(
                    f"AI response stored for user_id: {user_id}, session: {session_id}, "
                    f"agent: demo, tokens: {tokens_used}, response_time: {response_time_ms}ms"
                )

        except Exception as history_error:
            # IMPORTANT: Do NOT fail the request if history storage fails
            # This is a non-critical feature - log and continue
            logger.error(
                f"Failed to store conversation history (non-critical): {history_error}",
                exc_info=True,
            )
            # Continue with successful response anyway

        # Return successful response
        return DemoResponse(
            success=True,
            response=sanitized_response,
            tokens_used=tokens_used,
            tokens_remaining=tokens_remaining_val,
            warning=warning,
            session_id=session_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        # SECURITY (CWE-209 fix): Sanitize error messages to prevent information disclosure
        logger.exception(f"Error in demo_query: {e}")

        # Don't expose internal error details to users
        safe_message = sanitize_error_message(e, include_details=False)

        raise HTTPException(status_code=500, detail=safe_message)


@router.get("/status")
async def demo_status(request: Request):
    """Get authenticated user's current quota status.

    Requires Clerk authentication. Extracts user_id from JWT token.
    Returns quota information for the authenticated user across ALL devices.

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
      "next_reset": "2025-11-01T00:00:00Z",
      "daily_limit": 5000,
      "warning": {
        "is_warning": false,
        "message": null,
        "percentage_used": 25
      }
    }
    ```

    Note: When percentage_used >= DEMO_WARNING_THRESHOLD (default 85%),
    warning.is_warning will be true with a generic English message.
    Frontend should use is_warning flag to display i18n translations.

    Args:
        request: FastAPI request object.

    Returns:
        dict: Quota status information.

    Raises:
        HTTPException: 401 if not authenticated, 500 on server error.
    """
    try:
        demo_agent, _ = get_services(request)
        logger.info("=== demo_status START ===")

        # AUTHENTICATION: Extract user_id from Clerk JWT (same pattern as /v1/demo)
        logger.info("demo_status: Calling get_current_user")
        authenticated_user = get_current_user(request)
        logger.info(f"demo_status: authenticated_user = {authenticated_user}")

        if not authenticated_user:
            logger.warning("demo_status: No authenticated user found")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "authentication_required",
                    "message": "Please log in to view quota status.",
                },
            )

        user_id = authenticated_user.get("db_user_id")
        logger.info(f"demo_status: Extracted user_id = {user_id}")

        if not user_id:
            logger.error(
                f"demo_status: db_user_id not found in authenticated_user: {authenticated_user}"
            )
            raise HTTPException(
                status_code=400, detail="User ID not found in authentication token"
            )

        # USER-BASED QUOTA: Use user_id as the key (same across all devices)
        # This ensures quota is shared across all user's sessions/devices
        user_key = str(user_id)

        logger.info(f"Quota status requested by user: {user_id}")

        # Get quota status
        status = await demo_agent.get_user_status(user_key)
        logger.info(f"demo_status: Returning status = {status}")
        return status

    except HTTPException:
        logger.error("demo_status: HTTPException raised")
        raise
    except Exception as e:
        logger.exception(f"Error in demo_status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history")
async def get_demo_history(
    limit: int = Query(100, description="Maximum number of messages to return"),
    request: Request = None,
):
    """Retrieve user's complete conversation history (all devices, all sessions).

    Requires Clerk authentication. Returns all messages for the authenticated user.
    Messages are returned in chronological order (oldest first).

    Query Parameters:
    - `limit` (optional): Max messages to return (default: 100, max: 500)

    Response (Success):
    ```json
    {
      "success": true,
      "messages": [
        {
          "id": 1,
          "role": "user",
          "message_text": "Hello, how can I book an appointment?",
          "token_count": 0,
          "created_at": "2025-11-08T10:30:00Z"
        },
        {
          "id": 2,
          "role": "model",
          "message_text": "I'd be happy to help you book an appointment...",
          "token_count": 45,
          "created_at": "2025-11-08T10:30:02Z"
        }
      ],
      "total_messages": 2,
      "session_id": "abc-123-def"
    }
    ```

    Response (Empty History):
    ```json
    {
      "success": true,
      "messages": [],
      "total_messages": 0,
      "session_id": "abc-123-def"
    }
    ```

    Response (Unauthorized - 401):
    ```json
    {
      "success": false,
      "error": "authentication_required",
      "message": "Please log in to access chat history"
    }
    ```

    Response (Forbidden - 403):
    ```json
    {
      "success": false,
      "error": "access_denied",
      "message": "You do not have access to this chat session"
    }
    ```

    Args:
        limit: Maximum number of messages to return.
        request: FastAPI request object.

    Returns:
        dict: Chat history with messages.

    Raises:
        HTTPException: 401 if not authenticated, 500 on server error.
    """
    try:
        _, user_service = get_services(request)

        # SECURITY: Require Clerk authentication
        authenticated_user = get_current_user(request)

        if not authenticated_user or not authenticated_user.get("db_user_id"):
            logger.error("Unauthorized chat history access attempt")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "authentication_required",
                    "message": "Please log in to access chat history.",
                },
            )

        user_id = authenticated_user["db_user_id"]
        logger.info(f"Chat history requested by user: {user_id}")

        # SECURITY: Limit max messages to prevent abuse
        limit = min(max(1, limit), 500)  # Clamp between 1 and 500

        # USER-BASED QUERY: Fetch all user's messages across ALL devices/sessions
        # This is simpler, faster (no JOIN), and more secure than session-based approach
        messages_query = """
            SELECT
                cm.id,
                cm.role,
                cm.message_text,
                cm.token_count,
                cm.created_at
            FROM :SCHEMA_NAME.conversation_messages cm
            WHERE cm.user_id = %s
            ORDER BY cm.created_at ASC
            LIMIT %s
        """
        messages = await user_service.db.execute_all(messages_query, (user_id, limit))

        # Convert datetime objects to ISO strings for JSON serialization
        for msg in messages:
            if msg.get("created_at"):
                msg["created_at"] = msg["created_at"].isoformat()

        logger.info(
            f"Chat history retrieved: {len(messages)} messages for user {user_id} (cross-device sync)"
        )

        return {
            "success": True,
            "messages": messages,
            "total_messages": len(messages),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving chat history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve chat history",
        )


@router.post("/verify-captcha", tags=["Security"])
async def verify_captcha(
    token: str = Query(..., description="reCAPTCHA v3 response token"),
    user_id: str | None = Query(None, description="Authenticated user ID"),
    session_id: str | None = Query(None, description="Anonymous session ID"),
    remote_ip: str | None = Query(None, description="Client IP address"),
    request: Request = None,
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

    Args:
        token: reCAPTCHA response token.
        user_id: Authenticated user ID (optional).
        session_id: Anonymous session ID (optional).
        remote_ip: Client IP address (optional).
        request: FastAPI request object.

    Returns:
        dict: CAPTCHA verification result.

    Raises:
        HTTPException: 500 on server error.
    """
    try:
        demo_agent, _ = get_services(request)

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
