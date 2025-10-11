"""
MCP Prompt Handlers
AI assistant prompt templates for MCP protocol.
Provides structured prompts for different use cases.
"""

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

        Args:
            query: User's search query
            context: Search context (general, specific, troubleshooting)

        Returns:
            Formatted prompt for AI assistant
        """
        base_prompt = f"""You are a helpful product search assistant with access to advanced search tools.

User Query: "{query}"
Context: {context}

Available MCP Tools:
- fuzzy_search_smart: Best for handling typos and partial matches (recommended)
- search_products: Semantic search using AI embeddings
- fetch_by_sku: Direct lookup by product code
- fetch_by_id: Direct lookup by ID

Database Schema: products table with fields: name, description, category, brand, price, tags, color, size

Instructions:
1. Understand the user's search intent
2. Choose the most appropriate search tool
3. Handle typos gracefully using fuzzy_search_smart
4. Provide detailed product information
5. Suggest alternatives if no exact matches found
"""

        if context == "troubleshooting":
            base_prompt += """

TROUBLESHOOTING MODE:
- Use fuzzy_search_smart with lower thresholds for broader results
- Suggest alternative search terms
- Check for common typos in product names
- Recommend browsing by category or brand
"""
        elif context == "specific":
            base_prompt += """

SPECIFIC SEARCH MODE:
- Focus on exact matches first using fetch_by_sku
- Use technical specifications when available
- Provide detailed product comparisons
- Include pricing and availability information
"""

        return base_prompt

    @mcp.prompt()  # type: ignore[union-attr]
    def product_comparison_prompt(products: list[str]) -> str:
        """
        Generate a prompt for comparing multiple products.

        Args:
            products: List of product identifiers (SKUs or names)

        Returns:
            Formatted prompt for product comparison
        """
        products_str = ", ".join(products)
        return f"""Product Comparison Analysis

Products to Compare: {products_str}

Using MCP tools, please:

1. **Data Collection**:
   - Use fetch_by_sku or search tools to gather complete product information
   - Collect specifications, pricing, and features for each product

2. **Comparison Framework**:
   - Feature comparison matrix
   - Price-to-value analysis
   - Pros and cons for each product
   - Target use case recommendations

3. **Decision Support**:
   - Highlight key differentiators
   - Identify best product for different user needs
   - Include availability and purchasing recommendations

4. **Quality Assurance**:
   - Verify all product information using MCP tools
   - Provide confidence levels for recommendations
   - Include alternative suggestions if needed

Focus on helping users make informed purchasing decisions based on their specific needs.
"""
