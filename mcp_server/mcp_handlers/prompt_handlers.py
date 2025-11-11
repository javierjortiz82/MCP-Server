"""
MCP Prompt Handlers
AI assistant prompt templates for MCP protocol.
Provides structured prompts for different use cases.

Prompts are internationalized using the i18n system and support both
Spanish (ES) and English (EN) translations loaded from locales/*/prompts.json
"""

from utils.i18n import t, get_language
from utils.logger import setup_logging

logger = setup_logging("mcp_prompt_handlers")

# Global mcp instance - will be injected from server.py
mcp = None


def init_prompt_handlers(mcp_instance):
    """Initialize prompt handlers with MCP instance."""
    global mcp
    mcp = mcp_instance
    register_prompts()


def register_prompts():
    """Register all MCP prompts."""

    @mcp.prompt()  # type: ignore[union-attr]
    def search_assistant_prompt(query: str, context: str = "general") -> str:
        """
        Generate a prompt for AI assistants to help users with product searches.

        Uses i18n system to provide prompts in user's preferred language (ES/EN).

        Args:
            query: User's search query
            context: Search context (general, specific, troubleshooting)

        Returns:
            Formatted prompt for AI assistant in user's preferred language
        """
        lang = get_language()

        # Get base prompt template from i18n
        base_prompt = t("prompts.search_assistant.base", lang=lang, query=query, context=context)

        # Add context-specific prompt extensions
        if context == "troubleshooting":
            context_suffix = t("prompts.search_assistant.troubleshooting", lang=lang)
            base_prompt += context_suffix
        elif context == "specific":
            context_suffix = t("prompts.search_assistant.specific", lang=lang)
            base_prompt += context_suffix

        logger.debug(f"Generated search_assistant_prompt for {lang} with context={context}")
        return base_prompt

    @mcp.prompt()  # type: ignore[union-attr]
    def product_comparison_prompt(products: list[str]) -> str:
        """
        Generate a prompt for comparing multiple products.

        Uses i18n system to provide prompts in user's preferred language (ES/EN).

        Args:
            products: List of product identifiers (SKUs or names)

        Returns:
            Formatted prompt for product comparison in user's preferred language
        """
        lang = get_language()
        products_str = ", ".join(products)

        # Build comparison prompt from i18n components
        header = t("prompts.product_comparison.header", lang=lang)
        products_intro = t("prompts.product_comparison.products_intro", lang=lang, products=products_str)
        instructions = t("prompts.product_comparison.instructions", lang=lang)

        comparison_prompt = f"{header}\n\n{products_intro}{instructions}"

        logger.debug(f"Generated product_comparison_prompt for {lang} with {len(products)} products")
        return comparison_prompt
