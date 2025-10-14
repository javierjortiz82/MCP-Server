"""Context Transfer Handler for Multi-Agent Handoffs.

Manages context preservation and transfer between specialized agents (Sales, Booking, General).
Follows best practices from Letta Memory Blocks pattern and LangChain context management.

Architecture:
    When user intent changes (e.g., sales → booking):
    1. Extract relevant context from source agent
    2. Identify and transfer important memory blocks
    3. Record handoff in database for analytics
    4. Provide context summary to target agent

Best Practices:
    - Semantic Compression: LLM summarizes conversation before transfer
    - Selective Transfer: Only transfer relevant memory blocks
    - Context Scoring: Priority-based filtering (priority >= 5)
    - Audit Trail: All transfers logged for debugging

References:
    - Letta Memory Blocks: https://www.letta.com/blog/memory-blocks
    - LangChain Multi-Agent: https://python.langchain.com/docs/

Author: Lab01-MCP Team
Created: 2025-10-12
Version: 1.0.0 (Fase 3)
"""

from typing import Any

from pydantic import BaseModel, Field

from utils.logger import setup_logging
from utils.memory_manager import MemoryManager

# Setup logger
logger = setup_logging("context_transfer")


# ============================================================================
# Pydantic Models
# ============================================================================


class TransferContext(BaseModel):
    """Context data transferred between agents."""

    session_id: str = Field(description="Session UUID")
    from_agent: str = Field(description="Source agent name")
    to_agent: str = Field(description="Target agent name")
    transfer_reason: str = Field(description="Why transfer is happening")
    conversation_summary: str = Field(description="LLM-generated summary of conversation")
    memory_blocks: list[dict[str, Any]] = Field(
        default_factory=list, description="Relevant memory blocks to transfer"
    )
    user_query: str = Field(description="User query that triggered transfer")


# ============================================================================
# ContextTransferHandler Class
# ============================================================================


