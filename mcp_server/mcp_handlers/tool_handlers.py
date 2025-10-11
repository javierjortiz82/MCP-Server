"""
MCP Tool Handlers
Async wrappers for MCP tools with Context support.
Separates MCP protocol handling from business logic.
"""

from typing import Any

from mcp.server.fastmcp import Context

from tools import fetch as fetch_tool
from tools import fuzzy_search as fuzzy_search_tool
from tools import ingest as ingest_tool
from tools import search as search_tool
from utils.logger import setup_logging

# Setup logger for tool handlers
logger = setup_logging("mcp_tool_handlers")

# Global mcp instance - will be injected from server.py
mcp = None


def init_tool_handlers(mcp_instance):
    """Initialize tool handlers with MCP instance."""
    global mcp
    mcp = mcp_instance
    register_tools()


def register_tools():
    """Register all MCP tools."""

    @mcp.tool()  # type: ignore[union-attr]
    async def fetch_by_sku(ctx: Context, sku: str) -> dict[str, Any] | None:
        """
        Fetch product details by exact SKU code (Stock Keeping Unit).

        ** WHEN TO USE THIS TOOL **:
        ✅ Client explicitly mentions a product code/SKU
        ✅ Query contains patterns like: "SKU XXX", "código YYY", "producto ZZZ-####"
        ✅ Client asks for "el producto [CODE]"

        ** EXAMPLES OF VALID USE **:
        - "quiero el TOY-0018"
        - "busco el producto COMP-0038"
        - "dame información del SKU HOME-0007"
        - "producto AUTO-0016"

        ** DON'T USE WHEN **:
        ❌ Client mentions product name without code ("busco laptop")
        ❌ Query is conceptual/need-based ("algo para limpiar")
        ❌ Query has typos in SKU (use fuzzy_search_smart instead)

        ** PERFORMANCE **: Ultra-fast (~9ms average) - Direct database lookup

        Args:
            ctx: MCP context for logging and progress
            sku: The exact product SKU to search for (case-sensitive)
                 Format examples: COMP-0009, TOY-0018, HOME-0007

        Returns:
            Product details dict if found, None otherwise
            Returns: {id, sku, name, description, category, brand, tags, color, size, price}
        """
        try:
            await ctx.info(f"Fetching product by SKU: {sku}")
            logger.debug(f"fetch_by_sku called with sku={sku}")
            result = fetch_tool.fetch_by_sku(sku)

            if result:
                await ctx.info(f"Successfully found product: {result.get('name', 'Unknown')}")
                logger.info(f"Product found for SKU {sku}: {result.get('name', 'Unknown')}")
            else:
                await ctx.info(f"No product found with SKU: {sku}")
                logger.warning(f"No product found for SKU: {sku}")

            return result
        except Exception as e:
            await ctx.debug(f"Error fetching by SKU {sku}: {e}")
            logger.error(f"Error in fetch_by_sku for SKU {sku}: {str(e)}", exc_info=True)
            raise

    @mcp.tool()  # type: ignore[union-attr]
    async def fetch_by_id(ctx: Context, product_id: int) -> dict[str, Any] | None:
        """
        Fetch product details by ID.

        Args:
            ctx: MCP context for logging and progress
            product_id: The product ID to search for

        Returns:
            Product details if found, None otherwise
        """
        try:
            await ctx.info(f"Fetching product by ID: {product_id}")
            result = fetch_tool.fetch_by_id(product_id)

            if result:
                await ctx.info(f"Successfully found product: {result.get('name', 'Unknown')}")
            else:
                await ctx.info(f"No product found with ID: {product_id}")

            return result
        except Exception as e:
            await ctx.debug(f"Error fetching by ID {product_id}: {e}")
            raise

    @mcp.tool()  # type: ignore[union-attr]
    async def search_products(ctx: Context, query: str, k: int = 5) -> dict[str, Any]:
        """
        Search products using semantic/conceptual search with AI embeddings (Gemini).

        ** WHEN TO USE THIS TOOL **:
        ✅ Client describes a NEED or BENEFIT (not a specific product name)
        ✅ Conceptual/abstract queries about PURPOSE or USE CASE
        ✅ Queries with patterns: "algo para...", "necesito para...", "quiero para..."
        ✅ Client describes what they want to ACHIEVE, not what they want to BUY

        ** EXAMPLES OF VALID USE **:
        - "algo para limpiar mi casa automáticamente"
        - "necesito mejorar mi computadora, quiero más velocidad"
        - "proteger mi celular de caídas"
        - "trabajar desde casa profesionalmente"
        - "hacer ejercicio en casa"
        - "algo para dormir mejor"
        - "iluminar mi habitación de forma inteligente"

        ** DON'T USE WHEN **:
        ❌ Client mentions specific product name ("busco laptop", "quiero teclado")
        ❌ Client asks about a category ("productos de gaming", "qué hay en hogar")
        ❌ Query has typos in product names (use fuzzy_search_smart)
        ❌ Client mentions exact SKU/code (use fetch_by_sku)

        ** HOW IT WORKS **:
        - Uses Google Gemini embedding-001 to convert query → 1536-dim vector
        - Compares semantic meaning (not exact words) with product embeddings
        - Finds products by WHAT THEY DO, not just what they're called
        - Example: "limpiar automáticamente" → finds robot vacuums (even without word "robot")

        ** PERFORMANCE **:
        - Average: ~490ms (slower than fuzzy_search_smart due to AI embedding generation)
        - Use when semantic understanding is critical, not for simple name lookups

        ** SUCCESS RATE **: 100% on conceptual queries (improved from 87% after fallback system)

        Args:
            ctx: MCP context for logging and progress
            query: Conceptual search query describing need/benefit/use case
            k: Number of results to return (default: 5, max: 10 recommended)

        Returns:
            List of product dicts ordered by semantic similarity
            Each product: {id, sku, name, description, category, brand, tags, color, size, price}
        """
        try:
            await ctx.info(f"Starting semantic search for: '{query}'")
            await ctx.report_progress(0, 1, "Initializing semantic search")

            results = search_tool.search_products(query, k)

            await ctx.report_progress(1, 1, f"Found {len(results)} results")
            await ctx.info(f"Semantic search completed: {len(results)} products found")

            # MCP protocol issue: wrap list in object
            return {"items": results, "count": len(results), "query": query}
        except Exception as e:
            await ctx.debug(f"Error in semantic search: {e}")
            raise

    @mcp.tool()  # type: ignore[union-attr]
    async def fuzzy_search_smart(
        ctx: Context,
        query: str,
        fields: list[str] | None = None,
        limit: int = 20,
        strict_threshold: float = 0.3,
        word_threshold: float = 0.4,
        fallback_threshold: float = 0.2,
        name_weight: float = 2.0,
        description_weight: float = 1.0,
        category_weight: float = 1.5,
        brand_weight: float = 1.0,
    ) -> dict[str, Any]:
        """
        Smart fuzzy text search with typo tolerance and category support (PostgreSQL pg_trgm).

        ** WHEN TO USE THIS TOOL **:
        ✅ Client mentions SPECIFIC PRODUCT NAME (even with typos)
        ✅ Client asks about PRODUCT CATEGORY ("qué hay en hogar", "productos de gaming")
        ✅ Query contains TYPOS or SPELLING ERRORS in product names
        ✅ Client wants to browse a category without specific needs

        ** EXAMPLES OF VALID USE **:
        Product name searches:
        - "busco un teclado mecánico"
        - "necesito auriculares inalámbricos"
        - "quiero una silla de oficina"
        - "auriculars de estudio" (with typo 'auriculars')
        - "roboot aspirador" (with typo 'roboot')
        - "chaquetta impermeable" (with typo 'chaquetta')

        Category searches (NEW - improved from 40% → 100% success rate):
        - "qué hay en hogar"
        - "productos de computación"
        - "tienes cosas de deportes"
        - "qué vendes de audio"
        - "muéstrame productos de cocina"
        - "productos para oficina"

        ** DON'T USE WHEN **:
        ❌ Query is conceptual/need-based ("algo para limpiar", "trabajar desde casa")
        ❌ Client mentions exact SKU code (use fetch_by_sku)
        ❌ Query describes benefits/purposes rather than product names (use search_products)

        ** HOW IT WORKS - 4-TIER FALLBACK STRATEGY **:
        1. Tier 1 (strict_threshold=0.3): Standard trigram similarity search
        2. Tier 2 (word_threshold=0.4): Word similarity for better partial/typo matching (weighted)
        2.5. Tier 2.5 (word_threshold=0.4): Token-based search (splits query into individual words)
        3. Tier 3 (fallback_threshold=0.2): Relaxed threshold as final attempt

        Returns results from first successful tier. Each result includes 'search_tier' field
        showing which tier succeeded: 'standard', 'word_similarity', 'token_based', or 'fallback'.

        ** TIER 2.5 EXPLANATION (NEW 2025-10-03) **:
        When multi-word queries fail in Tier 2 due to irrelevant terms diluting similarity:
        - Example: "sartenes electricos" → whole phrase similarity = 0.200 (fails threshold 0.4)
        - Tier 2.5 splits into tokens: ["sartenes", "electricos"]
        - Evaluates each token separately: "sartenes" → 0.444 ✅ (passes threshold)
        - Returns products matching ANY token with highest individual token score
        - This solves the problem where users add modifiers that don't exist in product names

        ** POSITION-BASED TOKEN WEIGHTING (NEW 2025-10-03) **:
        Tier 2.5 applies position-based weights to prioritize earlier tokens (usually nouns):
        - First token: weight 1.0 (highest priority - typically the main product name)
        - Second token: weight 0.5 (medium priority - typically a modifier)
        - Third+ tokens: weight 0.33, 0.25... (decreasing priority)
        - Formula: position_weight = 1.0 / (position + 1)
        - Example: "sartenes electricos" → "sartenes" (pos 0, weight 1.0) prioritized over
          "electricos" (pos 1, weight 0.5), even if "electricos" has higher raw similarity
        - This prevents irrelevant modifiers from outranking the main search term

        ** KEY IMPROVEMENT (2025-10-03) **:
        Now searches in name, description, AND category fields by default (was name/description only).
        This enabled 60-point improvement in category searches: 40% → 100% success rate.
        Category field is indexed with GIN pg_trgm for ultra-fast performance.

        ** WEIGHTED SCORING (NEW 2025-10-03) **:
        Tier 2 now uses weighted scoring to prioritize name matches over description matches.
        This fixes issues like "sartén eléctrico" returning "Escritorio Ajustable" (has "eléctrico"
        in description) before "Sartén Antiadherente" (has "sartén" in name).

        Default weights:
        - name: 2.0 (highest priority - product name is most important)
        - category: 1.5 (high priority - helps with category searches)
        - description: 1.0 (medium priority - supplementary info)
        - brand: 1.0 (medium priority - brand matching)

        ** PERFORMANCE **:
        - Average: ~10.8ms (45x faster than semantic search)
        - Uses PostgreSQL trigram similarity with normalized text (accent-insensitive)
        - Category queries: <12ms even with category field scan
        - Weighted scoring adds <1ms overhead

        ** ACCENT & CASE INSENSITIVE **:
        - "camara" matches "cámara"
        - "LAPTOP" matches "laptop"
        - Uses normalize_text() function: unaccent + lowercase

        Args:
            ctx: MCP context for logging and progress
            query: Product name, category, or search term (typos OK)
            fields: Fields to search (default: ['name', 'description', 'category'])
                   Available: 'name', 'description', 'brand', 'category'
            limit: Maximum results to return (default: 20, max recommended: 50)
                   Balances token efficiency (~800 tokens for 20 products) with UX
                   (enables 5 pages of 4 products). Follows API best practices 2025.
            strict_threshold: Tier 1 similarity threshold (default: 0.3 = 30% match)
            word_threshold: Tier 2 word similarity threshold (default: 0.4 = 40% match)
            fallback_threshold: Tier 3 relaxed threshold (default: 0.2 = 20% match)
            name_weight: Weight for name field (default: 2.0 - prioritize name matches)
            description_weight: Weight for description field (default: 1.0)
            category_weight: Weight for category field (default: 1.5)
            brand_weight: Weight for brand field (default: 1.0)

        Returns:
            List of product dicts with similarity scores and search_tier indicator
            Each product: {id, sku, name, description, category, brand, tags, color, size, price,
                          max_similarity: float, search_tier: str, [field]_similarity: float}
        """
        try:
            await ctx.info(f"Starting smart fuzzy search for: '{query}'")
            await ctx.report_progress(0, 3, "Initializing multi-tier search")

            # Default to searching in name, description, and category
            # This enables category-based searches like "qué hay en hogar"
            if fields is None:
                fields = ["name", "description", "category"]

            results = fuzzy_search_tool.fuzzy_search_smart(
                query,
                fields,
                limit,
                strict_threshold,
                word_threshold,
                fallback_threshold,
                name_weight,
                description_weight,
                category_weight,
                brand_weight,
            )

            await ctx.report_progress(3, 3, f"Search completed with {len(results)} results")

            # Log search tier information
            if results and len(results) > 0:
                tier = results[0].get("search_tier", "unknown")
                await ctx.info(f"Smart fuzzy search succeeded at tier: {tier}")
            else:
                await ctx.info("Smart fuzzy search found no results")

            # MCP protocol issue: returning a list directly only sends first item
            # Wrap in object to ensure all items are transmitted
            return {"items": results, "count": len(results), "query": query}
        except Exception as e:
            await ctx.debug(f"Error in smart fuzzy search: {e}")
            raise

    @mcp.tool()  # type: ignore[union-attr]
    async def ingest_products(ctx: Context, products: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Ingest new products into the database with progress reporting.

        Args:
            ctx: MCP context for logging and progress
            products: List of product dictionaries to ingest

        Returns:
            Ingestion status with success/error counts
        """
        try:
            total_products = len(products)
            await ctx.info(f"Starting ingestion of {total_products} products")
            await ctx.report_progress(0, total_products, "Starting product ingestion")

            result = ingest_tool.ingest_products(products)

            await ctx.report_progress(total_products, total_products, "Ingestion completed")
            await ctx.info(f"Successfully processed {total_products} products")

            return {"processed": result}
        except Exception as e:
            await ctx.debug(f"Error ingesting products: {e}")
            raise
