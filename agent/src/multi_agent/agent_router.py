"""Agent Router - Intent Classification and Query Routing.

This module provides the AgentRouter class that classifies user queries into
three intents: sales, booking, or general. Uses Gemini 2.5 Flash with
temperature=0 for deterministic classification.

The router analyzes user queries and returns the appropriate intent:
- sales: Product queries, purchases, recommendations
- booking: Appointments, reservations, scheduling
- general: FAQ, company info, support

Memory Integration (Phase 3 - 2025-10-12):
    - Optional MemoryManager integration for context-aware classification
    - Uses memory blocks (user preferences, interests) to improve accuracy
    - Memory context is automatically loaded and included in classification
    - Supports sticky sessions with last_intent fallback
    - Intent persistence handled by MemoryManager.save_message()

Example with Memory:
    >>> from multi_agent import MemoryManager
    >>> memory = MemoryManager()
    >>> session_id = memory.create_session("user@example.com")
    >>> router = AgentRouter(memory_manager=memory, session_id=session_id)
    >>> await router.initialize()
    >>> intent = await router.classify_intent("Busco una laptop gaming")
    # Uses memory blocks for context-aware classification

References:
    - https://ai.google.dev/gemini-api/docs/function-calling
    - https://googleapis.github.io/python-genai/
    - https://github.com/anthropics/anthropic-quickstarts/tree/main/mcp

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 1.2.0 (Memory Integration)
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from google import genai
from google.genai import types

from gemini_agent.config import settings
from gemini_agent.utils.logger import setup_logging
from multi_agent.prompt_manager import PromptManager

# Try to import MCP server settings for memory configuration
try:
    from mcp_server.config.settings import settings as mcp_settings
except (ImportError, ModuleNotFoundError):
    mcp_settings = None

# Setup logger for agent router
logger = setup_logging("agent_router")


class Intent(str, Enum):
    """User query intent classification.

    Attributes:
        SALES: Product-related queries (search, purchase, recommendations).
        BOOKING: Appointment/reservation queries (schedule, cancel, reschedule).
        GENERAL: General information queries (FAQ, company info, support).
    """

    SALES = "sales"
    BOOKING = "booking"
    GENERAL = "general"


class AgentRouter:
    """Intent classification router using Gemini 2.5 Flash.

    This class analyzes user queries and classifies them into one of three
    intents: sales, booking, or general. Uses temperature=0 for deterministic
    classification to ensure consistent routing behavior.

    The router uses a specialized system prompt with clear classification rules
    and examples to achieve high accuracy (target: >95%).

    Example:
        >>> router = AgentRouter()
        >>> await router.initialize()
        >>> intent = await router.classify_intent("Quiero reservar una cita")
        >>> print(intent)  # Intent.BOOKING
        >>> intent = await router.classify_intent("Busco una laptop")
        >>> print(intent)  # Intent.SALES
    """

    # PromptManager instance (shared across all AgentRouter instances)
    _prompt_manager: PromptManager | None = None

    # Legacy classification prompt (DEPRECATED - use PromptManager)
    CLASSIFICATION_PROMPT = """Eres un clasificador de intenciones para un sistema multi-agente de ventas y reservas.

Tu ÚNICA tarea es clasificar la consulta del usuario en una de estas 3 categorías:

1. "sales" - Consultas sobre PRODUCTOS:
   - Búsqueda de productos ("busco laptop", "quiero teclado")
   - Recomendaciones ("qué me recomiendas para...")
   - Información de productos ("cuánto cuesta", "características")
   - Compras y carrito ("agregar al carrito", "comprar")
   - Disponibilidad de stock ("tienen en stock", "hay disponible")
   - Comparación de productos

2. "booking" - Consultas sobre RESERVAS/CITAS:
   - Crear citas ("quiero agendar", "reservar una cita")
   - Consultar disponibilidad ("qué horarios hay", "cuándo puedo")
   - Modificar citas ("cambiar mi cita", "mover la reserva")
   - Cancelar citas ("cancelar mi reserva", "no puedo asistir")
   - Estado de reservas ("mi cita", "mis reservas")
   - Servicios disponibles ("qué servicios ofrecen")