class ContextTransferHandler:
    """Manages context transfer between agents with memory preservation.

    Provides methods to:
    - Extract context from source agent
    - Filter and transfer relevant memory blocks
    - Record handoffs in database
    - Prepare context for target agent

    Example:
        >>> handler = ContextTransferHandler(memory_manager)
        >>> context = await handler.prepare_transfer(
        ...     session_id=session_id,
        ...     from_agent="sales",
        ...     to_agent="booking",
        ...     reason="User wants to schedule demo",
        ...     conversation_history=history
        ... )
        >>> await handler.execute_transfer(context)
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        """Initialize ContextTransferHandler.

        Args:
            memory_manager: MemoryManager instance for persistence.
                If None, creates new instance.
        """
        self.memory = memory_manager or MemoryManager()
        logger.info("ContextTransferHandler initialized")

    async def prepare_transfer(
        self,
        session_id: str,
        from_agent: str,
        to_agent: str,
        reason: str,
        user_query: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> TransferContext:
        """Prepare context for agent transfer.

        Analyzes conversation history and memory blocks to prepare
        optimal context for target agent.

        Args:
            session_id: Session UUID
            from_agent: Source agent name ('sales', 'booking', 'general')
            to_agent: Target agent name
            reason: Why transfer is happening
            user_query: User query that triggered transfer
            conversation_history: Optional conversation turns for summarization

        Returns:
            TransferContext with all relevant context data

        Example:
            >>> context = await handler.prepare_transfer(
            ...     session_id=session_id,
            ...     from_agent="sales",
            ...     to_agent="booking",
            ...     reason="User wants to book demo",
            ...     user_query="Quiero agendar una demo",
            ...     conversation_history=[...]
            ... )
        """
        logger.info(f"Preparing transfer: {from_agent} → {to_agent} (reason: {reason})")

        # Get memory blocks from source agent
        memory_blocks = self._get_relevant_memory_blocks(
            session_id, from_agent, to_agent
        )

        # Generate conversation summary
        conversation_summary = self._summarize_conversation(
            conversation_history, from_agent, to_agent, reason
        )

        # Build transfer context
        context = TransferContext(
            session_id=session_id,
            from_agent=from_agent,
            to_agent=to_agent,
            transfer_reason=reason,
            conversation_summary=conversation_summary,
            memory_blocks=memory_blocks,
            user_query=user_query,
        )

        logger.debug(
            f"Transfer prepared: {len(memory_blocks)} memory blocks, "
            f"summary length: {len(conversation_summary)}"
        )

        return context

    async def execute_transfer(self, context: TransferContext) -> int:
        """Execute agent transfer and record in database.

        Args:
            context: TransferContext prepared by prepare_transfer()

        Returns:
            Transfer record ID from database

        Example:
            >>> transfer_id = await handler.execute_transfer(context)
            >>> print(f"Transfer recorded: {transfer_id}")
        """
        logger.info(
            f"Executing transfer: {context.from_agent} → {context.to_agent} "
            f"(session={context.session_id[:8]})"
        )

        # Update session current_agent
        self.memory.update_session_agent(context.session_id, context.to_agent)

        # Record transfer in database
        transfer_id = self.memory.record_context_transfer(
            session_id=context.session_id,
            from_agent=context.from_agent,
            to_agent=context.to_agent,
            transfer_reason=context.transfer_reason,
            context_summary=context.conversation_summary,
            memory_blocks_transferred=len(context.memory_blocks),
            success=True,
        )

        logger.info(
            f"✅ Transfer executed successfully (id={transfer_id}, "
            f"blocks={len(context.memory_blocks)})"
        )

        return transfer_id

    def _get_relevant_memory_blocks(
        self, session_id: str, from_agent: str, to_agent: str
    ) -> list[dict[str, Any]]:
        """Get memory blocks relevant for transfer.

        Filters memory blocks by:
        1. Source agent scope (from_agent or 'shared')
        2. Priority threshold (>= 5)
        3. Not expired (TTL)

        Args:
            session_id: Session UUID
            from_agent: Source agent name
            to_agent: Target agent name

        Returns:
            List of relevant memory blocks
        """
        # Get blocks from source agent
        blocks_from_source = self.memory.get_active_memory_blocks(
            session_id, agent_scope=from_agent
        )

        # Get shared blocks
        blocks_shared = self.memory.get_active_memory_blocks(
            session_id, agent_scope="shared"
        )

        # Combine and deduplicate
        all_blocks = blocks_from_source + blocks_shared
        seen_ids = set()
        unique_blocks = []
        for block in all_blocks:
            if block["id"] not in seen_ids:
                seen_ids.add(block["id"])
                unique_blocks.append(block)

        # Filter by priority (>= 5)
        relevant_blocks = [b for b in unique_blocks if b.get("priority", 0) >= 5]

        logger.debug(
            f"Found {len(relevant_blocks)} relevant blocks "
            f"(from {len(all_blocks)} total)"
        )

        return relevant_blocks

    def _summarize_conversation(
        self,
        conversation_history: list[dict[str, Any]] | None,
        from_agent: str,
        to_agent: str,
        reason: str,
    ) -> str:
        """Summarize conversation for context transfer.

        Uses LLM to generate semantic summary if available,
        otherwise falls back to simple structured summary.

        Args:
            conversation_history: List of conversation turns
            from_agent: Source agent
            to_agent: Target agent
            reason: Transfer reason

        Returns:
            Conversation summary string
        """
        if not conversation_history:
            return f"Handoff from {from_agent} to {to_agent}: {reason}"

        # Try LLM-based summarization first
        try:
            import asyncio

            from utils.semantic_extractor import SemanticExtractor

            # Create extractor and generate summary
            extractor = SemanticExtractor()

            # Run async summarization in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, create task
                future = asyncio.ensure_future(
                    self._async_summarize(extractor, conversation_history, from_agent, to_agent, reason)
                )
                # Note: Can't await here in sync function, fall back to simple summary
                logger.debug("Event loop already running, using simple summary")
                raise RuntimeError("Cannot await in running loop")
            # Run in new loop
            summary = loop.run_until_complete(
                self._async_summarize(extractor, conversation_history, from_agent, to_agent, reason)
            )
            logger.debug(f"Generated LLM summary: {len(summary)} chars")
            return summary

        except Exception as e:
            logger.debug(f"LLM summarization failed, using simple summary: {e}")

        # Fallback: Simple summary
        recent_turns = conversation_history[-6:]  # Last 3 user+model pairs
        summary_parts = [f"Context transfer: {from_agent} → {to_agent}"]
        summary_parts.append(f"Reason: {reason}")

        if recent_turns:
            summary_parts.append("\nRecent conversation:")
            for turn in recent_turns:
                role = turn.get("role", "unknown")
                text = turn.get("message_text", turn.get("text", ""))[:100]
                summary_parts.append(f"  {role}: {text}...")

        summary = "\n".join(summary_parts)

        logger.debug(f"Generated simple summary: {len(summary)} chars")
        return summary

    async def _async_summarize(
        self,
        extractor: Any,
        conversation_history: list[dict[str, Any]],
        from_agent: str,
        to_agent: str,
        reason: str,
    ) -> str:
        """Async helper for LLM summarization.

        Args:
            extractor: SemanticExtractor instance
            conversation_history: Messages
            from_agent: Source agent
            to_agent: Target agent
            reason: Transfer reason

        Returns:
            Summary string
        """
        await extractor.initialize()
        summary = await extractor.summarize_conversation(
            messages=conversation_history, from_agent=from_agent, to_agent=to_agent, reason=reason
        )
        return summary

    def format_context_for_prompt(self, context: TransferContext) -> str:
        """Format transfer context for agent system prompt.

        Creates a formatted context string that can be injected into
        the target agent's system prompt.

        Args:
            context: TransferContext from prepare_transfer()

        Returns:
            Formatted context string for system prompt

        Example:
            >>> context_str = handler.format_context_for_prompt(context)
            >>> system_prompt = f"{base_prompt}\n\n{context_str}"
        """
        lines = [
            "=" * 70,
            "CONTEXT FROM PREVIOUS AGENT",
            "=" * 70,
            f"Previous agent: {context.from_agent}",
            f"Transfer reason: {context.transfer_reason}",
            "",
            "CONVERSATION SUMMARY:",
            context.conversation_summary,
        ]

        # Add memory blocks if present
        if context.memory_blocks:
            lines.append("")
            lines.append("IMPORTANT CONTEXT (Memory Blocks):")
            for block in context.memory_blocks:
                label = block.get("block_label", "unknown")
                value = block.get("block_value", "")
                priority = block.get("priority", 0)
                lines.append(f"  - [{label}] (priority={priority}): {value}")

        lines.append("")
        lines.append("CURRENT USER QUERY:")
        lines.append(context.user_query)
        lines.append("=" * 70)

        formatted = "\n".join(lines)
        logger.debug(f"Formatted context: {len(formatted)} chars")
        return formatted

    def get_transfer_statistics(self, session_id: str) -> dict[str, Any]:
        """Get transfer statistics for a session.

        Args:
            session_id: Session UUID

        Returns:
            Dictionary with transfer statistics

        Example:
            >>> stats = handler.get_transfer_statistics(session_id)
            >>> print(f"Total transfers: {stats['total_transfers']}")
        """
        stats = self.memory.get_session_statistics(session_id)
        if not stats:
            return {
                "total_transfers": 0,
                "transfer_details": [],
            }

        # Get detailed transfer history from database
        # TODO: Add query to get transfer details if needed

        return {
            "total_transfers": stats.get("context_transfers", 0),
            "session_duration_minutes": stats.get("session_duration_minutes", 0),
            "total_messages": stats.get("total_messages", 0),
            "memory_blocks": stats.get("memory_blocks", 0),
        }
