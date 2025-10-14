"""Semantic Memory Extractor using LLM.

Automatically extracts important memory blocks from conversations using Gemini LLM.
Follows Memory Blocks pattern (Letta) for structured semantic memory.

Architecture:
    1. Analyze conversation turns (user + model messages)
    2. LLM identifies important facts, preferences, context
    3. Extract structured memory blocks with:
       - block_label: Category (user_preferences, product_interest, etc)
       - block_value: The actual memory content
       - priority: 0-10 score based on importance
       - agent_scope: Which agent(s) need this context

Best Practices:
    - Selective Extraction: Only extract high-priority facts (>= 5)
    - Structured Output: JSON format for parsing
    - Context Awareness: Consider conversation intent
    - Deduplication: Avoid storing redundant information

References:
    - Letta Memory Blocks: https://www.letta.com/blog/memory-blocks
    - Google Gemini: https://github.com/googleapis/python-genai

Author: Lab01-MCP Team
Created: 2025-10-12
Version: 1.0.0 (Fase 4)
"""

import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from config.settings import settings
from utils.logger import setup_logging

# Setup logger
logger = setup_logging("semantic_extractor")

# ============================================================================
# Pydantic Models
# ============================================================================


class ExtractedMemory(BaseModel):
    """Model for extracted memory block."""

    block_label: str = Field(description="Memory category")
    block_value: str = Field(description="Memory content")
    priority: int = Field(ge=0, le=10, description="Priority score 0-10")
    agent_scope: str = Field(default="shared", description="Agent scope")
    reasoning: str = Field(description="Why this memory is important")


class ExtractionResult(BaseModel):
    """Result from semantic extraction."""

    memories: list[ExtractedMemory] = Field(default_factory=list)
    total_extracted: int = Field(default=0)
    high_priority_count: int = Field(default=0)


# ============================================================================
# SemanticExtractor Class
# ============================================================================


class SemanticExtractor:
    """LLM-based semantic memory extractor.

    Uses Gemini to analyze conversations and extract important memory blocks
    automatically. Applies Memory Blocks pattern for structured context.

    Example:
        >>> extractor = SemanticExtractor()
        >>> await extractor.initialize()
        >>> result = await extractor.extract_from_conversation(
        ...     messages=[
        ...         {"role": "user", "text": "Busco laptop gaming"},
        ...         {"role": "model", "text": "Tenemos RTX 4060..."}
        ...     ],
        ...     agent_name="sales"
        ... )
        >>> for memory in result.memories:
        ...     print(f"{memory.block_label}: {memory.block_value}")
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-2.0-flash-exp",
    ):
        """Initialize SemanticExtractor.

        Args:
            api_key: Google API key (uses settings.GOOGLE_API_KEY if None)
            model_name: Gemini model for extraction (default: gemini-2.0-flash-exp)
        """
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model_name = model_name
        self.client: genai.Client | None = None

        logger.info(f"SemanticExtractor initialized (model={self.model_name})")

    async def initialize(self) -> None:
        """Initialize Gemini client.

        Must be called before extract_from_conversation().
        """
        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info("✅ SemanticExtractor Gemini client initialized")
        except Exception as e:
            logger.exception(f"Failed to initialize SemanticExtractor: {e}")
            raise RuntimeError(f"SemanticExtractor initialization failed: {e}") from e

    async def extract_from_conversation(
        self,
        messages: list[dict[str, Any]],
        agent_name: str = "general",
        context: str | None = None,
    ) -> ExtractionResult:
        """Extract semantic memory blocks from conversation.

        Analyzes conversation turns and identifies important facts to store.

        Args:
            messages: List of message dicts with 'role' and 'text' keys
            agent_name: Current agent name for scope determination
            context: Optional additional context for extraction

        Returns:
            ExtractionResult with extracted memories

        Example:
            >>> result = await extractor.extract_from_conversation(
            ...     messages=[
            ...         {"role": "user", "text": "Busco laptop gaming"},
            ...         {"role": "model", "text": "RTX 4060 disponible"}
            ...     ],
            ...     agent_name="sales"
            ... )
        """
        if not self.client:
            raise RuntimeError("SemanticExtractor not initialized - call initialize() first")

        if not messages:
            logger.debug("No messages to extract from")
            return ExtractionResult()

        try:
            # Build extraction prompt
            prompt = self._build_extraction_prompt(messages, agent_name, context)

            # Call Gemini for extraction
            logger.debug(f"Extracting semantic memory from {len(messages)} messages...")

            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temperature for consistent extraction
                    response_mime_type="application/json",
                ),
            )

            # Parse response
            if not response.candidates or not response.candidates[0].content.parts:
                logger.warning("Empty response from Gemini")
                return ExtractionResult()

            response_text = response.candidates[0].content.parts[0].text
            result = self._parse_extraction_response(response_text, agent_name)

            logger.info(
                f"✅ Extracted {result.total_extracted} memories "
                f"({result.high_priority_count} high-priority)"
            )
            return result

        except Exception as e:
            logger.exception(f"Failed to extract semantic memory: {e}")
            return ExtractionResult()  # Return empty result on error

    def _build_extraction_prompt(
        self,
        messages: list[dict[str, Any]],
        agent_name: str,
        context: str | None,
    ) -> str:
        """Build prompt for semantic extraction.

        Args:
            messages: Conversation messages
            agent_name: Current agent
            context: Optional context

        Returns:
            Extraction prompt string
        """
        # Format conversation
        conversation_text = "\n".join(
            [f"{msg['role']}: {msg.get('text', msg.get('message_text', ''))}" for msg in messages]
        )

        prompt = f"""Analiza esta conversación y extrae MEMORY BLOCKS importantes siguiendo el patrón de Letta.

