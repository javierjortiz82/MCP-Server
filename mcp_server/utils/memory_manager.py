"""Memory Manager for Multi-Agent Persistent Context.

Manages conversation history, semantic memory extraction, and context transfer
between agents using PostgreSQL for persistence.

Architecture:
    - Short-term memory: Last 10 turns in RAM (BaseAgent.conversation_history)
    - Long-term memory: All messages in PostgreSQL (conversation_messages)
    - Semantic memory: LLM-extracted facts (agent_memory_blocks)
    - Context transfer: Handoff tracking (agent_context_transfers)

Best Practices:
    - Memory Blocks Pattern (Letta/MemGPT)
    - Hybrid Memory (RAM + PostgreSQL)
    - Priority Scoring (0-10)
    - TTL Management (auto-expiration)

References:
    - https://github.com/googleapis/python-genai
    - https://www.letta.com/blog/memory-blocks
    - https://python.langchain.com/docs/how_to/chatbots_memory/

Author: Lab01-MCP Team
Created: 2025-10-12
Version: 1.0.0 (Fase 2)
"""

import json
import uuid
from typing import Any

from pydantic import BaseModel, Field

from config.settings import settings
from utils.db import execute, fetchall, fetchone
from utils.logger import setup_logging

# Setup logger
logger = setup_logging("memory_manager")


# ============================================================================
# Pydantic Models (Data Validation)
# ============================================================================


class ConversationMessage(BaseModel):
    """Model for conversation message."""

    session_id: str = Field(description="UUID of the session")
    role: str = Field(description="'user' or 'model'")
    agent_name: str | None = Field(default=None, description="Agent that generated response")
    intent: str | None = Field(default=None, description="'sales', 'booking', or 'general'")
    message_text: str = Field(description="Message content")
    tool_calls: dict[str, Any] | None = Field(default=None, description="MCP tools used")
    response_time_ms: int | None = Field(default=None, description="Response latency")
    token_count: int | None = Field(default=None, description="Token count")


class MemoryBlock(BaseModel):
    """Model for semantic memory block (Letta pattern)."""

    session_id: str = Field(description="UUID of the session")
    block_label: str = Field(min_length=1, max_length=100, description="Memory category (user_preferences, product_interest, etc)")
    block_value: str = Field(min_length=1, max_length=2000, description="Memory content (LLM-extracted)")
    priority: int = Field(default=5, ge=0, le=10, description="Priority score (0-10)")
    agent_scope: str = Field(
        default="shared", description="'shared', 'sales', 'booking', or 'general'"
    )
    ttl_days: int = Field(default=90, gt=0, description="Time-to-live in days")


class UserMemoryBlock(BaseModel):
    """Model for user-level memory block (cross-session)."""

    customer_email: str = Field(description="Customer email (unique identifier)")
    block_label: str = Field(description="Memory category (user_preferences, product_interest, etc)")
    block_value: str = Field(min_length=1, max_length=2000, description="Memory content (LLM-extracted)")
    priority: int = Field(default=7, ge=0, le=10, description="Priority score (0-10)")
    agent_scope: str = Field(
        default="shared", description="'shared', 'sales', 'booking', or 'general'"
    )
    ttl_days: int = Field(default=180, gt=0, description="Time-to-live in days")
    source_session_id: str | None = Field(default=None, description="Source session UUID for tracking")


class ContextTransfer(BaseModel):
    """Model for agent context transfer."""

    session_id: str = Field(description="UUID of the session")
    from_agent: str = Field(description="Source agent name")
    to_agent: str = Field(description="Target agent name")
    transfer_reason: str | None = Field(default=None, description="Why transfer occurred")
    context_summary: str | None = Field(default=None, description="LLM-generated summary")
    memory_blocks_transferred: int = Field(default=0, description="Number of blocks transferred")
    success: bool = Field(default=True, description="Transfer success status")


# ============================================================================
# MemoryManager Class
# ============================================================================


