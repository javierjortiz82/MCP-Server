"""User Management MCP Tool Handlers.

Registers user management tools for BookingAgent authentication flow.
Exposes functions for email validation, OTP verification, user registration,
and profile management.

Tools:
    - check_user_exists: Verify if user email exists in database
    - create_user: Register new user account
    - request_otp: Send OTP code to user email
    - verify_otp: Validate OTP code submission
    - update_user: Update user profile information

Integration:
    These tools enable BookingAgent to implement structured authentication flow:
    1. Email validation and user lookup
    2. OTP-based email ownership verification
    3. User registration for new accounts
    4. Welcome back flow for existing users
    5. Profile updates (language preference, name)

Author: Lab01-MCP Team
Created: 2025-11-12
Version: 1.0.0
"""

import logging
from typing import Optional

from tools.user_management import (
    check_user_exists,
    create_user,
    request_otp,
    verify_otp,
    update_user,
    check_session_auth,
    clear_session_auth,
    save_session_auth,
    update_session_activity,
)

logger = logging.getLogger(__name__)


def register_user_tools(mcp):
    """Register all user management tools with MCP server.

    Args:
        mcp: FastMCP server instance for tool registration.

    Registers:
        9 tools for complete user authentication and management workflow.
    """

    @mcp.tool(
        name="check_user_exists",
        description=(
            "Check if a user exists in the database by email address. "
            "Returns user status including verification state, active status, "
            "preferred language, and full name. Use this as the FIRST STEP "
            "in authentication flow to determine if user needs registration "
            "or can proceed directly to OTP verification."
        )
    )
    async def tool_check_user_exists(email: str) -> dict:
        """Check if user exists in database.

        Args:
            email: User email address to lookup (case-insensitive).

        Returns:
            dict: User existence and status information with keys:
                - exists (bool): True if user found in database
                - user_id (int|None): User ID if exists
                - email (str): Normalized email address
                - full_name (str|None): User full name if exists
                - is_active (bool): Account activation status
                - is_verified (bool): Email verification status
                - language (str|None): Preferred language code (es|en)
                - error (str): Error message if operation failed

        Example:
            >>> result = await tool_check_user_exists("user@example.com")
            >>> if result["exists"]:
            ...     print(f"Welcome back, {result['full_name']}!")
            ... else:
            ...     print("New user - proceed to registration")
        """
        logger.info(f"[MCP Tool] check_user_exists called for email={email}")
        result = await check_user_exists(email)
        logger.info(
            f"[MCP Tool] check_user_exists result: exists={result.get('exists')}, "
            f"verified={result.get('is_verified')}"
        )
        return result

    @mcp.tool(
        name="create_user",
        description=(
            "Create a new user account in the database. Use this ONLY AFTER "
            "check_user_exists confirms user does not exist AND after OTP "
            "verification succeeds (to confirm email ownership). Requires "
            "email, full_name, and optional phone number. Sets user as active "
            "and verified by default for booking flow."
        )
    )
    async def tool_create_user(
        email: str,
        full_name: str,
        phone: Optional[str] = None,
        language: str = "es"
    ) -> dict:
        """Create new user account.

        Args:
            email: User email address (will be normalized).
            full_name: User's full name (required for booking).
            phone: Optional phone number for contact.
            language: Preferred language code (default: "es"). Options: es|en.

        Returns:
            dict: Creation result with keys:
                - success (bool): True if user created successfully
                - user_id (int|None): Created user ID (use for future operations)
                - email (str): Normalized email address
                - message (str): Success or error message

        Example:
            >>> result = await tool_create_user(
            ...     email="newuser@example.com",
            ...     full_name="John Doe",
            ...     phone="+1234567890",
            ...     language="en"
            ... )
            >>> if result["success"]:
            ...     print(f"Account created with ID: {result['user_id']}")
        """
        logger.info(
            f"[MCP Tool] create_user called for email={email}, "
            f"full_name={full_name}, language={language}"
        )
        result = await create_user(
            email=email,
            full_name=full_name,
            phone=phone,
            language=language
        )
        logger.info(
            f"[MCP Tool] create_user result: success={result.get('success')}, "
            f"user_id={result.get('user_id')}"
        )
        return result

    @mcp.tool(
        name="request_otp",
        description=(
            "Generate and send a 6-digit OTP code to user's email address. "
            "Use this AFTER collecting email (either for new registration or "
            "existing user login). OTP expires in 10 minutes. Rate limited to "
            "1 request per minute per email. User will receive email with code "
            "to verify ownership. Always inform user to check their email inbox."
        )
    )
    async def tool_request_otp(
        email: str,
        purpose: str = "booking_auth"
    ) -> dict:
        """Request OTP code for email verification.

        Args:
            email: User email address to send OTP to.
            purpose: OTP purpose identifier (default: "booking_auth").
                     Used to track OTP context in database.

        Returns:
            dict: OTP request result with keys:
                - success (bool): True if OTP sent successfully
                - message (str): Success message or error description
                - rate_limit_seconds (int): Seconds to wait if rate limited
                - expires_in_minutes (int): OTP validity duration (10 min)

        Rate Limiting:
            - Maximum 1 OTP per minute per email address
            - Returns rate_limit_seconds if too many requests

        Example:
            >>> result = await tool_request_otp("user@example.com")
            >>> if result["success"]:
            ...     print("OTP sent! Check your email inbox.")
            ... elif "rate_limit_seconds" in result:
            ...     print(f"Please wait {result['rate_limit_seconds']} seconds")
        """
        logger.info(
            f"[MCP Tool] request_otp called for email={email}, purpose={purpose}"
        )
        result = await request_otp(email=email, purpose=purpose)
        logger.info(
            f"[MCP Tool] request_otp result: success={result.get('success')}"
        )
        return result

    @mcp.tool(
        name="verify_otp",
        description=(
            "Verify the 6-digit OTP code submitted by user. Use this AFTER "
            "request_otp and user provides the code from their email. "
            "Max 3 attempts per OTP - returns attempts_remaining in response. "
            "Code must be exactly 6 digits. OTP expires in 10 minutes. "
            "Successful verification confirms email ownership - proceed to "
            "create_user (new users) or welcome menu (existing users)."
        )
    )
    async def tool_verify_otp(
        email: str,
        code: str,
        purpose: str = "booking_auth"
    ) -> dict:
        """Verify OTP code submission.

        Args:
            email: User email address used in request_otp.
            code: 6-digit OTP code from user's email.
            purpose: OTP purpose identifier (must match request_otp call).

        Returns:
            dict: Verification result with keys:
                - success (bool): True if code is valid and verified
                - verified (bool): Alias for success (backward compatibility)
                - message (str): Success or error description
                - attempts_remaining (int): Remaining verification attempts (max 3)
                - error_code (str): Error type if verification failed:
                    - "NOT_FOUND": No OTP exists for this email/purpose
                    - "EXPIRED": OTP expired (>10 minutes old)
                    - "INVALID_CODE": Code doesn't match (wrong digits)
                    - "MAX_ATTEMPTS": 3 failed attempts exhausted
                    - "INVALID_FORMAT": Code not exactly 6 digits

        Security:
            - Constant-time comparison prevents timing attacks
            - Max 3 attempts per OTP prevents brute force
            - Codes SHA-256 hashed in database

        Example:
            >>> result = await tool_verify_otp("user@example.com", "123456")
            >>> if result["success"]:
            ...     print("Email verified successfully!")
            ... elif result.get("error_code") == "INVALID_CODE":
            ...     remaining = result["attempts_remaining"]
            ...     print(f"Wrong code. {remaining} attempts remaining.")
        """
        logger.info(
            f"[MCP Tool] verify_otp called for email={email}, "
            f"code={'*' * len(code)}, purpose={purpose}"
        )
        result = await verify_otp(email=email, code=code, purpose=purpose)
        logger.info(
            f"[MCP Tool] verify_otp result: success={result.get('success')}, "
            f"attempts_remaining={result.get('attempts_remaining')}"
        )
        return result

    @mcp.tool(
        name="update_user",
        description=(
            "Update user profile information. Use this when user wants to "
            "change their name or language preference. Requires user email "
            "to identify account. Only updates provided fields (partial updates "
            "supported). Language must be 'es' or 'en'. Returns updated user data."
        )
    )
    async def tool_update_user(email: str, data: dict) -> dict:
        """Update user profile information.

        Args:
            email: User email address to identify account.
            data: Dictionary with fields to update. Supported keys:
                - full_name (str): Update user's full name
                - language (str): Update preferred language (es|en)

        Returns:
            dict: Update result with keys:
                - success (bool): True if update successful
                - user_id (int): Updated user ID
                - email (str): User email address
                - updated_fields (list): Fields that were updated
                - message (str): Success or error message

        Example:
            >>> result = await tool_update_user(
            ...     email="user@example.com",
            ...     data={"language": "en", "full_name": "Jane Doe"}
            ... )
            >>> if result["success"]:
            ...     print(f"Updated: {result['updated_fields']}")
        """
        logger.info(
            f"[MCP Tool] update_user called for email={email}, "
            f"fields={list(data.keys())}"
        )
        result = await update_user(email=email, data=data)
        logger.info(
            f"[MCP Tool] update_user result: success={result.get('success')}, "
            f"updated_fields={result.get('updated_fields')}"
        )
        return result

    @mcp.tool(
        name="check_session_auth",
        description=(
            "Check if current user session is authenticated and valid. "
            "Verifies authentication status by querying memory blocks for this session. "
            "Returns authentication details including user info, session expiration status, "
            "and whether re-authentication is required. Use this at the START of every "
            "booking conversation to determine if user needs to authenticate. "
            "Session timeout: 30 minutes of inactivity."
        )
    )
    async def tool_check_session_auth(session_id: str) -> dict:
        """Check session authentication status.

        Args:
            session_id: UUID of the current conversation session.
                        This is provided by the agent framework in the context.

        Returns:
            dict: Authentication status with keys:
                - is_authenticated (bool): True if session has valid auth
                - user_id (int|None): Authenticated user ID
                - email (str|None): User email address
                - full_name (str|None): User full name
                - language (str|None): User preferred language (es|en)
                - last_activity (str|None): Last activity timestamp (ISO format)
                - session_expired (bool): True if inactive > 30 minutes
                - requires_reauth (bool): True if expired or not authenticated

        Example:
            >>> result = await tool_check_session_auth("f95db5a9-770b-4238-9790-0398754d1c6b")
            >>> if result["requires_reauth"]:
            ...     # Start authentication flow
            ...     print("Please provide your email to authenticate")
            ... else:
            ...     # Session valid, show welcome menu
            ...     print(f"Welcome back, {result['full_name']}!")
        """
        logger.info(f"[MCP Tool] check_session_auth called for session_id={session_id}")
        result = await check_session_auth(session_id)
        logger.info(
            f"[MCP Tool] check_session_auth result: "
            f"authenticated={result.get('is_authenticated')}, "
            f"requires_reauth={result.get('requires_reauth')}, "
            f"expired={result.get('session_expired')}"
        )
        return result

    @mcp.tool(
        name="clear_session_auth",
        description=(
            "Clear authentication data from current session (logout). "
            "Removes all authentication-related memory blocks for this session. "
            "Use this when session expires, user explicitly logs out, or when "
            "security requires re-authentication. Does NOT delete conversation history, "
            "only authentication state. User will need to re-authenticate with OTP "
            "on next interaction."
        )
    )
    async def tool_clear_session_auth(session_id: str) -> dict:
        """Clear session authentication (logout).

        Args:
            session_id: UUID of the current conversation session to clear.

        Returns:
            dict: Deletion result with keys:
                - success (bool): True if auth data cleared successfully
                - session_id (str): Session ID that was cleared
                - blocks_cleared (int): Number of memory blocks deleted
                - message (str): Success or error message

        Example:
            >>> result = await tool_clear_session_auth("f95db5a9-770b-4238-9790-0398754d1c6b")
            >>> if result["success"]:
            ...     print(f"Session cleared. {result['blocks_cleared']} auth blocks removed.")
            ...     # Start authentication flow from beginning
        """
        logger.info(f"[MCP Tool] clear_session_auth called for session_id={session_id}")
        result = await clear_session_auth(session_id)
        logger.info(
            f"[MCP Tool] clear_session_auth result: "
            f"success={result.get('success')}, "
            f"blocks_cleared={result.get('blocks_cleared')}"
        )
        return result

    @mcp.tool(
        name="save_session_auth",
        description=(
            "Save authentication data to session memory blocks after successful OTP verification. "
            "Creates memory blocks for is_authenticated, user_id, email, full_name, language, "
            "and last_activity_timestamp. Call this IMMEDIATELY after verify_otp returns success=true. "
            "This makes the session authenticated and allows access to booking operations."
        )
    )
    async def tool_save_session_auth(
        session_id: str,
        user_id: int,
        email: str,
        full_name: str,
        language: str = "es"
    ) -> dict:
        """Save authentication to session.

        Args:
            session_id: UUID of the current conversation session
            user_id: User ID from check_user_exists or create_user
            email: User email address
            full_name: User full name
            language: User preferred language (es|en)

        Returns:
            dict: Save result with keys:
                - success (bool): True if auth data saved
                - session_id (str): Session ID
                - blocks_created (int): Number of memory blocks created (6)
                - message (str): Success or error message

        Example:
            >>> # After successful OTP verification
            >>> otp_result = await tool_verify_otp("user@example.com", "123456")
            >>> if otp_result["success"]:
            ...     user_info = await tool_check_user_exists("user@example.com")
            ...     auth_result = await tool_save_session_auth(
            ...         session_id="f95db5a9-770b-4238-9790-0398754d1c6b",
            ...         user_id=user_info["user_id"],
            ...         email=user_info["email"],
            ...         full_name=user_info["full_name"],
            ...         language="es"
            ...     )
        """
        logger.info(
            f"[MCP Tool] save_session_auth called for session={session_id}, "
            f"user={email}"
        )
        result = await save_session_auth(
            session_id=session_id,
            user_id=user_id,
            email=email,
            full_name=full_name,
            language=language
        )
        logger.info(
            f"[MCP Tool] save_session_auth result: "
            f"success={result.get('success')}, "
            f"blocks_created={result.get('blocks_created')}"
        )
        return result

    @mcp.tool(
        name="update_session_activity",
        description=(
            "Update last_activity_timestamp for authenticated session. "
            "Call this on EVERY user interaction to prevent session timeout (30 minutes). "
            "Updates the activity timestamp to current time, resetting the inactivity counter."
        )
    )
    async def tool_update_session_activity(session_id: str) -> dict:
        """Update session activity timestamp.

        Args:
            session_id: UUID of the current conversation session

        Returns:
            dict: Update result with keys:
                - success (bool): True if timestamp updated
                - session_id (str): Session ID
                - last_activity (str): Updated ISO timestamp
                - message (str): Success or error message

        Example:
            >>> # On every user interaction
            >>> result = await tool_update_session_activity("f95db5a9-...")
            >>> if result["success"]:
            ...     print(f"Activity updated: {result['last_activity']}")
        """
        logger.debug(f"[MCP Tool] update_session_activity called for session={session_id}")
        result = await update_session_activity(session_id=session_id)
        logger.debug(
            f"[MCP Tool] update_session_activity result: "
            f"success={result.get('success')}"
        )
        return result

    logger.info("[User Handlers] Registered 9 user management tools with MCP")