CONVERSACIÓN:
{conversation_text}

AGENTE ACTUAL: {agent_name}
{f"CONTEXTO ADICIONAL: {context}" if context else ""}

INSTRUCCIONES:
1. Identifica hechos importantes sobre el usuario (preferencias, intereses, necesidades)
2. Extrae información relevante para futuras conversaciones
3. Asigna prioridad (0-10) basada en importancia
4. Determina el scope apropiado: 'shared', 'sales', 'booking', o 'general'
5. Solo extrae información con prioridad >= 5 (importante)

CATEGORÍAS (block_label):
- user_preferences: Preferencias generales del usuario
- product_interest: Productos específicos de interés
- budget_range: Presupuesto mencionado
- purchase_timeline: Timeline de compra
- technical_requirements: Requisitos técnicos específicos
- contact_preferences: Preferencias de contacto
- booking_preferences: Preferencias de reservas/citas
- previous_interactions: Interacciones previas importantes

FORMATO DE SALIDA (JSON):
{{
  "memories": [
    {{
      "block_label": "product_interest",
      "block_value": "Usuario busca laptop gaming con RTX 4060, 16GB RAM",
      "priority": 8,
      "agent_scope": "sales",
      "reasoning": "Interés específico en producto de alto valor"
    }}
  ]
}}

REGLAS IMPORTANTES:
- Solo incluir información NUEVA e IMPORTANTE
- Prioridad >= 5 solamente
- block_value debe ser descriptivo y específico
- reasoning debe explicar por qué es importante
- Si no hay información importante, retornar {{"memories": []}}

Analiza y extrae:"""

        return prompt

    def _parse_extraction_response(
        self, response_text: str, agent_name: str
    ) -> ExtractionResult:
        """Parse LLM extraction response.

        Args:
            response_text: JSON response from LLM
            agent_name: Current agent name

        Returns:
            ExtractionResult with parsed memories
        """
        try:
            # Parse JSON
            data = json.loads(response_text)
            memories_data = data.get("memories", [])

            # Validate and convert to ExtractedMemory objects
            memories = []
            for mem_data in memories_data:
                try:
                    memory = ExtractedMemory(**mem_data)
                    # Filter by priority threshold
                    if memory.priority >= 5:
                        memories.append(memory)
                    else:
                        logger.debug(
                            f"Filtered low-priority memory: {memory.block_label} (p={memory.priority})"
                        )
                except Exception as e:
                    logger.warning(f"Failed to parse memory: {e}")
                    continue

            # Calculate stats
            high_priority = sum(1 for m in memories if m.priority >= 7)

            result = ExtractionResult(
                memories=memories,
                total_extracted=len(memories),
                high_priority_count=high_priority,
            )

            logger.debug(
                f"Parsed {len(memories)} memories from LLM response "
                f"({high_priority} high-priority)"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {e}")
            logger.debug(f"Response was: {response_text[:200]}...")
            return ExtractionResult()
        except Exception as e:
            logger.exception(f"Error parsing extraction response: {e}")
            return ExtractionResult()

    async def summarize_conversation(
        self,
        messages: list[dict[str, Any]],
        from_agent: str,
        to_agent: str,
        reason: str,
    ) -> str:
        """Generate semantic summary of conversation for context transfer.

        Args:
            messages: Conversation messages
            from_agent: Source agent
            to_agent: Target agent
            reason: Transfer reason

        Returns:
            Semantic summary string

        Example:
            >>> summary = await extractor.summarize_conversation(
            ...     messages=[...],
            ...     from_agent="sales",
            ...     to_agent="booking",
            ...     reason="User wants to schedule demo"
            ... )
        """
        if not self.client:
            raise RuntimeError("SemanticExtractor not initialized")

        if not messages:
            return f"Handoff {from_agent} → {to_agent}: {reason}"

        try:
            # Format conversation
            conversation_text = "\n".join(
                [
                    f"{msg['role']}: {msg.get('text', msg.get('message_text', ''))}"
                    for msg in messages[-10:]  # Last 5 turns
                ]
            )

            prompt = f"""Genera un resumen CONCISO y SEMÁNTICO de esta conversación para transferencia de contexto entre agentes.

CONVERSACIÓN:
{conversation_text}

CONTEXTO DE TRANSFERENCIA:
- De: {from_agent}
- Hacia: {to_agent}
- Razón: {reason}

INSTRUCCIONES:
1. Resume los puntos clave de la conversación en 2-4 oraciones
2. Enfócate en información RELEVANTE para {to_agent}
3. Incluye preferencias, necesidades, y contexto importante
4. Usa formato claro y directo
5. Máximo 200 palabras

Genera el resumen:"""

            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.3),
            )

            if response.candidates and response.candidates[0].content.parts:
                summary = response.candidates[0].content.parts[0].text
                logger.debug(f"Generated summary: {len(summary)} chars")
                return summary.strip()
            return f"Handoff {from_agent} → {to_agent}: {reason}"

        except Exception as e:
            logger.exception(f"Failed to generate summary: {e}")
            return f"Handoff {from_agent} → {to_agent}: {reason}"
