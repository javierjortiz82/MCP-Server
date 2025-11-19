"""Booking Agent - Specialized Agent for Reservation Queries.

This module provides the BookingAgent class that handles all booking-related
queries including creating, canceling, rescheduling appointments, and checking
availability. Uses Gemini 2.5 Flash with booking MCP tools.

The agent specializes in:
- Creating new appointments/reservations
- Canceling existing bookings
- Rescheduling appointments
- Checking available time slots
- Listing customer bookings
- Providing booking confirmations

Architecture:
    BookingAgent inherits from BaseAgent, eliminating ~280 lines of duplicated code.
    Only agent-specific functionality is implemented here:
    - System prompt via PromptManager (with A/B testing support)
    - MCP tools configuration for function calling
    - Booking-specific business logic

References:
    - https://ai.google.dev/gemini-api/docs/function-calling
    - https://googleapis.github.io/python-genai/
    - https://github.com/anthropics/anthropic-quickstarts/tree/main/mcp

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 2.0.0 (Refactored to inherit from BaseAgent)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from gemini_agent.base_agent import BaseAgent
from gemini_agent.config.booking_agent_settings import booking_agent_settings
from gemini_agent.utils.gemini_response_handler import ResponseStatus
from google.genai import types
from multi_agent.prompt_manager import PromptManager

# Import centralized configuration for session/OTP timeouts
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "mcp_server"))
from config.otp_session_config import OTPSessionConfig

if TYPE_CHECKING:
    from core.function_call_handler import FunctionCallHandler  # type: ignore[import-not-found]
    from core.mcp_connector import MCPConnector  # type: ignore[import-not-found]

# Gemini 2.5 Function Calling Optimization (Scope Limiting)
# Hardcoded allowed tools for booking operations
# CRITICAL: Must include ALL tools that BookingAgent may need for OTP/auth flow
# These are: 8 booking operations + 9 auth/user management = 17 total
BOOKING_TOOLS_ALLOWED = {
    # Booking operations (8 tools)
    "create_booking",
    "cancel_booking",
    "reschedule_booking",
    "get_available_slots",
    "get_booking_by_id",
    "list_customer_bookings",
    "get_services",
    "get_business_hours",
    # Authentication & user management (9 tools)
    # CRITICAL for OTP flow: request_otp, verify_otp, check_session_auth, save_session_auth
    "check_user_exists",
    "create_user",
    "request_otp",
    "verify_otp",
    "update_user",
    "check_session_auth",
    "save_session_auth",
    "clear_session_auth",
    "update_session_activity",
}

# Import language context for MCP tool execution
try:
    from utils.language_context import set_current_language  # type: ignore[import-not-found]

    LANGUAGE_CONTEXT_AVAILABLE = True
except ImportError:
    LANGUAGE_CONTEXT_AVAILABLE = False
    set_current_language = None  # type: ignore[assignment]

# Import client_mcp utilities for function calling
client_mcp_path = Path(__file__).parent.parent.parent.parent / "client_mcp"
if str(client_mcp_path) not in sys.path:
    sys.path.insert(0, str(client_mcp_path))

try:
    from core.function_call_handler import FunctionCallHandler  # type: ignore[import-not-found]
    from core.mcp_connector import MCPConnector  # type: ignore[import-not-found]

    FUNCTION_CALLING_AVAILABLE = True
except ImportError:
    FUNCTION_CALLING_AVAILABLE = False
    FunctionCallHandler = None  # type: ignore[misc,assignment]
    MCPConnector = None  # type: ignore[misc,assignment]


# ═══════════════════════════════════════════════════════════════════════════════
# BOOKING RESPONSE SCHEMA (Gemini 2.5 Structured Output Feature)
# ═══════════════════════════════════════════════════════════════════════════════
# Defines JSON schema for structured responses (Google Gemini Best Practice 2025)
# Ensures: 100% valid JSON parsing, automatic intent detection, strict compliance
#
# Feature: responseSchema (introduced July 2025)
# Benefit: Eliminates parsing errors, enables reliable downstream processing
# ═══════════════════════════════════════════════════════════════════════════════

# Schema for booking response - using dict-based approach for compatibility
# with google.genai types.GenerateContentConfig (response_schema expects dict)
BOOKING_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": [
                "create_booking",
                "cancel_booking",
                "reschedule_booking",
                "list_bookings",
                "service_info",
                "business_hours",
                "availability_check",
                "disambiguation",
                "out_of_scope",
                "error",
            ],
            "description": "Automatically detected user intent",
        },
        "confidence": {
            "type": "number",
            "description": "Confidence score 0.0-1.0 for detected intent",
        },
        "missing_data": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of required data still needed from user",
        },
        "suggested_actions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of next steps or options for user",
        },
        "response_text": {
            "type": "string",
            "description": "Main response text to user (conversational format)",
        },
        "data_extracted": {
            "type": "object",
            "properties": {
                "service_type": {"type": "string"},
                "booking_date": {"type": "string"},
                "booking_time": {"type": "string"},
                "customer_email": {"type": "string"},
                "customer_name": {"type": "string"},
                "booking_id": {"type": "string"},
            },
            "description": "Extracted booking-related data from conversation",
        },
    },
    "required": ["intent", "confidence", "response_text"],
}


class BookingAgent(BaseAgent):
    """Specialized agent for handling booking/reservation queries.

    Inherits all common functionality from BaseAgent:
    - Gemini client initialization and lifecycle
    - Conversation history management
    - Base generation configuration
    - Response generation pipeline

    BookingAgent-specific additions:
    - Booking system prompt via PromptManager (with A/B testing)
    - MCP tools for booking operations
    - Function calling loop for tool execution
    - Booking-specific helper methods

    Example:
        >>> agent = BookingAgent(mcp_tools=booking_tools)
        >>> await agent.initialize()
        >>> response = await agent.generate_response(
        ...     "Quiero reservar una cita para mañana",
        ...     customer_email="maria@example.com"
        ... )
    """

    # PromptManager instance (shared across all BookingAgent instances)
    _prompt_manager: PromptManager | None = None

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        mcp_tools: list[types.FunctionDeclaration] | None = None,
        mcp_client: MCPConnector | None = None,  # type: ignore[name-defined]
        **generation_params: Any,
    ) -> None:
        """Initialize BookingAgent with function calling support.

        Args:
            api_key: Google API key for Gemini.
            model_name: Model to use for generation.
            mcp_tools: List of MCP tools for booking operations.
            mcp_client: MCP connector for tool execution.
            **generation_params: Override generation parameters.
        """
        super().__init__(api_key, model_name, mcp_tools, **generation_params)

        # Function calling support (max iterations configurable via booking_agent_settings)
        self.mcp_client = mcp_client
        self.function_call_handler = None
        if FUNCTION_CALLING_AVAILABLE and FunctionCallHandler is not None:  # type: ignore[name-defined]
            self.function_call_handler = FunctionCallHandler(  # type: ignore[name-defined]
                max_iterations=booking_agent_settings.BOOKING_MAX_FUNCTION_CALL_ITERATIONS
            )

        # NOTE: response_handler is now inherited from BaseAgent
        # BaseAgent.__init__() creates it with default config
        # BookingAgent inherits retry logic + validation automatically

    @property
    def agent_name(self) -> str:
        """Return agent name for logging.

        Required by BaseAgent abstract property.
        CRITICAL: Must return "booking" (without "_agent" suffix) to match memory scope
        used in save_memory_block() and database constraints.
        """
        return "booking"

    async def initialize(self) -> None:
        """Initialize BookingAgent and log available MCP tools.

        Extends BaseAgent.initialize() to log available tools for debugging.
        """
        # Initialize BaseAgent (Gemini client, config, etc.)
        await super().initialize()

        # Log MCP tools if available
        if self.mcp_tools:
            self._log_available_tools()

    def _log_available_tools(self) -> None:
        """Log available MCP tools (FunctionDeclaration format)."""
        if not self.mcp_tools:
            return

        self.logger.info("📋 Available MCP tools (FunctionDeclaration):")
        for i, func_decl in enumerate(self.mcp_tools, 1):
            tool_name = func_decl.name
            tool_description = func_decl.description or "No description"
            desc_first_line = tool_description.split("\n")[0]
            self.logger.info(f"   {i}. {tool_name}: {desc_first_line}")

    async def _check_and_enforce_authentication(
        self,
        query: str,
        **kwargs: Any
    ) -> str | None:
        """Check if user is authenticated and enforce authentication if not.

        This is a HARD BLOCK at the code level that prevents ANY booking operations
        until the user has successfully authenticated with OTP.

        Authentication Flow:
        1. Check session authentication status via MCP tool
        2. If not authenticated or session expired:
           - Check if user is IN THE MIDDLE of authentication flow (responding to auth prompt)
           - If yes, allow Gemini to process (handle email/OTP)
           - If no, return authentication prompt
        3. If authenticated, return None (allow request to proceed)

        Args:
            query: User's query/message
            **kwargs: Additional context (language, etc.)

        Returns:
            str | None:
                - Authentication prompt if user needs to authenticate
                - None if user is authenticated OR in authentication flow (proceed to Gemini)

        Security:
            - Blocks ALL requests until authentication succeeds
            - Cannot be bypassed by Gemini or user input
            - Session timeout: 30 minutes of inactivity
        """
        try:
            # Get session_id from current session
            if not self.session_id:
                self.logger.error("No session_id available - cannot check authentication")
                return self._get_auth_error_message(kwargs.get("language", "es"))

            # Call check_session_auth MCP tool
            self.logger.info(f"🔐 Checking authentication status for session: {self.session_id}")

            # Execute MCP tool via client
            auth_status = await self.mcp_client.call_tool(
                "check_session_auth",
                {"session_id": str(self.session_id)}
            )

            if not auth_status:
                self.logger.error("Failed to check authentication status")
                return self._get_auth_error_message(kwargs.get("language", "es"))

            self.logger.info(f"🔍 Auth status: {auth_status}")

            # Check if re-authentication is required
            requires_reauth = auth_status.get("requires_reauth", True)
            is_authenticated = auth_status.get("is_authenticated", False)
            session_expired = auth_status.get("session_expired", False)

            if requires_reauth:
                # User is NOT authenticated or session expired
                self.logger.warning(
                    f"🔒 Authentication required: "
                    f"authenticated={is_authenticated}, "
                    f"expired={session_expired}"
                )

                # ⚠️ CRITICAL: If session expired, ALWAYS clear the auth_flow_pending flag
                # The flag from the PREVIOUS session (which expired) is STALE and must not be reused.
                # Even if auth_flow_pending=true, it's from the old session and no longer valid.
                if session_expired:
                    self.logger.warning(
                        "⚠️ Session has expired - the auth_flow_pending flag is stale, clearing it"
                    )
                    self._set_auth_flow_pending(False)

                # Now check if user is IN THE MIDDLE of authentication flow
                # This uses the FRESH flag state after cleanup
                is_in_auth_flow = self._is_user_in_auth_flow()
                self.logger.info(f"🔍 Auth flow check: is_in_auth_flow={is_in_auth_flow}")

                if is_in_auth_flow:
                    self.logger.info(
                        "🔓 User is responding to authentication prompt - "
                        "allowing Gemini to process (email/OTP collection)"
                    )
                    return None  # Let Gemini handle authentication flow

                # User is NOT in auth flow - set flag and show authentication prompt
                # Set auth_flow_pending flag in memory blocks so next request knows user is in auth flow
                self._set_auth_flow_pending(True)

                return self._get_authentication_prompt(
                    session_expired=session_expired,
                    language=kwargs.get("language", "es")
                )

            # User is authenticated - clear auth_flow_pending flag and allow request to proceed
            self.logger.info("✅ User authenticated - session valid")
            self._set_auth_flow_pending(False)  # Clear flag
            return None

        except Exception as e:
            self.logger.exception(f"Error checking authentication: {e}")
            # On error, be conservative and require authentication
            return self._get_auth_error_message(kwargs.get("language", "es"))

    def _is_user_in_auth_flow(self) -> bool:
        """Check if user is currently in the middle of authentication flow.

        CRITICAL: The hard block returns a text response when auth is required.
        That response goes back to the user but is NOT added to history yet.
        So we can't rely on history to detect if we're in auth flow.

        Instead, we check if the RESPONSE we're about to return is an auth prompt.
        But that creates a chicken-and-egg problem.

        SOLUTION: Always allow the FIRST message after a hard block returns auth prompt.
        We detect this by checking if this is a NEW conversation (no history).

        Returns:
            bool: True if we should allow Gemini to process (in auth flow), False otherwise.
        """
        try:
            # CRITICAL INSIGHT: The hard block executes BEFORE history is updated.
            # When hard block returns "¿Cuál es tu correo?" that message is NOT in history yet.
            # So when user replies with email, history is EMPTY or has old messages only.

            # Check if we have recent conversation history
            if not hasattr(self, 'history') or not self.history:
                self.logger.info("🔍 No history - this could be first message OR response to auth prompt")
                # Can't determine reliably - check database for recent auth prompt
                return self._check_recent_auth_prompt_in_db()

            # Look at the LAST message in history
            # If it's from the model and contains auth keywords, user is responding to it
            self.logger.info(f"🔍 Checking last message in history ({len(self.history)} total messages)...")

            if len(self.history) > 0:
                last_msg = self.history[-1]

                # Check if last message is from the model (assistant)
                if hasattr(last_msg, 'role') and last_msg.role == 'model':
                    if hasattr(last_msg, 'parts') and last_msg.parts:
                        text = ''.join(part.text for part in msg.parts if hasattr(part, 'text'))

                        # Check for auth keywords
                        auth_keywords = [
                            "correo electrónico", "email", "email address",
                            "sesión ha expirado", "session has expired",
                            "verificar tu identidad", "verify your identity",
                            "código OTP", "OTP code", "verification code",
                            "¿Cuál es tu", "What's your", "What is your"
                        ]

                        if any(keyword.lower() in text.lower() for keyword in auth_keywords):
                            self.logger.info(f"✅ Last message is auth prompt: {text[:80]}...")
                            return True

                self.logger.info("Last message in history is not an auth prompt")

            # Fallback: check DB for recent auth prompt sent
            return self._check_recent_auth_prompt_in_db()

        except Exception as e:
            self.logger.warning(f"Error checking auth flow status: {e}")
            return False

    def _check_recent_auth_prompt_in_db(self) -> bool:
        """Check if user is responding to a recent authentication prompt.

        IMPROVED LOGIC: Don't assume user is in auth flow just because history is empty.
        Instead, check the auth_flow_pending memory block:
        - If auth_flow_pending=true → User IS responding to auth prompt
        - If auth_flow_pending=false/missing → User is NOT in auth flow (show new prompt)

        This fixes the issue where users were automatically allowed without seeing the prompt.

        Returns:
            bool: True if user is responding to auth prompt, False if new auth needed.
        """
        try:
            # IMPROVED: Check auth_flow_pending memory block to determine actual state
            # This is more reliable than guessing based on history availability

            is_in_auth_flow = self._check_auth_flow_from_memory()

            if is_in_auth_flow:
                self.logger.info("✅ auth_flow_pending=true found - user is responding to auth prompt")
                self.logger.info("✅ Allowing request to proceed (will let Gemini handle email/OTP)")
                return True
            else:
                # auth_flow_pending is false or missing
                # User is NOT in auth flow - should show authentication prompt
                self.logger.info("❌ auth_flow_pending=false/missing - user needs authentication")
                self.logger.info("❌ User is NOT responding to auth prompt - will show new prompt")
                return False

        except Exception as e:
            self.logger.warning(f"Error checking auth flow from memory: {e}")
            # On error, be conservative and show auth prompt
            return False

    def _check_auth_flow_from_memory(self) -> bool:
        """Check if auth flow is pending by looking at memory blocks.

        Returns:
            bool: True if auth_flow_pending memory block exists, False otherwise.
        """
        try:
            # Check if memory is enabled
            if not self._memory_enabled or not hasattr(self, 'memory_manager'):
                self.logger.info("🔍 Memory not enabled - cannot check auth_flow_pending")
                return False

            # Debug: Log session_id and memory manager state
            self.logger.info(f"🔍 DEBUG: session_id={self.session_id}, memory_manager={self.memory_manager is not None}")

            # Get session memory blocks (use default scope to match save_memory_block)
            memory_blocks = self.get_memory_blocks()
            self.logger.info(f"🔍 Found {len(memory_blocks)} memory blocks (scope={self.agent_name})")
            if memory_blocks:
                self.logger.info(f"🔍 DEBUG: Memory blocks: {[(b.get('block_label'), b.get('block_value')) for b in memory_blocks]}")

            # Look for auth_flow_pending flag
            for block in memory_blocks:
                if block.get('block_label') == 'auth_flow_pending':
                    value = block.get('block_value')
                    self.logger.info(f"✅ Found auth_flow_pending in memory: {value}")
                    return value == 'true'

            self.logger.info("❌ No auth_flow_pending flag found in memory blocks")
            return False

        except Exception as e:
            self.logger.warning(f"Error checking auth flow from memory: {e}")
            return False

    def _set_auth_flow_pending(self, pending: bool) -> None:
        """Set or clear the auth_flow_pending flag in memory blocks.

        This flag indicates that the system is waiting for user to provide
        email or OTP as part of the authentication flow.

        Args:
            pending: True to set flag (waiting for auth), False to clear it.
        """
        try:
            # Check if memory is enabled
            if not self._memory_enabled or not self.memory_manager or not self.session_id:
                self.logger.warning("Memory not enabled - cannot set auth_flow_pending flag")
                return

            # Set or clear the flag using BaseAgent's save_memory_block method
            # CRITICAL: Specify agent_scope="booking" to match get_memory_blocks() default
            # Without this, save goes to "shared" but get reads from "booking"
            if pending:
                self.logger.info("🔐 Setting auth_flow_pending flag - waiting for user email/OTP")
                self.save_memory_block(
                    block_label="auth_flow_pending",
                    block_value="true",
                    priority=10,
                    agent_scope="booking"  # CRITICAL: Must match get_memory_blocks() scope
                )
            else:
                self.logger.info("✅ Clearing auth_flow_pending flag - authentication complete")
                # Clear the flag by setting to false
                self.save_memory_block(
                    block_label="auth_flow_pending",
                    block_value="false",
                    priority=10,
                    agent_scope="booking"  # CRITICAL: Must match get_memory_blocks() scope
                )

        except Exception as e:
            self.logger.warning(f"Error setting auth_flow_pending flag: {e}")
            # Don't fail the whole request if we can't set the flag

    def _get_authentication_prompt(
        self,
        session_expired: bool,
        language: str
    ) -> str:
        """Get authentication prompt based on session status.

        Args:
            session_expired: True if session was authenticated but expired
            language: User's language (es|en)

        Returns:
            str: Localized authentication prompt
        """
        # Get timeout value from centralized configuration
        timeout_display = OTPSessionConfig.get_session_timeout_display(language)

        if session_expired:
            # Session was valid but expired due to inactivity
            if language == "en":
                return (
                    f"⏰ Your session has expired due to inactivity ({timeout_display}).\n\n"
                    "For security, I need to verify your identity again.\n"
                    "What's your email address?"
                )
            else:  # Spanish (default)
                return (
                    f"⏰ Tu sesión ha expirado por inactividad ({timeout_display}).\n\n"
                    "Por seguridad, necesito verificar tu identidad nuevamente.\n"
                    "¿Cuál es tu correo electrónico?"
                )
        else:
            # No session or first time
            if language == "en":
                return (
                    "Hello! 👋 Welcome.\n\n"
                    "To get started, I need your email address.\n"
                    "What's your email?"
                )
            else:  # Spanish (default)
                return (
                    "¡Hola! 👋 Bienvenido(a).\n\n"
                    "Para comenzar, necesito tu correo electrónico.\n"
                    "¿Cuál es tu email?"
                )

    def _get_auth_error_message(self, language: str) -> str:
        """Get error message when authentication check fails.

        Args:
            language: User's language (es|en)

        Returns:
            str: Localized error message
        """
        if language == "en":
            return (
                "I'm sorry, I'm having trouble verifying your session.\n\n"
                "Please provide your email address to continue."
            )
        else:  # Spanish (default)
            return (
                "Disculpa, estoy teniendo problemas para verificar tu sesión.\n\n"
                "Por favor, proporciona tu correo electrónico para continuar."
            )

    def get_system_prompt(
        self,
        customer_email: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Get system prompt for BookingAgent using PromptManager (Jinja2).

        Implements BaseAgent's abstract method.

        Configuration-driven thresholds:
        - TOKEN_ESTIMATE_RATIO: Ratio for estimating tokens from character count (default: 0.25)
        - BOOKING_MAX_PROMPT_SIZE_CHARS: Maximum prompt size in characters (warning threshold, default: 30000)

        CRITICAL FIX: Includes memory blocks and conversation context in system prompt
        to help agent understand user preferences and previous conversation state.

        Args:
            customer_email: Optional customer email for personalization.
            **kwargs: Additional parameters (user_id for A/B testing, etc.).

        Returns:
            System prompt text for BookingAgent.

        Example:
            >>> prompt = agent.get_system_prompt(customer_email="maria@example.com")
        """
        # Initialize PromptManager if not already done
        if self._prompt_manager is None:
            self.logger.debug("Initializing PromptManager for BookingAgent (Jinja2)")
            self._prompt_manager = PromptManager()

        # Get prompt from PromptManager (supports A/B testing and multilingual)
        user_lang = kwargs.get("user_lang", "es")
        self.logger.info(f"🌐 GET_SYSTEM_PROMPT: Requesting template for language: {user_lang}")
        prompt = self._prompt_manager.get_booking_prompt(
            customer_email=customer_email,
            user_id=kwargs.get("user_id"),
            user_lang=user_lang,  # Pass language context for template selection
        )

        # CRITICAL: Add session_id to prompt for authentication flow
        # The agent needs this to call check_session_auth() and clear_session_auth() tools
        if self.session_id:
            prompt += f"\n\n## CURRENT SESSION CONTEXT:\n"
            prompt += f"**Session ID:** {self.session_id}\n"
            prompt += f"⚠️ IMPORTANT: Use this session_id when calling check_session_auth() or clear_session_auth() tools.\n"

        # CRITICAL FIX: Append memory blocks context to system prompt
        # This helps the agent understand user preferences and conversation history
        if self._memory_enabled:
            try:
                # Get session-level memory blocks (this conversation)
                session_blocks = self.get_memory_blocks(agent_scope="booking")
                if session_blocks:
                    self.logger.debug(f"Including {len(session_blocks)} session memory blocks in prompt")
                    blocks_text = "\n".join([
                        f"  - {block['block_label']}: {block['block_value']}"
                        for block in session_blocks
                    ])
                    prompt += f"\n\n## CONTEXTO DE CONVERSACIÓN (Session Memory):\n{blocks_text}"

                # Get user-level memory blocks (cross-session) for personalization
                if customer_email:
                    try:
                        user_blocks = self.memory_manager.get_user_memory_blocks(
                            customer_email=customer_email,
                            agent_scope="shared"
                        )
                        if user_blocks:
                            self.logger.debug(f"Including {len(user_blocks)} user memory blocks in prompt")
                            user_blocks_text = "\n".join([
                                f"  - {block['block_label']}: {block['block_value']}"
                                for block in user_blocks
                            ])
                            prompt += f"\n\n## PREFERENCIAS DE USUARIO (User Profile):\n{user_blocks_text}"
                    except Exception as e:
                        self.logger.debug(f"Could not load user memory blocks: {e}")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to include memory blocks in prompt: {e}")
                # Continue gracefully - agent can still function without memory blocks

        prompt_size = len(prompt)
        estimated_tokens = int(prompt_size * booking_agent_settings.TOKEN_ESTIMATE_RATIO)
        self.logger.info(
            f"✅ Loaded booking prompt from Jinja2 (lang={user_lang}, "
            f"{prompt_size} chars, ~{estimated_tokens} tokens)"
        )
        # Log first 200 chars of prompt to verify template
        self.logger.debug(f"Prompt preview: {prompt[:200]}...")

        # Warn if prompt exceeds configured threshold
        if prompt_size > booking_agent_settings.BOOKING_MAX_PROMPT_SIZE_CHARS:
            self.logger.warning(
                f"⚠️ Prompt is very long: {prompt_size} chars (~{estimated_tokens} tokens)\n"
                f"   This may cause issues with Gemini API (recommended < {booking_agent_settings.BOOKING_MAX_PROMPT_SIZE_CHARS} chars)"
            )

        return prompt

    async def generate_response(
        self,
        query: str,
        *,
        include_history: bool = True,
        intent: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate response for user query with function calling support.

        Implements Gemini 2.5 Best Practices:
        - Scope limiting: Only booking tools are available
        - Strict system instructions: Prevents hallucinations and off-topic responses
        - Function calling with AUTO mode: Flexible, natural conversation flow
        - Runtime scope validation: Ensures no function calls outside allowed scope

        This method overrides BaseAgent.generate_response() to add function
        calling loop support. When Gemini wants to call a tool, this method:
        1. Detects the function call
        2. Validates it's in BOOKING_TOOLS_ALLOWED (scope check)
        3. Executes it via MCP
        4. Sends result back to Gemini
        5. Repeats until text response

        Args:
            query: User query/message to respond to.
            include_history: Whether to include conversation history.
            **kwargs: Agent-specific parameters (customer_email, user_id, etc.).

        Returns:
            Generated response text from agent.

        Raises:
            RuntimeError: If client not initialized or function calling not available.

        Example:
            >>> response = await booking_agent.generate_response(
            ...     "Quiero agendar para el 2025-10-27",
            ...     customer_email="customer@example.com"
            ... )

        Security Notes (Gemini 2.5):
        - All functions validated against BOOKING_TOOLS_ALLOWED before execution
        - System prompt includes explicit scope boundaries
        - Out-of-scope queries are redirected to appropriate teams
        """
        # Check if client is initialized
        if not self.client:
            self.logger.error(f"{self.agent_name} not initialized - call initialize() first")
            raise RuntimeError(f"{self.agent_name} not initialized")

        # Start timing for metrics
        import time

        start_time = time.time()
        self._metrics["total_requests"] += 1

        try:
            # Store intent for use in _update_history()
            self.current_intent = intent

            self.logger.info(f"Generating response for: '{query[:100]}...'")

            # ================================================================
            # 🔐 MANDATORY AUTHENTICATION CHECK - BLOCKING GUARD
            # ================================================================
            # CRITICAL: Check session authentication BEFORE processing ANY request
            # This is a HARD BLOCK at the code level - Gemini cannot bypass this
            auth_check_result = await self._check_and_enforce_authentication(query, **kwargs)
            if auth_check_result:
                # User is not authenticated - return authentication prompt immediately
                # Do NOT proceed to Gemini, do NOT process the request
                self.logger.warning(
                    f"🔒 Authentication required - blocking request until user authenticates"
                )
                return auth_check_result
            # If we reach here, user is authenticated - proceed normally
            self.logger.info("✅ User authenticated - proceeding with request")

            # Auto-detect or use provided language for consistent context
            if "language" in kwargs:
                # Priority 1: Explicit language parameter from caller
                new_language = kwargs["language"]
                if new_language != self.language:
                    self.logger.info(
                        f"🌐 Updating agent language (explicit): {self.language} → {new_language}"
                    )
                    self.language = new_language
            else:
                # Priority 2: Auto-detect language from user query (using inherited language_detector)
                detected_language = await self.language_detector.detect_language(
                    text=query,
                    session_language=self.language,  # Use current language as fallback
                    use_cache=True
                )
                if detected_language != self.language:
                    self.logger.info(
                        f"🌐 Auto-detected language: {self.language} → {detected_language}"
                    )
                    self.language = detected_language
                kwargs["language"] = detected_language

            # Build conversation contents (uses template method pattern)
            contents = self._build_contents(query, include_history, **kwargs)

            # DEBUG: Log contents size for diagnosis (using configurable token estimation ratio)
            total_chars = sum(len(str(content)) for content in contents)
            estimated_tokens = int(total_chars * booking_agent_settings.TOKEN_ESTIMATE_RATIO)
            self.logger.debug(
                f"Contents built: {len(contents)} messages, "
                f"{total_chars} chars, ~{estimated_tokens} tokens"
            )
            if total_chars > booking_agent_settings.BOOKING_MAX_CONTENT_SIZE_CHARS:
                self.logger.warning(
                    f"⚠️ Total contents size is very large: {total_chars} chars "
                    f"(~{estimated_tokens} tokens, threshold: {booking_agent_settings.BOOKING_MAX_CONTENT_SIZE_CHARS})"
                )

            # Build system prompt using language context (following Google Gemini best practices)
            kwargs["user_lang"] = self.language
            self.logger.info(
                f"🌐 GENERATE_RESPONSE: Agent language is '{self.language}', setting kwargs['user_lang']={self.language}"
            )
            system_prompt = self.get_system_prompt(**kwargs)
            self.logger.debug(
                f"Language: {self.language}, System prompt length: {len(system_prompt)}"
            )

            # Build generation config with system instruction
            if self.generation_config is None:
                raise RuntimeError(
                    "generation_config not initialized. Call initialize() first."
                )

            # GOOGLE BEST PRACTICE: Use temperature=0.0 for deterministic function calling
            # Reference: https://ai.google.dev/gemini-api/docs/function-calling
            # "Use low temperature values (e.g., 0) for more deterministic and reliable function calls"
            config_dict = {
                "temperature": 0.0,  # Deterministic responses (reduces empty response rate)
                "top_k": self.generation_config.top_k,
                "top_p": self.generation_config.top_p,
                "max_output_tokens": 2048,  # Explicit limit (prevents MAX_TOKENS empty response)
                "response_mime_type": self.generation_config.response_mime_type,
                "system_instruction": system_prompt,
            }

            # === GOOGLE BEST PRACTICE: Control thinking budget for Gemini 2.5 ===
            # Gemini 2.5 Flash has thinking enabled by default (dynamic budget).
            # Explicitly setting thinking_budget prevents token exhaustion issues.
            # Reference: https://ai.google.dev/gemini-api/docs/thinking
            thinking_budget = booking_agent_settings.BOOKING_THINKING_BUDGET
            if thinking_budget is not None and thinking_budget >= 0:
                config_dict["thinking_config"] = types.GenerationConfigThinkingConfig(
                    thinking_budget=thinking_budget
                )
                reserved_output = self.generation_config.max_output_tokens - thinking_budget
                self.logger.info(
                    f"✅ Thinking budget configured: {thinking_budget} tokens "
                    f"(reserves ~{reserved_output} for actual output)"
                )

            # CRITICAL FIX: Only add response_schema if NO tools are available
            # When tools are present, response_schema conflicts with function_calling:
            # - response_schema forces Gemini to return structured JSON
            # - function_calling expects Gemini to return function_call parts
            # - These are mutually exclusive → response.parts becomes None
            # Solution: Use response_schema ONLY for text-only responses (no tools)
            if not self.mcp_tools:
                config_dict["response_schema"] = BOOKING_RESPONSE_SCHEMA
                self.logger.info(
                    "✅ Structured output enabled: BOOKING_RESPONSE_SCHEMA with intent detection"
                )
            else:
                self.logger.info(
                    "⏭️ Skipping response_schema (tools present): Let Gemini choose function calls naturally"
                )

            # Add tools and tool config if available
            # Implements Gemini 2.5 Function Calling Best Practices
            if self.mcp_tools:
                # Validate tools are in allowed booking tools (scope limiting)
                # BOOKING_TOOLS_ALLOWED is autodiscovered from get_booking_tool_names()
                # This prevents the agent from calling unintended functions
                # If autodiscover failed, falls back to hardcoded list
                tool_names = {func.name for func in self.mcp_tools}
                invalid_tools = tool_names - BOOKING_TOOLS_ALLOWED
                if invalid_tools:
                    self.logger.warning(
                        f"⚠️ Invalid tools passed to BookingAgent (not in BOOKING_TOOLS_ALLOWED): "
                        f"{invalid_tools}. These will be available but not recommended by system prompt."
                    )

                config_dict["tools"] = [types.Tool(function_declarations=self.mcp_tools)]
                config_dict["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        # Mode selection rationale:
                        # - AUTO (default): Model decides when to call functions
                        #   ✅ Flexible (can choose text or function calls)
                        #   ✅ Good for booking (sometimes just answer questions)
                        #   ✅ Prevents forced function calling when not needed
                        # - ANY: Model MUST call a function (if specified allowed_function_names)
                        #   ❌ Not ideal for booking (some queries need text only)
                        # - NONE: No function calling (use only if debugging)
                        #   ❌ Defeats purpose of MCP integration
                        mode=types.FunctionCallingConfigMode.AUTO,
                    )
                )

                self.logger.info(
                    f"✅ Function calling configured: AUTO mode with {len(self.mcp_tools)} booking tools"
                )

            # CRITICAL FIX: Avoid conflict between response_schema and function_calling_loop
            # Google Gemini API returns 500 INTERNAL when response_schema is used in
            # subsequent calls within a function calling loop. Solution: create two configs:
            # 1. initial_config: WITH response_schema (for first call, intent detection)
            # 2. loop_config: WITHOUT response_schema (for function calling loop iterations)
            # Reference: https://github.com/google-gemini/generative-ai-python/issues/...

            initial_config = types.GenerateContentConfig(**config_dict)  # type: ignore[arg-type]

            # For function calling loop: remove response_schema to avoid API conflicts
            loop_config_dict = config_dict.copy()
            loop_config_dict.pop("response_schema", None)
            loop_config = types.GenerateContentConfig(**loop_config_dict)  # type: ignore[arg-type]

            self.logger.debug(
                "📋 Created two configs: initial_config (WITH schema), loop_config (WITHOUT schema)"
            )

            # Generate initial response with system_instruction in config
            # (uses response_schema for intent detection)
            if self.client is None:
                raise RuntimeError(
                    "Gemini client not initialized. Call initialize() first."
                )

            # === GOOGLE BEST PRACTICE: Use retry with exponential backoff ===
            response = await self.response_handler.retry_with_backoff(
                self.client.aio.models.generate_content,
                model=self.model_name,
                contents=contents,  # type: ignore[arg-type]
                config=initial_config,
            )

            # === EARLY VALIDATION: Catch errors before entering function calling loop ===
            # Validates finish_reason, safety_ratings, empty content/parts
            # Provides better diagnostics and faster failure detection
            initial_status, initial_diagnostic = self.response_handler.validate_response(response)
            if initial_status != ResponseStatus.SUCCESS:
                self.logger.warning(
                    f"⚠️ Initial response validation failed: {initial_status}"
                )
                self.response_handler.log_response_diagnostics(
                    response=response,
                    query=query[:100] if query else "N/A",
                    status=initial_status,
                )
                # Return fallback immediately - don't enter function calling loop
                return await self._create_fallback_response(1)

            # DEBUG: Log response details for diagnosis
            self.logger.debug(f"Response type: {type(response).__name__}")
            self.logger.debug(f"Has candidates: {hasattr(response, 'candidates')}")
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                self.logger.debug(f"Candidates count: {len(response.candidates)}")
                self.logger.debug(f"Candidate.content: {candidate.content}")
                self.logger.debug(
                    f"Candidate.finish_reason: {getattr(candidate, 'finish_reason', 'N/A')}"
                )
                self.logger.debug(
                    f"Candidate.safety_ratings: {getattr(candidate, 'safety_ratings', 'N/A')}"
                )

            # CRITICAL FIX: Save original user query BEFORE function calling loop
            # The loop appends function responses with role="user", making it impossible
            # to find the original user query later. We need to preserve it now.
            original_user_query = types.Content(role="user", parts=[types.Part(text=query)])

            # Run function calling loop if tools are available
            # Use loop_config (WITHOUT response_schema) to avoid API conflicts
            if self.mcp_tools and self.function_call_handler:
                final_text, tool_calls, token_count = await self._run_function_calling_loop(
                    response, contents, loop_config
                )
            else:
                # No tools - extract text directly (fallback to BaseAgent behavior)
                final_text = await self._extract_text_from_response(response)
                tool_calls = None  # No tools were called
                # Extract token count from initial response
                token_count = None
                try:
                    if hasattr(response, 'usage_metadata') and response.usage_metadata:
                        token_count = response.usage_metadata.total_token_count
                except (AttributeError, TypeError):
                    pass

            # Calculate elapsed time BEFORE updating history (for accurate DB storage)
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Update history if requested
            if include_history:
                self.logger.info(
                    f"📝 Updating history (session_id={self.session_id}, "
                    f"memory_enabled={self._memory_enabled}, "
                    f"memory_manager={self.memory_manager is not None})"
                )

                # Use the original user query saved before function calling loop
                # (not the function response parts that were appended with role="user")
                self._update_history(
                    original_user_query,
                    types.Content(role="model", parts=[types.Part(text=final_text)]),
                    response_time_ms=elapsed_ms,
                    tool_calls=tool_calls,
                    token_count=token_count
                )
            else:
                self.logger.warning("⚠️ History update skipped (include_history=False)")

            # Track success metrics
            self._metrics["successful_requests"] += 1
            self._metrics["total_response_time_ms"] += elapsed_ms
            self._metrics["history_sizes"].append(len(self.conversation_history))

            self.logger.info(f"✅ Response generated ({len(final_text)} chars, {elapsed_ms:.0f}ms)")
            return final_text

        except Exception as e:
            # Track error metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self._metrics["failed_requests"] += 1
            self._metrics["total_response_time_ms"] += elapsed_ms

            # Track error type
            error_type = type(e).__name__
            self._metrics["errors"][error_type] = self._metrics["errors"].get(error_type, 0) + 1

            self.logger.exception(f"Error generating response: {e}")
            raise

    async def _run_function_calling_loop(
        self,
        response: Any,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> tuple[str, list[dict[str, Any]] | None, int | None]:
        """Run function calling loop until text response or max iterations.

        Args:
            response: Initial Gemini API response.
            contents: Current conversation contents.
            config: Generation config with system instruction and language context.

        Returns:
            Tuple of (final_text, tool_calls_log, token_count) where:
            - final_text: The final response text
            - tool_calls_log: List of tool calls executed during the loop
            - token_count: Total token count from final Gemini response
        """
        if self.client is None:
            raise RuntimeError(
                "Gemini client not initialized. Call initialize() first."
            )
        if not self.function_call_handler:
            raise RuntimeError("Function call handler not available")

        # Track all tool calls for analytics/debugging
        tool_calls_log: list[dict[str, Any]] = []

        # Helper function to extract token count from response
        def extract_token_count(resp: Any) -> int | None:
            try:
                if hasattr(resp, 'usage_metadata') and resp.usage_metadata:
                    return resp.usage_metadata.total_token_count
            except (AttributeError, TypeError):
                pass
            return None

        # Track last response for token count extraction
        last_response = response

        iteration = 0
        max_iterations = self.function_call_handler.max_iterations

        while iteration < max_iterations:
            iteration += 1
            self.logger.debug(f"Function calling iteration {iteration}/{max_iterations}")

            # === GOOGLE BEST PRACTICE: Validate response before processing ===
            # Check finish_reason, safety_ratings, empty content, etc.
            status, diagnostic_msg = self.response_handler.validate_response(response)

            if status != ResponseStatus.SUCCESS:
                # Log comprehensive diagnostics
                self.response_handler.log_response_diagnostics(
                    response=response,
                    query=contents[0].parts[0].text if contents else "N/A",
                    status=status,
                )

                # Handle based on status
                if status == ResponseStatus.SAFETY_BLOCKED:
                    # Safety filters triggered - cannot retry, use fallback
                    self.logger.warning(f"🚫 Safety filter blocked response: {diagnostic_msg}")
                    fallback = await self._create_fallback_response(iteration)
                    return (fallback, tool_calls_log if tool_calls_log else None, extract_token_count(response))

                elif status == ResponseStatus.RECITATION:
                    # Recitation detected - increase temperature and retry
                    self.logger.warning(f"📋 Recitation detected: {diagnostic_msg}")
                    fallback = await self._create_fallback_response(iteration)
                    return (fallback, tool_calls_log if tool_calls_log else None, extract_token_count(response))

                elif status == ResponseStatus.MAX_TOKENS:
                    # Hit token limit - extract partial response or use fallback
                    self.logger.warning(f"⚠️ Max tokens reached: {diagnostic_msg}")
                    try:
                        # Try to extract partial text
                        content = response.candidates[0].content if response.candidates else None
                        text = self.function_call_handler.extract_text_from_content(content)
                        if text and len(text.strip()) > 10:
                            return (text, tool_calls_log if tool_calls_log else None, extract_token_count(response))
                    except (AttributeError, IndexError):
                        pass
                    fallback = await self._create_fallback_response(iteration)
                    return (fallback, tool_calls_log if tool_calls_log else None, extract_token_count(response))

                else:
                    # Empty response, no candidates, or unknown error
                    self.logger.warning(f"⚠️ Response validation failed: {status} - {diagnostic_msg}")
                    fallback = await self._create_fallback_response(iteration)
                    return (fallback, tool_calls_log if tool_calls_log else None, extract_token_count(response))

            # === Response is valid - proceed with function calling ===
            # Get parts from response
            parts = self.function_call_handler.get_parts(response)

            # === DEFENSIVE CHECK: Ensure parts is not None ===
            # This can happen in edge cases where content exists but parts are empty
            # Matches SalesAgent's defensive programming pattern
            if parts is None:
                self.logger.warning(
                    f"⚠️ Response parts is None after validation (iteration {iteration}) - edge case detected"
                )
                fallback = await self._create_fallback_response(iteration)
                return (fallback, tool_calls_log if tool_calls_log else None, extract_token_count(response))

            # Extract function calls
            function_calls = self.function_call_handler.extract_function_calls(parts)

            # If no function calls, extract and return text
            if not function_calls:
                text = self.function_call_handler.extract_text(parts)
                if text:
                    self.logger.debug(f"Extracted final text: {text[:100]}...")
                    return (text, tool_calls_log if tool_calls_log else None, extract_token_count(response))
                else:
                    # Try fallback text extraction from content
                    try:
                        content = response.candidates[0].content if response.candidates else None
                        text = self.function_call_handler.extract_text_from_content(content)
                        if text:
                            self.logger.debug(f"Extracted text from content (fallback): {text[:100]}...")
                            return (text, tool_calls_log if tool_calls_log else None, extract_token_count(response))
                    except (AttributeError, IndexError):
                        pass

                    self.logger.warning(f"No function calls and no text in iteration {iteration}")
                    fallback = await self._create_fallback_response(iteration)
                    return (fallback, tool_calls_log if tool_calls_log else None, extract_token_count(response))

            # Execute function calls
            self.logger.debug(f"Found {len(function_calls)} function calls")

            # Track tool calls for analytics/debugging
            for fc in function_calls:
                tool_calls_log.append({
                    "tool_name": fc.name,
                    "args": dict(fc.args) if fc.args else {},
                })

            function_response_parts = await self._execute_function_calls(function_calls)

            # Add function call parts to contents (model response)
            contents.append(types.Content(role="model", parts=parts))

            # Add function response parts (user role)
            contents.append(types.Content(role="user", parts=function_response_parts))

            # Generate next response with system_instruction in config
            # (maintain language context through function calling loop)
            # Use retry logic for transient errors
            response = await self.response_handler.retry_with_backoff(
                self.client.aio.models.generate_content,
                model=self.model_name,
                contents=contents,  # type: ignore[arg-type]
                config=config,
            )

        # Exhausted iterations
        self.logger.warning(f"Function calling loop exhausted after {iteration} iterations")
        fallback = await self._create_fallback_response(iteration)
        return (fallback, tool_calls_log if tool_calls_log else None, extract_token_count(response))

    async def _execute_function_calls(self, function_calls: list[Any]) -> list[types.Part]:
        """Execute function calls and return structured responses.

        Implements scope validation (Gemini 2.5 best practice) to ensure
        the agent only calls booking-related functions and never attempts
        to call functions outside the allowed scope.

        Args:
            function_calls: List of function call objects from response.

        Returns:
            List of FunctionResponse Parts with structured data.

        Raises:
            ValueError: If function call attempts to call non-booking function.
        """
        function_response_parts = []

        for fc in function_calls:
            function_name = fc.name
            function_args = dict(fc.args)

            # SCOPE VALIDATION: Gemini 2.5 Best Practice
            # Ensure agent only calls allowed booking tools
            if function_name not in BOOKING_TOOLS_ALLOWED:
                self.logger.error(
                    f"🚫 SCOPE VIOLATION: Attempted to call '{function_name}' "
                    f"which is NOT in BOOKING_TOOLS_ALLOWED. Returning error."
                )
                # Return error response instead of calling the invalid function
                response_data = {
                    "error": f"Function '{function_name}' is not available for this agent. "
                    f"Only booking-related functions are allowed.",
                    "function": function_name,
                    "allowed_functions": sorted(BOOKING_TOOLS_ALLOWED),
                }
                function_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=function_name, response=response_data
                        )
                    )
                )
                continue  # Skip to next function call

            self.logger.info(f"🔧 Executing: {function_name}({function_args})")

            try:
                # Execute tool
                result = await self._execute_tool(function_name, function_args)
                self.logger.debug(f"✅ Tool result: {type(result).__name__}")

                # Serialize result
                response_data = self._serialize_tool_result(result)

                function_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=function_name, response=response_data
                        )
                    )
                )

            except Exception as e:
                self.logger.exception(f"❌ Error executing {function_name}: {e}")
                # Structured error response
                response_data = {
                    "error": str(e),
                    "function": function_name,
                    "args": function_args,
                }

                function_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=function_name, response=response_data
                        )
                    )
                )

        return function_response_parts

    async def _execute_tool(self, tool_name: str, args: dict) -> Any:
        """Execute a single tool with proper error handling and language context.

        Propagates the agent's language context to MCP tools so responses
        are in the correct language (English or Spanish).

        Args:
            tool_name: Tool name to execute.
            args: Tool arguments.

        Returns:
            Tool result (preserving structure).

        Raises:
            RuntimeError: If no MCP client available.
        """
        if not self.mcp_client:
            raise RuntimeError("No MCP client available for tool execution")

        # Propagate language context to MCP tools (CRITICAL for multilingual support)
        if LANGUAGE_CONTEXT_AVAILABLE and set_current_language:
            set_current_language(self.language)
            self.logger.debug(f"Set MCP language context to: {self.language}")

        # Execute tool via MCP (MCP handlers will use the language context)
        result = await self.mcp_client.call_tool(tool_name, args)
        return result

    def _serialize_tool_result(self, result: Any) -> dict:
        """Serialize tool result to structured format.

        Args:
            result: Tool result to serialize.

        Returns:
            Serialized result as dictionary.
        """
        if isinstance(result, dict):
            return result
        elif isinstance(result, list):
            return {"items": result}
        elif isinstance(result, str):
            return {"result": result}
        else:
            return {"result": str(result)}

    async def _extract_text_from_response(self, response: Any) -> str:
        """Extract text from response (fallback when no tools).

        Args:
            response: Gemini API response.

        Returns:
            Extracted text.

        Raises:
            RuntimeError: If no text found.
        """
        if not response.candidates or not response.candidates[0].content:
            self.logger.error("Empty response from Gemini API")
            raise RuntimeError("No response from Gemini")

        content_parts = response.candidates[0].content.parts
        if not content_parts or len(content_parts) == 0:
            self.logger.error("Response has no content parts")
            raise RuntimeError("No content parts in response")

        response_text = content_parts[0].text
        if not response_text:
            self.logger.error("Response text is None or empty")
            raise RuntimeError("Empty response text")

        return response_text

    async def _handle_validation_failure(
        self,
        status: ResponseStatus,
        diagnostic: str,
        query: str,
    ) -> str:
        """Override: Handle validation failures with booking-specific fallback logic.

        Booking agent provides graceful fallback responses instead of raising exceptions,
        ensuring users always get a helpful message even when API calls fail.

        Args:
            status: Response validation status (SAFETY_BLOCKED, EMPTY_RESPONSE, etc.)
            diagnostic: Diagnostic message explaining the failure
            query: Original user query (for logging context)

        Returns:
            Multilingual fallback message generated via BaseAgent._create_fallback_response()
        """
        # Log comprehensive diagnostics
        self.logger.warning(
            f"🚨 Booking agent validation failure: {status}\n"
            f"   Diagnostic: {diagnostic}\n"
            f"   Query: '{query[:100]}...'\n"
            f"   Returning multilingual fallback response"
        )

        # Return appropriate fallback based on error type
        if status == ResponseStatus.SAFETY_BLOCKED:
            # Safety filters triggered - cannot retry, use fallback
            return await self._create_fallback_response(iteration=1)

        elif status == ResponseStatus.RECITATION:
            # Recitation detected - use fallback
            return await self._create_fallback_response(iteration=1)

        elif status == ResponseStatus.MAX_TOKENS:
            # Hit token limit - use fallback
            return await self._create_fallback_response(iteration=1)

        else:
            # Other errors (EMPTY_RESPONSE, NO_CANDIDATES, etc.)
            return await self._create_fallback_response(iteration=2)

    def __repr__(self) -> str:
        """String representation of BookingAgent."""
        return (
            f"BookingAgent(model={self.model_name}, "
            f"tools={len(self.mcp_tools)}, "
            f"history_len={len(self.conversation_history)}, "
            f"mcp_connected={self.mcp_client is not None})"
        )