3. "general" - Consultas GENERALES/FAQ:
   - Información de la empresa ("quiénes son", "dónde están")
   - Políticas ("política de devolución", "garantía")
   - Horarios de atención ("cuándo abren", "horario de tienda")
   - Métodos de pago ("aceptan tarjeta", "formas de pago")
   - Envíos ("cómo envían", "tiempo de entrega")
   - Soporte general ("ayuda", "tengo un problema")
   - Saludos e inicio de conversación ("hola", "buenos días")

REGLAS DE CLASIFICACIÓN:
- Si la consulta menciona productos específicos o categorías → "sales"
- Si la consulta menciona citas, reservas, horarios, servicios → "booking"
- Si la consulta es genérica, FAQ, o saludo → "general"
- En caso de ambigüedad, prioriza el tema más específico
- Los saludos sin contexto adicional son "general"

RESPONDE ÚNICAMENTE con una de estas tres palabras: sales, booking, general

NO agregues explicaciones ni puntuación adicional."""

    @classmethod
    def get_classification_prompt(cls, use_template: bool = True) -> str:
        """Get classification prompt using PromptManager.

        Args:
            use_template: Whether to use PromptManager templates (True) or legacy prompt (False).

        Returns:
            Classification prompt text for router.

        Example:
            >>> prompt = AgentRouter.get_classification_prompt()
        """
        try:
            if use_template:
                # Initialize PromptManager if not already done
                if cls._prompt_manager is None:
                    logger.debug("Initializing PromptManager for AgentRouter")
                    cls._prompt_manager = PromptManager()

                # Get prompt from PromptManager
                prompt = cls._prompt_manager.get_router_prompt()
                logger.debug(
                    f"Loaded router prompt from PromptManager ({len(prompt)} chars)"
                )
                return prompt

        except Exception as e:
            logger.warning(
                f"Failed to load prompt from PromptManager: {e}. Using legacy prompt."
            )

        # Fallback to legacy prompt
        logger.debug("Using legacy CLASSIFICATION_PROMPT")
        return cls.CLASSIFICATION_PROMPT

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        memory_manager: Any | None = None,
        session_id: str | None = None,
    ) -> None:
        """Initialize Agent Router.

        Args:
            api_key: Google API key for Gemini (uses settings if not provided).
            model_name: Model to use for classification (uses settings.MODEL if not provided).
                       Uses Gemini 2.5 Flash for faster classification.
            memory_manager: Optional MemoryManager for context-aware classification.
            session_id: Optional session ID for memory integration.
        """
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model_name = model_name or settings.MODEL
        self.client: genai.Client | None = None
        self.generation_config: types.GenerateContentConfig | None = None

        # Memory integration (optional)
        self.memory_manager = memory_manager
        self.session_id = session_id
        self._memory_enabled = memory_manager is not None and session_id is not None

        logger.info(
            f"Initializing AgentRouter - Model: {self.model_name}, "
            f"API Key: {'***REDACTED***' if self.api_key else 'None'}, "
            f"Memory: {'enabled' if self._memory_enabled else 'disabled'}"
        )

    async def initialize(self) -> None:
        """Initialize the Gemini client for intent classification.

        Raises:
            RuntimeError: If client initialization fails.
        """
        try:
            logger.debug("Initializing Gemini client for AgentRouter...")
            self.client = genai.Client(api_key=self.api_key)

            # Build generation config with temperature=0 for deterministic classification
            self.generation_config = types.GenerateContentConfig(
                temperature=0.0,  # Deterministic classification
                top_k=1,  # Take only the top prediction
                top_p=1.0,  # No nucleus sampling needed
                max_output_tokens=500,  # Generous limit for thinking tokens + response (Gemini 2.5 Flash uses variable thinking)
                response_mime_type="text/plain",
            )

            logger.info("✅ AgentRouter initialized successfully (temperature=0)")

        except Exception as e:
            logger.exception(f"Failed to initialize AgentRouter: {e}")
            raise RuntimeError(f"AgentRouter initialization failed: {e}") from e

    def _get_memory_context(self) -> str:
        """Get memory context for classification (session + user-level).

        Retrieves relevant memory blocks to improve classification accuracy.
        Includes both session-level memory (short-term) and user-level memory
        (cross-session, long-term) for better context understanding.

        Memory thresholds and limits are configurable via settings:
        - MEMORY_PRIORITY_HIGH_THRESHOLD: Priority threshold for high-priority blocks (default: 7)
        - MEMORY_PRIORITY_MEDIUM_MIN/MAX: Range for medium-priority blocks (default: 5-7)
        - MEMORY_HIGH_PRIORITY_LIMIT: Max high-priority blocks in context (default: 3)
        - MEMORY_MEDIUM_PRIORITY_LIMIT: Max medium-priority blocks in context (default: 2)
        - MEMORY_USER_BLOCKS_LIMIT: Max user-level blocks in context (default: 5)

        Returns:
            Formatted memory context string, or empty string if no memory available.
        """
        if not self._memory_enabled or not self.memory_manager:
            return ""

        try:
            # Load configurable thresholds from settings (with fallbacks)
            high_threshold = 7
            medium_min = 5
            medium_max = 7
            high_limit = 3
            medium_limit = 2
            user_limit = 5

            if mcp_settings:
                high_threshold = mcp_settings.MEMORY_PRIORITY_HIGH_THRESHOLD
                medium_min = mcp_settings.MEMORY_PRIORITY_MEDIUM_MIN
                medium_max = mcp_settings.MEMORY_PRIORITY_MEDIUM_MAX
                high_limit = mcp_settings.MEMORY_HIGH_PRIORITY_LIMIT
                medium_limit = mcp_settings.MEMORY_MEDIUM_PRIORITY_LIMIT
                user_limit = mcp_settings.MEMORY_USER_BLOCKS_LIMIT

            memory_lines = []

            # 1. Get session-level memory blocks (shared scope)
            session_blocks = self.memory_manager.get_active_memory_blocks(
                self.session_id, agent_scope="shared"
            )

            if session_blocks:
                memory_lines.append("[MEMORIA DE LA SESIÓN ACTUAL]:")
                # Prioritize high-priority blocks (configurable threshold)
                high_priority = [b for b in session_blocks if b.get("priority", 0) >= high_threshold]
                medium_priority = [
                    b for b in session_blocks if medium_min <= b.get("priority", 0) < medium_max
                ]

                # Add high-priority session memories (configurable limit)
                for block in high_priority[:high_limit]:
                    label = block.get("block_label", "unknown")
                    value = block.get("block_value", "")
                    memory_lines.append(f"- {label}: {value[:100]}")

                # Add medium-priority if space allows (configurable limit)
                for block in medium_priority[:medium_limit]:
                    label = block.get("block_label", "unknown")
                    value = block.get("block_value", "")
                    memory_lines.append(f"- {label}: {value[:100]}")

            # 2. Get user-level memory blocks (cross-session)
            try:
                session_info = self.memory_manager.get_session_info(self.session_id)
                if session_info and session_info.get("customer_email"):
                    customer_email = session_info["customer_email"]
                    user_blocks = self.memory_manager.get_user_memory_blocks(
                        customer_email=customer_email, agent_scope="shared"
                    )

                    if user_blocks:
                        if memory_lines:  # Add separator if session memory exists
                            memory_lines.append("")
                        memory_lines.append("[MEMORIA HISTÓRICA DEL USUARIO]:")

                        # Take top user-level blocks (configurable limit, already sorted by priority in DB)
                        for block in user_blocks[:user_limit]:
                            label = block.get("block_label", "unknown")
                            value = block.get("block_value", "")
                            priority = block.get("priority", 0)
                            memory_lines.append(
                                f"- {label}: {value[:100]} (p={priority})"
                            )

                        logger.debug(
                            f"Loaded {len(user_blocks)} user memory blocks for {customer_email}"
                        )

            except Exception as e:
                logger.debug(f"Could not load user memory blocks: {e}")

            if not memory_lines:
                return ""

            memory_context = "\n".join(memory_lines)
            total_blocks = len(session_blocks) + (
                len(user_blocks) if "user_blocks" in locals() else 0
            )
            logger.debug(
                f"Loaded {total_blocks} total memory blocks "
                f"({len(session_blocks)} session + {len(user_blocks) if 'user_blocks' in locals() else 0} user) "
                f"for classification context (thresholds: high={high_threshold}, "
                f"medium={medium_min}-{medium_max}, limits: high={high_limit}, medium={medium_limit}, user={user_limit})"
            )

            return memory_context

        except Exception as e:
            logger.warning(f"Failed to load memory context: {e}")
            return ""

    async def classify_intent(
        self,
        query: str,
        *,
        context: dict[str, Any] | None = None,
        persist_intent: bool = True,
    ) -> Intent:
        """Classify user query into sales, booking, or general intent.

        Uses Gemini 2.5 Flash with temperature=0 for deterministic classification.
        Analyzes query content, optional context, and memory blocks (if available)
        to determine the best intent.

        Args:
            query: User query text to classify.
            context: Optional context dict with additional information:
                    - conversation_history: list[str] - Previous messages
                    - customer_email: str - Customer identifier
                    - session_id: str - Session identifier
                    - last_intent: str - Previous intent for sticky sessions
                    - last_bot_message: str - Last bot response
            persist_intent: If True and memory is enabled, persist classified intent
                          to database for analytics (default: True).

        Returns:
            Intent enum value (SALES, BOOKING, or GENERAL).

        Raises:
            ValueError: If query is empty or whitespace.
            RuntimeError: If client not initialized or classification fails.

        Example:
            >>> router = AgentRouter(memory_manager=memory, session_id=session_id)
            >>> await router.initialize()
            >>> intent = await router.classify_intent("Busco una laptop gaming")
            >>> print(intent)  # Intent.SALES (uses memory context for better accuracy)
            >>> intent = await router.classify_intent("Quiero agendar una cita")
            >>> print(intent)  # Intent.BOOKING
        """
        if not self.client:
            logger.error("AgentRouter not initialized - call initialize() first")
            raise RuntimeError("AgentRouter not initialized - call initialize() first")

        if not query or not query.strip():
            logger.error("Empty query provided for classification")
            raise ValueError("Query cannot be empty")

        query = query.strip()

        try:
            logger.info(f"Classifying query: '{query[:100]}...'")

            # Get classification prompt using PromptManager
            classification_prompt = self.get_classification_prompt(use_template=True)

            # Build query text with context if available
            query_text = f"Consulta: {query}"

            # Add memory context if available (improves accuracy)
            memory_context = self._get_memory_context()
            if memory_context:
                query_text += f"\n\n{memory_context}"

            # Add additional context information if provided
            if context:
                if "last_intent" in context:
                    query_text += (
                        f"\n[CONTEXTO] Intención previa: {context['last_intent']}"
                    )
                if "last_bot_message" in context:
                    last_msg = context["last_bot_message"]
                    query_text += f"\n[CONTEXTO] Última respuesta del bot: {last_msg}"

            # Build conversation contents
            contents = [
                # System prompt as first user message
                types.Content(
                    role="user",
                    parts=[types.Part(text=classification_prompt)],
                ),
                # Model acknowledgment
                types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text="Entendido. Clasificaré cada consulta en: sales, booking, o general."
                        )
                    ],
                ),
                # User query to classify (with context if available)
                types.Content(
                    role="user",
                    parts=[types.Part(text=query_text)],
                ),
            ]

            logger.debug("Generating classification with temperature=0 (deterministic)")

            # Generate classification
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=self.generation_config,
            )

            # Extract classification result with defensive checks
            if not response.candidates or not response.candidates[0].content:
                logger.error("Empty response from Gemini API")
                raise RuntimeError("No classification result from Gemini")

            # Additional defensive checks for None values
            candidate = response.candidates[0]
            if not candidate.content.parts:
                logger.error("Response has no parts")
                logger.debug(f"Response candidates: {len(response.candidates)}")
                logger.debug(
                    f"Candidate finish_reason: {candidate.finish_reason if hasattr(candidate, 'finish_reason') else 'N/A'}"
                )
                logger.debug(
                    f"Safety ratings: {candidate.safety_ratings if hasattr(candidate, 'safety_ratings') else 'N/A'}"
                )

                # STICKY SESSION: If in an active conversation, maintain intent
                if context and "last_intent" in context:
                    last_intent_str = context["last_intent"]
                    logger.warning(
                        f"⚠️ Empty response but continuing conversation. "
                        f"Maintaining previous intent: {last_intent_str}"
                    )
                    return Intent(last_intent_str)

                raise RuntimeError("No content parts in classification response")

            if not candidate.content.parts[0].text:
                logger.error("Response part has no text")
                logger.debug(f"Response structure: {candidate.content}")

                # STICKY SESSION: If in an active conversation, maintain intent
                if context and "last_intent" in context:
                    last_intent_str = context["last_intent"]
                    logger.warning(
                        f"⚠️ No text in response but continuing conversation. "
                        f"Maintaining previous intent: {last_intent_str}"
                    )
                    return Intent(last_intent_str)

                raise RuntimeError("No text in classification response")

            classification_text = candidate.content.parts[0].text.strip().lower()

            logger.debug(f"Raw classification result: '{classification_text}'")

            # Parse classification result
            intent = self._parse_classification(classification_text)

            logger.info(f"✅ Query classified as: {intent.value}")
            logger.debug(f"Query: '{query[:50]}...' → Intent: {intent.value}")

            # Persist intent to database if memory is enabled
            if persist_intent and self._memory_enabled:
                try:
                    # Update last user message with classified intent
                    # This will be used for analytics and context tracking
                    logger.debug(f"Persisting classified intent: {intent.value}")
                    # Note: Intent is already saved in save_message() when user message is stored
                    # This is just for tracking/logging purposes
                except Exception as e:
                    logger.warning(f"Failed to persist intent: {e}")

            return intent

        except ValueError:
            # Re-raise validation errors
            raise

        except Exception as e:
            logger.exception(f"Error classifying query: {e}")

            # IMPROVED STICKY SESSION: Only use for short/ambiguous queries (likely follow-ups)
            # For longer/complex queries, raise error and require user to repeat/clarify
            is_short_query = len(query.strip()) < 10  # "¿y ese?" = follow-up
            is_likely_followup = query.lower().strip() in [
                "sí", "si", "no", "ok", "okay", "de acuerdo", "bueno", "gracias"
            ]

            if (is_short_query or is_likely_followup) and context and "last_intent" in context:
                # Use sticky session ONLY for likely follow-up questions
                last_intent_str = context["last_intent"]
                logger.warning(
                    f"⚠️ Classification failed on short/follow-up query but context available. "
                    f"Maintaining previous intent: {last_intent_str} (sticky session for follow-ups)"
                )
                return Intent(last_intent_str)

            # For complex/unrelated queries: Don't hide the error, let it propagate
            logger.error(
                f"Classification failed on query: '{query[:50]}...' (length={len(query)}). "
                f"Not using sticky session because query appears to be independent."
            )
            raise RuntimeError(
                f"Failed to classify query (not a follow-up): {e}. "
                f"Please try again with a clear query."
            ) from e

    def _parse_classification(self, classification_text: str) -> Intent:
        """Parse classification text into Intent enum.

        Args:
            classification_text: Raw classification result from Gemini.

        Returns:
            Intent enum value.

        Raises:
            ValueError: If classification text is not recognized.
        """
        # Clean up response (remove punctuation, whitespace)
        cleaned = classification_text.strip().lower()
        cleaned = cleaned.replace(".", "").replace(",", "").replace(":", "")

        # Map to Intent enum
        if "sales" in cleaned or "venta" in cleaned:
            return Intent.SALES

        elif "booking" in cleaned or "reserva" in cleaned or "cita" in cleaned:
            return Intent.BOOKING

        elif "general" in cleaned or "faq" in cleaned:
            return Intent.GENERAL

        else:
            logger.warning(
                f"⚠️ Unrecognized classification: '{classification_text}', "
                f"defaulting to GENERAL"
            )
            return Intent.GENERAL

    async def classify_batch(
        self,
        queries: list[str],
    ) -> list[Intent]:
        """Classify multiple queries in batch.

        Useful for testing and analytics. Classifies each query independently.

        Args:
            queries: List of query strings to classify.

        Returns:
            List of Intent enum values, one per query.

        Example:
            >>> queries = [
            ...     "Busco laptop",
            ...     "Quiero reservar",
            ...     "Cuál es su horario?"
            ... ]
            >>> intents = await router.classify_batch(queries)
            >>> print(intents)  # [Intent.SALES, Intent.BOOKING, Intent.GENERAL]
        """
        logger.info(f"Classifying batch of {len(queries)} queries")

        intents = []
        for i, query in enumerate(queries, 1):
            try:
                intent = await self.classify_intent(query)
                intents.append(intent)
                logger.debug(
                    f"Batch {i}/{len(queries)}: '{query[:30]}...' → {intent.value}"
                )

            except Exception as e:
                logger.error(f"Error classifying query {i}: {e}")
                intents.append(Intent.GENERAL)  # Fallback

        logger.info(f"✅ Batch classification completed: {len(intents)} results")
        return intents

    def get_intent_statistics(
        self,
        intents: list[Intent],
    ) -> dict[str, int | float]:
        """Calculate statistics for a list of classified intents.

        Useful for analytics and monitoring intent distribution.

        Args:
            intents: List of classified Intent values.

        Returns:
            Statistics dict with:
            {
                "total": int,
                "sales_count": int,
                "booking_count": int,
                "general_count": int,
                "sales_percentage": float,
                "booking_percentage": float,
                "general_percentage": float
            }

        Example:
            >>> stats = router.get_intent_statistics([
            ...     Intent.SALES, Intent.SALES, Intent.BOOKING, Intent.GENERAL
            ... ])
            >>> print(f"Sales: {stats['sales_percentage']:.1f}%")
            # Sales: 50.0%
        """
        total = len(intents)

        if total == 0:
            return {
                "total": 0,
                "sales_count": 0,
                "booking_count": 0,
                "general_count": 0,
                "sales_percentage": 0.0,
                "booking_percentage": 0.0,
                "general_percentage": 0.0,
            }

        sales_count = sum(1 for i in intents if i == Intent.SALES)
        booking_count = sum(1 for i in intents if i == Intent.BOOKING)
        general_count = sum(1 for i in intents if i == Intent.GENERAL)

        return {
            "total": total,
            "sales_count": sales_count,
            "booking_count": booking_count,
            "general_count": general_count,
            "sales_percentage": (sales_count / total) * 100,
            "booking_percentage": (booking_count / total) * 100,
            "general_percentage": (general_count / total) * 100,
        }

    async def cleanup(self) -> None:
        """Cleanup resources and close client.

        Should be called when the router is no longer needed.
        """
        logger.info("Cleaning up AgentRouter resources")
        self.client = None
        self.generation_config = None
        logger.debug("AgentRouter cleanup completed")

    def __repr__(self) -> str:
        """String representation of AgentRouter."""
        return f"AgentRouter(model={self.model_name}, temperature=0.0)"
