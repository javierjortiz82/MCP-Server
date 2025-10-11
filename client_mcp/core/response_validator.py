"""Response validation to prevent LLM hallucinations.

This module provides SKU validation and anti-hallucination mechanisms to ensure
the bot only mentions products that actually exist in tool results.
"""

import re
from typing import Any

from google.genai import types

from utils.logger import get_logger
from config.settings import settings

logger = get_logger("ResponseValidator", settings.LOG_LEVEL)


class ResponseValidator:
    """Validator to prevent LLM hallucinations in responses.

    This class implements code-based defenses against hallucinations by:
    - Extracting SKUs from responses
    - Validating against actual tool results
    - Regenerating responses with strict constraints if needed

    Attributes:
        conversation_history: Reference to conversation history
        gemini_client: Reference to Gemini client for regeneration
    """

    def __init__(self, conversation_history: list[types.Content], gemini_client: Any):
        """Initialize response validator.

        Args:
            conversation_history: Conversation history to search for valid SKUs
            gemini_client: GeminiAgent instance for regeneration
        """
        self.conversation_history = conversation_history
        self.gemini_client = gemini_client

    def validate_response_skus(
        self, response_text: str, user_query: str
    ) -> str | None:
        """Validate that all SKUs in response exist in tool results.

        This is a CODE-BASED defense against LLM hallucinations.

        Args:
            response_text: Generated response from model
            user_query: Original user query (to retrieve tool results)

        Returns:
            response_text if valid, None if hallucinated SKUs detected

        Example:
            >>> validator = ResponseValidator(history, client)
            >>> response = "Product: LAPTOP-001"
            >>> validated = validator.validate_response_skus(response, "laptops")
            >>> validated is not None
            True
        """
        # Extract ONLY SKUs that appear after "SKU:" label
        sku_pattern = r"SKU:\s*([A-Z]{2,10}-\d{1,6}(?:-[A-Z]{1,5})?)"
        mentioned_skus = set(re.findall(sku_pattern, response_text))

        if not mentioned_skus:
            # No SKUs mentioned - response is safe
            logger.debug("✅ No SKUs found in response - safe")
            return response_text

        logger.debug(f"🔍 Found SKUs in response: {mentioned_skus}")

        # Get valid SKUs from last tool execution
        valid_skus = self._get_valid_skus_from_tool_results()

        if valid_skus is None:
            # No tool was executed - allow response
            logger.debug("ℹ️ No tool results to validate against - allowing response")
            return response_text

        # Check if all mentioned SKUs are valid
        invalid_skus = mentioned_skus - valid_skus

        if invalid_skus:
            logger.error(
                f"🚫 HALLUCINATION DETECTED! Invalid SKUs: {invalid_skus}\n"
                f"   Valid SKUs from tool: {valid_skus}\n"
                f"   Response preview: {response_text[:200]}..."
            )
            return None  # Reject response

        logger.success(f"✅ All SKUs validated: {mentioned_skus}")
        return response_text

    def _get_valid_skus_from_tool_results(self) -> set[str] | None:
        """Extract valid SKUs from last tool execution result.

        Returns:
            Set of valid SKUs from tool result, or None if no tool was executed
        """
        valid_skus = set()

        # Look for function_response parts in recent history
        for content in reversed(self.conversation_history[-10:]):
            if content.role == "user":  # Function responses are added as "user" role
                for part in content.parts:
                    if hasattr(part, "function_response") and part.function_response:
                        response_data = part.function_response.response

                        # Handle different response structures
                        if isinstance(response_data, dict):
                            # Structure: {"product": {"sku": "...", ...}}
                            if "product" in response_data:
                                product = response_data["product"]
                                if isinstance(product, dict) and "sku" in product:
                                    valid_skus.add(product["sku"])

                            # Structure: {"items": [{"sku": "...", ...}, ...]}
                            if "items" in response_data and isinstance(
                                response_data["items"], list
                            ):
                                for item in response_data["items"]:
                                    if isinstance(item, dict) and "sku" in item:
                                        valid_skus.add(item["sku"])

                            # Structure: {"products": [{"sku": "...", ...}, ...]}
                            if "products" in response_data and isinstance(
                                response_data["products"], list
                            ):
                                for item in response_data["products"]:
                                    if isinstance(item, dict) and "sku" in item:
                                        valid_skus.add(item["sku"])

                            # Structure: {"sku": "...", "name": "...", ...}
                            if "sku" in response_data:
                                valid_skus.add(response_data["sku"])

        if valid_skus:
            logger.debug(f"📋 Valid SKUs from tool: {valid_skus}")
            return valid_skus
        else:
            # No products found (0 results) - return empty set (not None)
            logger.debug("📋 Tool returned 0 products - empty valid SKU set")
            return set()

    async def regenerate_without_hallucinations(
        self, user_query: str
    ) -> str:
        """Regenerate response with strict constraint after hallucination detected.

        Args:
            user_query: Original user query

        Returns:
            Safe response without hallucinations
        """
        # Get tool results count
        valid_skus = self._get_valid_skus_from_tool_results()

        if valid_skus is not None and len(valid_skus) == 0:
            # Tool returned 0 results - force simple "no results" message
            return (
                f"No encontré productos que coincidan con '{user_query}' en el inventario actual.\n\n"
                "¿Te gustaría buscar algo relacionado o puedo ayudarte con otro tipo de producto?"
            )

        # Tool had results but model hallucinated - add strict constraint
        strict_instruction = types.Content(
            role="user",
            parts=[
                types.Part(
                    text=(
                        "⚠️ VALIDACIÓN CRÍTICA: Tu respuesta anterior mencionó SKUs "
                        "que NO EXISTEN en la herramienta.\n\n"
                        f"SKUs VÁLIDOS de la herramienta: {list(valid_skus) if valid_skus else 'NINGUNO'}\n\n"
                        "REGLAS OBLIGATORIAS:\n"
                        '1. SOLO muestra productos del array tool_response["products"]\n'
                        '2. El SKU REAL está en products[i]["sku"] - NO en products[i]["name"]\n'
                        '3. NUNCA uses códigos del nombre como SKUs\n'
                        "4. Si no hay productos → Di 'No encontré productos'\n"
                        "5. VERIFICA cada SKU contra la lista de SKUs válidos arriba\n\n"
                        "Regenera tu respuesta mostrando SOLO productos con SKUs de la lista válida."
                    )
                )
            ],
        )

        self.conversation_history.append(strict_instruction)

        # Regenerate
        response = await self.gemini_client.generate_with_retry(
            self.conversation_history
        )

        # Extract text
        if hasattr(response, "candidates") and response.candidates:
            parts = response.candidates[0].content.parts
            text_parts = [part.text for part in parts if hasattr(part, "text") and part.text]
            if text_parts:
                regenerated_text = " ".join(text_parts)

                # Validate again (ONE retry only to prevent infinite loop)
                final_validated = self.validate_response_skus(regenerated_text, user_query)
                if final_validated is None:
                    # Still hallucinating after retry - force safe fallback
                    logger.error("🚫 Model still hallucinating after retry - using fallback")
                    return (
                        "Encontré algunos productos, pero estoy teniendo dificultades técnicas para "
                        "mostrártelos correctamente. Por favor, reformula tu búsqueda o contacta con soporte."
                    )

                return final_validated

        # Fallback if regeneration failed
        return "No pude generar una respuesta válida. Por favor, intenta reformular tu consulta."

    @staticmethod
    def clean_json_artifacts(text: str) -> str:
        """Clean JSON escape artifacts from LLM responses.

        Removes escaped characters that sometimes appear when LLM processes
        JSON data (e.g., \\" becomes ", \\\\ becomes \\).

        Args:
            text: Raw text response from LLM

        Returns:
            Cleaned text with unescaped characters

        Example:
            >>> ResponseValidator.clean_json_artifacts('Name: \\"Product\\"')
            'Name: "Product"'
        """
        if not text:
            return text

        # Common JSON escapes to clean
        replacements = {
            '\\"': '"',  # Escaped quotes
            "\\\\": "\\",  # Escaped backslashes
            "\\n": "\n",  # Keep newlines as actual newlines
            "\\t": "\t",  # Keep tabs as actual tabs
        }

        cleaned = text
        for escaped, unescaped in replacements.items():
            cleaned = cleaned.replace(escaped, unescaped)

        return cleaned

    @staticmethod
    def remove_generated_debug_info(text: str) -> str:
        """Remove DEBUG INFO sections generated by Gemini (hallucination).

        Gemini learns the DEBUG format from conversation history and tries
        to generate it. This method removes such hallucinations.

        Args:
            text: Response text that may contain generated DEBUG INFO

        Returns:
            Text with DEBUG INFO removed

        Example:
            >>> text = "Product info\\n---\\n🔧 **DEBUG INFO**\\n..."
            >>> ResponseValidator.remove_generated_debug_info(text)
            'Product info'
        """
        if text and "🔧 **DEBUG INFO**" in text:
            debug_start = text.find("\n---\n🔧 **DEBUG INFO**")
            if debug_start != -1:
                text = text[:debug_start]
                logger.debug("🧹 Removed Gemini-generated DEBUG INFO (hallucination)")

        return text