class MemoryManager:
    """Manages persistent memory for multi-agent conversations.

    Provides methods to:
    - Save/load conversation messages
    - Extract semantic memory (Memory Blocks pattern)
    - Track context transfers between agents
    - Query conversation statistics

    Example:
        >>> memory = MemoryManager()
        >>> session_id = memory.create_session("maria@example.com")
        >>> memory.save_message(session_id, "user", "Busco una laptop gaming")
        >>> history = memory.get_recent_messages(session_id, limit=10)
    """

    def __init__(self):
        """Initialize MemoryManager with configuration from settings."""
        self.config = settings.get_memory_config()
        self.schema = settings.SCHEMA_NAME

        logger.info(
            f"MemoryManager initialized (enabled={self.config['enabled']}, "
            f"ttl_days={self.config['ttl_days']})"
        )

    # ========================================================================
    # Session Management
    # ========================================================================

    def create_session(
        self,
        customer_email: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a new conversation session.

        Args:
            customer_email: Optional customer email for tracking
            metadata: Optional metadata (device, source, campaign, etc)

        Returns:
            str: UUID of created session

        Example:
            >>> session_id = memory.create_session("maria@example.com", {"source": "web"})
        """
        session_id = str(uuid.uuid4())
        session_id_short = session_id[:8]  # For logging

        query = f"""
        INSERT INTO {self.schema}.conversation_sessions
            (id, customer_email, session_id, metadata)
        VALUES (%s, %s, %s, %s)
        """

        params = (session_id, customer_email, session_id, json.dumps(metadata or {}))

        try:
            execute(query, params)
            logger.info(f"Session created: {session_id_short} (email={customer_email})")
            return session_id
        except Exception as e:
            logger.error(f"Failed to create session {session_id_short}: {e}")
            raise

    def get_or_create_session(
        self,
        customer_email: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Get existing active session or create new one.

        IMPORTANT: Only returns non-archived sessions. If an archived session
        is found, a new session is created to ensure user gets fresh context.

        Args:
            customer_email: Customer email to find existing session
            session_id: Specific session ID to retrieve

        Returns:
            str: UUID of session

        Example:
            >>> session_id = memory.get_or_create_session(customer_email="maria@example.com")
        """
        if session_id:
            # Check if session exists and is not archived
            query = f"""
            SELECT id FROM {self.schema}.conversation_sessions
            WHERE id = %s AND archived = FALSE
            """
            result = fetchone(query, (session_id,))
            if result:
                return session_id
            # If session was archived, fall through to create new session

        if customer_email:
            # Find most recent NON-ARCHIVED session for customer
            query = f"""
            SELECT id FROM {self.schema}.conversation_sessions
            WHERE customer_email = %s
              AND archived = FALSE
            ORDER BY last_activity_at DESC
            LIMIT 1
            """
            result = fetchone(query, (customer_email,))
            if result:
                logger.debug(f"Found existing active session for {customer_email}")
                return result["id"]

            # If all sessions archived, user memory will be loaded instead
            logger.debug(f"No active session found for {customer_email}, creating new")

        # Create new session
        return self.create_session(customer_email)

    def update_session_agent(self, session_id: str, agent_name: str) -> None:
        """Update current agent for session.

        Args:
            session_id: Session UUID
            agent_name: Current agent name ('sales', 'booking', 'general')

        Example:
            >>> memory.update_session_agent(session_id, "sales")
        """
        query = f"""
        UPDATE {self.schema}.conversation_sessions
        SET current_agent = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """
        execute(query, (agent_name, session_id))
        logger.debug(f"Session {session_id[:8]} agent updated to: {agent_name}")

    # ========================================================================
    # Message Management
    # ========================================================================

    def save_message(
        self,
        session_id: str,
        role: str,
        message_text: str,
        agent_name: str | None = None,
        intent: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        response_time_ms: int | None = None,
        token_count: int | None = None,
    ) -> int:
        """Save a conversation message to database.

        Args:
            session_id: Session UUID
            role: 'user' or 'model'
            message_text: Message content
            agent_name: Agent that generated response (for model messages)
            intent: Classified intent ('sales', 'booking', 'general')
            tool_calls: List of MCP tools used
            response_time_ms: Response latency in milliseconds
            token_count: Token count for the message

        Returns:
            int: Message ID

        Example:
            >>> msg_id = memory.save_message(
            ...     session_id,
            ...     role="user",
            ...     message_text="Busco una laptop gaming",
            ...     intent="sales"
            ... )
        """
        # Validate with Pydantic
        msg = ConversationMessage(
            session_id=session_id,
            role=role,
            agent_name=agent_name,
            intent=intent,
            message_text=message_text,
            tool_calls=tool_calls,
            response_time_ms=response_time_ms,
            token_count=token_count,
        )

        query = f"""
        INSERT INTO {self.schema}.conversation_messages
            (session_id, role, agent_name, intent, message_text, tool_calls, response_time_ms, token_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        params = (
            msg.session_id,
            msg.role,
            msg.agent_name,
            msg.intent,
            msg.message_text,
            json.dumps(msg.tool_calls) if msg.tool_calls else None,
            msg.response_time_ms,
            msg.token_count,
        )

        try:
            result = fetchone(query, params)
            message_id = result["id"] if result else -1
            logger.debug(
                f"Message saved (id={message_id}, role={role}, "
                f"agent={agent_name}, len={len(message_text)})"
            )
            return message_id
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            raise

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent messages for a session.

        Args:
            session_id: Session UUID
            limit: Maximum number of messages to return (default: 10)

        Returns:
            list: Messages ordered by created_at DESC

        Example:
            >>> messages = memory.get_recent_messages(session_id, limit=10)
            >>> for msg in reversed(messages):  # Reverse to get chronological order
            ...     print(f"{msg['role']}: {msg['message_text']}")
        """
        # Use PostgreSQL function for optimized query
        query = f"SELECT * FROM {self.schema}.get_recent_messages(%s, %s)"

        try:
            messages = fetchall(query, (session_id, limit))
            logger.debug(f"Retrieved {len(messages)} recent messages for session {session_id[:8]}")
            return messages
        except Exception as e:
            logger.error(f"Failed to get recent messages: {e}")
            return []

    # ========================================================================
    # Memory Blocks Management (Semantic Memory)
    # ========================================================================

    def save_memory_block(
        self,
        session_id: str,
        block_label: str,
        block_value: str,
        priority: int = 5,
        agent_scope: str = "shared",
        ttl_days: int | None = None,
    ) -> int:
        """Save a semantic memory block (LLM-extracted fact).

        Args:
            session_id: Session UUID
            block_label: Memory category ('user_preferences', 'product_interest', etc)
            block_value: Memory content
            priority: Priority score 0-10 (default: 5)
            agent_scope: 'shared', 'sales', 'booking', or 'general' (default: 'shared')
            ttl_days: Time-to-live in days (default: from settings)

        Returns:
            int: Memory block ID

        Example:
            >>> block_id = memory.save_memory_block(
            ...     session_id,
            ...     block_label="product_interest",
            ...     block_value="Usuario interesado en laptops gaming con RTX 4060",
            ...     priority=8,
            ...     agent_scope="sales"
            ... )
        """
        # Validate with Pydantic
        block = MemoryBlock(
            session_id=session_id,
            block_label=block_label,
            block_value=block_value,
            priority=priority,
            agent_scope=agent_scope,
            ttl_days=ttl_days or self.config["ttl_days"],
        )

        # Only save if priority meets threshold
        if block.priority < self.config["priority_threshold"]:
            logger.debug(
                f"Memory block skipped (priority {block.priority} < "
                f"threshold {self.config['priority_threshold']})"
            )
            return -1

        query = f"""
        INSERT INTO {self.schema}.agent_memory_blocks
            (session_id, block_label, block_value, priority, agent_scope, ttl_days)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        params = (
            block.session_id,
            block.block_label,
            block.block_value,
            block.priority,
            block.agent_scope,
            block.ttl_days,
        )

        try:
            result = fetchone(query, params)
            block_id = result["id"] if result else -1
            logger.info(
                f"Memory block saved (id={block_id}, label={block_label}, "
                f"priority={priority}, scope={agent_scope})"
            )
            return block_id
        except Exception as e:
            logger.error(f"Failed to save memory block: {e}")
            raise

    def get_active_memory_blocks(
        self,
        session_id: str,
        agent_scope: str = "shared",
    ) -> list[dict[str, Any]]:
        """Get active (non-expired) memory blocks for a session.

        Args:
            session_id: Session UUID
            agent_scope: Agent scope to filter ('shared', 'sales', 'booking', 'general')

        Returns:
            list: Active memory blocks ordered by priority DESC

        Example:
            >>> blocks = memory.get_active_memory_blocks(session_id, agent_scope="sales")
            >>> for block in blocks:
            ...     print(f"{block['block_label']}: {block['block_value']}")
        """
        # Use PostgreSQL function for optimized query
        query = f"SELECT * FROM {self.schema}.get_active_memory_blocks(%s, %s)"

        try:
            blocks = fetchall(query, (session_id, agent_scope))
            logger.debug(
                f"Retrieved {len(blocks)} active memory blocks "
                f"(session={session_id[:8]}, scope={agent_scope})"
            )
            return blocks
        except Exception as e:
            logger.error(f"Failed to get memory blocks: {e}")
            return []

    # ========================================================================
    # Context Transfer Management
    # ========================================================================

    def record_context_transfer(
        self,
        session_id: str,
        from_agent: str,
        to_agent: str,
        transfer_reason: str | None = None,
        context_summary: str | None = None,
        memory_blocks_transferred: int = 0,
        success: bool = True,
    ) -> int:
        """Record agent context transfer (handoff).

        Args:
            session_id: Session UUID
            from_agent: Source agent name
            to_agent: Target agent name
            transfer_reason: Why transfer occurred
            context_summary: LLM-generated summary
            memory_blocks_transferred: Number of blocks transferred
            success: Transfer success status

        Returns:
            int: Transfer record ID

        Example:
            >>> transfer_id = memory.record_context_transfer(
            ...     session_id,
            ...     from_agent="sales",
            ...     to_agent="booking",
            ...     transfer_reason="User wants to schedule demo",
            ...     context_summary="Usuario interesado en laptop gaming, quiere agendar demo"
            ... )
        """
        # Validate with Pydantic
        transfer = ContextTransfer(
            session_id=session_id,
            from_agent=from_agent,
            to_agent=to_agent,
            transfer_reason=transfer_reason,
            context_summary=context_summary,
            memory_blocks_transferred=memory_blocks_transferred,
            success=success,
        )

        query = f"""
        INSERT INTO {self.schema}.agent_context_transfers
            (session_id, from_agent, to_agent, transfer_reason, context_summary, memory_blocks_transferred, success)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        params = (
            transfer.session_id,
            transfer.from_agent,
            transfer.to_agent,
            transfer.transfer_reason,
            transfer.context_summary,
            transfer.memory_blocks_transferred,
            transfer.success,
        )

        try:
            result = fetchone(query, params)
            transfer_id = result["id"] if result else -1
            logger.info(
                f"Context transfer recorded (id={transfer_id}, {from_agent} → {to_agent}, "
                f"success={success})"
            )
            return transfer_id
        except Exception as e:
            logger.error(f"Failed to record context transfer: {e}")
            raise

    # ========================================================================
    # Statistics and Analytics
    # ========================================================================

    def get_session_statistics(self, session_id: str) -> dict[str, Any] | None:
        """Get statistics for a session.

        Args:
            session_id: Session UUID

        Returns:
            dict: Statistics (messages, memory blocks, transfers, duration)

        Example:
            >>> stats = memory.get_session_statistics(session_id)
            >>> print(f"Total messages: {stats['total_messages']}")
            >>> print(f"Session duration: {stats['session_duration_minutes']} min")
        """
        # Use PostgreSQL function for optimized query
        query = f"SELECT * FROM {self.schema}.get_session_statistics(%s)"

        try:
            result = fetchone(query, (session_id,))
            if result:
                logger.debug(f"Session statistics retrieved for {session_id[:8]}")
            return result
        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            return None

    def cleanup_expired_memory_blocks(self) -> int:
        """Cleanup expired memory blocks (TTL management).

        Returns:
            int: Number of blocks deleted

        Example:
            >>> deleted_count = memory.cleanup_expired_memory_blocks()
            >>> print(f"Cleaned up {deleted_count} expired memory blocks")
        """
        if not self.config["auto_cleanup_enabled"]:
            logger.debug("Auto-cleanup disabled, skipping")
            return 0

        # Use PostgreSQL function for optimized cleanup
        query = f"SELECT {self.schema}.cleanup_expired_memory_blocks()"

        try:
            result = fetchone(query)
            deleted_count = result["cleanup_expired_memory_blocks"] if result else 0
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired memory blocks")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup expired memory blocks: {e}")
            return 0

    # ========================================================================
    # User Memory Management (Cross-Session - Fase 6)
    # ========================================================================

    def get_user_memory_blocks(
        self,
        customer_email: str,
        agent_scope: str = "shared",
    ) -> list[dict[str, Any]]:
        """Get cross-session memory blocks for user.

        Args:
            customer_email: Customer email
            agent_scope: Agent scope to filter ('shared', 'sales', 'booking', 'general')

        Returns:
            list: User memory blocks ordered by priority DESC

        Example:
            >>> blocks = memory.get_user_memory_blocks("maria@example.com")
            >>> for block in blocks:
            ...     print(f"{block['block_label']}: {block['block_value']}")
        """
        # Use PostgreSQL function for optimized query
        query = f"SELECT * FROM {self.schema}.get_user_memory_blocks(%s, %s)"

        try:
            blocks = fetchall(query, (customer_email, agent_scope))
            logger.debug(
                f"Retrieved {len(blocks)} user memory blocks "
                f"(email={customer_email}, scope={agent_scope})"
            )
            return blocks
        except Exception as e:
            logger.error(f"Failed to get user memory blocks: {e}")
            return []

    def save_user_memory_block(
        self,
        customer_email: str,
        block_label: str,
        block_value: str,
        priority: int = 7,
        agent_scope: str = "shared",
        source_session_id: str | None = None,
        ttl_days: int = 180,
    ) -> int:
        """Save user-level memory block (cross-session).

        Args:
            customer_email: Customer email
            block_label: Memory category
            block_value: Memory content
            priority: Priority score 0-10 (default: 7, higher than session-level)
            agent_scope: Agent scope (default: 'shared')
            source_session_id: Optional source session UUID for tracking
            ttl_days: Time-to-live in days (default: 180, longer than session-level)

        Returns:
            int: User memory block ID

        Example:
            >>> block_id = memory.save_user_memory_block(
            ...     "maria@example.com",
            ...     block_label="product_interest",
            ...     block_value="Usuario busca laptops gaming",
            ...     priority=9
            ... )
        """
        # Validate with Pydantic
        block = UserMemoryBlock(
            customer_email=customer_email,
            block_label=block_label,
            block_value=block_value,
            priority=priority,
            agent_scope=agent_scope,
            ttl_days=ttl_days,
            source_session_id=source_session_id,
        )

        # Ensure user profile exists
        profile_query = f"SELECT * FROM {self.schema}.get_or_create_user_profile(%s)"
        try:
            fetchone(profile_query, (block.customer_email,))
        except Exception as e:
            logger.error(f"Failed to get/create user profile: {e}")
            raise

        # Prepare source session IDs
        source_sessions = [block.source_session_id] if block.source_session_id else []

        query = f"""
        INSERT INTO {self.schema}.user_memory_blocks
            (customer_email, block_label, block_value, priority, agent_scope, source_session_ids, ttl_days)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        params = (
            block.customer_email,
            block.block_label,
            block.block_value,
            block.priority,
            block.agent_scope,
            json.dumps(source_sessions),
            block.ttl_days,
        )

        try:
            result = fetchone(query, params)
            block_id = result["id"] if result else -1
            logger.info(
                f"User memory block saved (id={block_id}, email={customer_email}, "
                f"label={block_label}, priority={priority})"
            )
            return block_id
        except Exception as e:
            logger.error(f"Failed to save user memory block: {e}")
            raise

    def sync_session_to_user_memory(
        self,
        session_id: str,
    ) -> dict[str, int]:
        """Promote high-priority session blocks to user profile.

        Automatically promotes memory blocks with priority >= 7 and scope='shared'
        from session-level to user-level memory.

        Args:
            session_id: Session UUID to sync

        Returns:
            dict: Sync statistics
                {
                    "synced_blocks": int,  # New blocks created
                    "updated_blocks": int,  # Existing blocks updated
                    "skipped_blocks": int  # Blocks skipped
                }

        Example:
            >>> stats = memory.sync_session_to_user_memory(session_id)
            >>> print(f"Synced {stats['synced_blocks']} new blocks")
        """
        # Use PostgreSQL function for sync logic
        query = f"SELECT * FROM {self.schema}.sync_session_to_user_memory(%s)"

        try:
            result = fetchone(query, (session_id,))
            if result:
                stats = {
                    "synced_blocks": result.get("synced_blocks", 0),
                    "updated_blocks": result.get("updated_blocks", 0),
                    "skipped_blocks": result.get("skipped_blocks", 0),
                }
                logger.info(
                    f"Session sync completed (session={session_id[:8]}, "
                    f"synced={stats['synced_blocks']}, updated={stats['updated_blocks']})"
                )
                return stats
            return {"synced_blocks": 0, "updated_blocks": 0, "skipped_blocks": 0}
        except Exception as e:
            logger.error(f"Failed to sync session to user memory: {e}")
            return {"synced_blocks": 0, "updated_blocks": 0, "skipped_blocks": 0}

    def get_user_profile(
        self,
        customer_email: str,
    ) -> dict[str, Any] | None:
        """Get user memory profile metadata.

        Args:
            customer_email: Customer email

        Returns:
            dict: User profile data or None if not found

        Example:
            >>> profile = memory.get_user_profile("maria@example.com")
            >>> print(f"First seen: {profile['first_seen_at']}")
            >>> print(f"Total sessions: {profile['total_sessions']}")
        """
        query = f"""
        SELECT
            customer_email,
            first_seen_at,
            last_seen_at,
            total_sessions,
            preferred_agent,
            metadata,
            created_at,
            updated_at
        FROM {self.schema}.user_memory_profiles
        WHERE customer_email = %s
        """

        try:
            result = fetchone(query, (customer_email,))
            if result:
                logger.debug(f"User profile retrieved for {customer_email}")
            return result
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return None

    def get_session_info(
        self,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Get session information including customer_email.

        Args:
            session_id: Session UUID

        Returns:
            dict: Session info or None if not found

        Example:
            >>> info = memory.get_session_info(session_id)
            >>> email = info['customer_email']
        """
        query = f"""
        SELECT
            id,
            customer_email,
            session_id,
            started_at,
            last_activity_at,
            current_agent,
            metadata
        FROM {self.schema}.conversation_sessions
        WHERE id = %s
        """

        try:
            result = fetchone(query, (session_id,))
            if result:
                logger.debug(f"Session info retrieved for {session_id[:8]}")
            return result
        except Exception as e:
            logger.error(f"Failed to get session info: {e}")
            return None

    def cleanup_expired_user_memory_blocks(self) -> int:
        """Cleanup expired user memory blocks.

        Returns:
            int: Number of blocks deleted

        Example:
            >>> deleted = memory.cleanup_expired_user_memory_blocks()
            >>> print(f"Cleaned up {deleted} expired user blocks")
        """
        query = f"SELECT {self.schema}.cleanup_expired_user_memory_blocks()"

        try:
            result = fetchone(query)
            deleted_count = result["cleanup_expired_user_memory_blocks"] if result else 0
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired user memory blocks")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup expired user memory blocks: {e}")
            return 0

    # ========================================================================
    # Session Lifecycle Management (GDPR Compliance - Fase 7)
    # ========================================================================

    def archive_inactive_sessions(
        self,
        inactivity_days: int | None = None,
    ) -> dict[str, int]:
        """Archive (soft delete) inactive sessions.

        Marks sessions as archived after N days of inactivity.
        Archived sessions are excluded from queries for better performance.

        Args:
            inactivity_days: Days of inactivity before archiving
                           (default: from settings.SESSION_SOFT_ARCHIVE_DAYS)

        Returns:
            dict: Archive statistics
                {
                    "archived_count": int,  # Sessions archived
                    "sessions": list[dict]  # Archived session details
                }

        Example:
            >>> stats = memory.archive_inactive_sessions(90)
            >>> print(f"Archived {stats['archived_count']} inactive sessions")
        """
        days = inactivity_days or settings.SESSION_SOFT_ARCHIVE_DAYS
        query = f"SELECT * FROM {self.schema}.archive_inactive_sessions(%s)"

        try:
            results = fetchall(query, (days,))
            archived_sessions = [
                {
                    "session_id": str(row["session_id"]),
                    "customer_email": row["customer_email"],
                    "last_activity_at": row["last_activity_at"],
                    "days_inactive": row["days_inactive"],
                }
                for row in results
            ]

            archived_count = len(archived_sessions)
            if archived_count > 0:
                logger.info(
                    f"Archived {archived_count} sessions inactive for {days}+ days"
                )
            else:
                logger.debug(f"No sessions eligible for archiving ({days}+ days)")

            return {
                "archived_count": archived_count,
                "sessions": archived_sessions,
            }
        except Exception as e:
            logger.error(f"Failed to archive inactive sessions: {e}")
            return {"archived_count": 0, "sessions": []}

    def cleanup_archived_sessions(
        self,
        archived_days: int | None = None,
    ) -> int:
        """Permanently delete archived sessions (hard delete).

        Deletes sessions that have been archived for N days.
        Uses CASCADE to delete related data (messages, memory blocks, transfers).

        Args:
            archived_days: Days after archiving before deletion
                          (default: from settings.SESSION_HARD_DELETE_DAYS)

        Returns:
            int: Number of sessions deleted

        Example:
            >>> deleted = memory.cleanup_archived_sessions(365)
            >>> print(f"Deleted {deleted} old archived sessions")
        """
        days = archived_days or settings.SESSION_HARD_DELETE_DAYS
        query = f"SELECT {self.schema}.cleanup_archived_sessions(%s)"

        try:
            result = fetchone(query, (days,))
            deleted_count = result["cleanup_archived_sessions"] if result else 0

            if deleted_count > 0:
                logger.info(
                    f"Deleted {deleted_count} sessions archived for {days}+ days"
                )
            else:
                logger.debug(f"No archived sessions eligible for deletion ({days}+ days)")

            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup archived sessions: {e}")
            return 0

    def cleanup_anonymous_sessions(
        self,
        inactive_days: int | None = None,
    ) -> int:
        """Delete anonymous sessions (no customer_email).

        Anonymous sessions have low business value and can be deleted faster.

        Args:
            inactive_days: Days of inactivity before deletion
                          (default: from settings.SESSION_ANONYMOUS_DELETE_DAYS)

        Returns:
            int: Number of anonymous sessions deleted

        Example:
            >>> deleted = memory.cleanup_anonymous_sessions(30)
            >>> print(f"Deleted {deleted} anonymous sessions")
        """
        days = inactive_days or settings.SESSION_ANONYMOUS_DELETE_DAYS
        query = f"SELECT {self.schema}.cleanup_anonymous_sessions(%s)"

        try:
            result = fetchone(query, (days,))
            deleted_count = result["cleanup_anonymous_sessions"] if result else 0

            if deleted_count > 0:
                logger.info(
                    f"Deleted {deleted_count} anonymous sessions inactive for {days}+ days"
                )
            else:
                logger.debug(f"No anonymous sessions eligible for deletion ({days}+ days)")

            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup anonymous sessions: {e}")
            return 0

    def get_session_retention_stats(self) -> dict[str, dict[str, int | float]]:
        """Get session retention statistics for monitoring.

        Returns:
            dict: Retention metrics with counts and percentages
                {
                    "active_sessions": {"count": int, "percentage": float},
                    "archived_sessions": {"count": int, "percentage": float},
                    "with_email": {"count": int, "percentage": float},
                    "anonymous": {"count": int, "percentage": float},
                    "active_7d": {"count": int, "percentage": float},
                    "active_30d": {"count": int, "percentage": float},
                    "eligible_archive": {"count": int, "percentage": float},
                    "eligible_delete": {"count": int, "percentage": float}
                }

        Example:
            >>> stats = memory.get_session_retention_stats()
            >>> print(f"Active: {stats['active_sessions']['count']}")
            >>> print(f"Eligible for archive: {stats['eligible_archive']['count']}")
        """
        query = f"SELECT * FROM {self.schema}.get_session_retention_stats()"

        try:
            results = fetchall(query)

            # Transform results into structured dict
            stats = {}
            for row in results:
                metric_name = row["metric"]
                stats[metric_name] = {
                    "count": int(row["count"]),
                    "percentage": float(row["percentage"]),
                }

            logger.debug("Session retention statistics retrieved")
            return stats

        except Exception as e:
            logger.error(f"Failed to get session retention stats: {e}")
            return {}
