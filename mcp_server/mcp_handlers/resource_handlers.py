"""
MCP Resource Handlers
Resource endpoints for MCP protocol.
Provides URI-based access to data resources.
"""

from config import settings
from tools import fetch as fetch_tool

# Global mcp instance - will be injected from server.py
mcp = None


def init_resource_handlers(mcp_instance):
    """Initialize resource handlers with MCP instance."""
    global mcp
    mcp = mcp_instance
    register_resources()


def register_resources():
    """Register all MCP resources."""

    @mcp.resource("product://sku/{sku}")  # type: ignore[union-attr]
    def get_product_by_sku(sku: str) -> str:
        """
        Resource to access product data by SKU.

        Args:
            sku: Product SKU identifier

        Returns:
            Product information as formatted text
        """
        try:
            product = fetch_tool.fetch_by_sku(sku)
            if product:
                return f"""Product Information:
Name: {product.get("name", "N/A")}
SKU: {product.get("sku", "N/A")}
Description: {product.get("description", "N/A")}
Category: {product.get("category", "N/A")}
Brand: {product.get("brand", "N/A")}
Price: ${product.get("price", "N/A")}
"""
            return f"Product with SKU '{sku}' not found."
        except Exception as e:
            return f"Error retrieving product {sku}: {str(e)}"

    @mcp.resource("database://stats")  # type: ignore[union-attr]
    def get_database_stats() -> str:
        """
        Resource providing database statistics.

        Returns:
            Database statistics as formatted text
        """
        try:
            from utils.db import fetchone

            stats_query = f"""
            SELECT
                COUNT(*) as total_products,
                COUNT(DISTINCT category) as categories,
                COUNT(DISTINCT brand) as brands,
                AVG(price) as avg_price
            FROM {settings.SCHEMA_NAME}.products
            """
            result = fetchone(stats_query, ())
            if result:
                return f"""Database Statistics:
Total Products: {result.get("total_products", 0)}
Categories: {result.get("categories", 0)}
Brands: {result.get("brands", 0)}
Average Price: ${result.get("avg_price", 0):.2f}
Schema: {settings.SCHEMA_NAME}
"""
            return "Unable to retrieve database statistics."
        except Exception as e:
            return f"Error retrieving database stats: {str(e)}"
