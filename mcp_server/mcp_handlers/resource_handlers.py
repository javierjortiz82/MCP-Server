"""
MCP Resource Handlers
Resource endpoints for MCP protocol.
Provides URI-based access to data resources.

Resources use the i18n system to provide content in both Spanish (ES)
and English (EN) based on user language preference.
"""

import json

from config import settings
from mcp_handlers import booking_handlers, product_handlers
from tools import fetch as fetch_tool
from utils.i18n import t, get_language
from utils.logger import setup_logging

logger = setup_logging("mcp_resource_handlers")

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

        Returns product information in the user's preferred language (ES/EN).

        Args:
            sku: Product SKU identifier

        Returns:
            Product information as formatted text in user's language
        """
        try:
            lang = get_language()
            product = fetch_tool.fetch_by_sku(sku)
            if product:
                # Build localized product information
                header = t("resource.product.sku.header", lang=lang)
                name = t("resource.product.sku.name", lang=lang, name=product.get("name", "N/A"))
                sku_line = t("resource.product.sku.sku", lang=lang, sku=product.get("sku", "N/A"))
                desc = t("resource.product.sku.description", lang=lang, description=product.get("description", "N/A"))
                cat = t("resource.product.sku.category", lang=lang, category=product.get("category", "N/A"))
                brand = t("resource.product.sku.brand", lang=lang, brand=product.get("brand", "N/A"))
                price = t("resource.product.sku.price", lang=lang, price=product.get("price", "N/A"))

                return f"{header}\n{name}\n{sku_line}\n{desc}\n{cat}\n{brand}\n{price}\n"

            not_found = t("resource.product.sku.not_found", lang=lang, sku=sku)
            return not_found
        except Exception as e:
            lang = get_language()
            logger.error(f"Error retrieving product {sku}: {str(e)}")
            return f"Error retrieving product {sku}: {str(e)}"

    @mcp.resource("database://stats")  # type: ignore[union-attr]
    def get_database_stats() -> str:
        """
        Resource providing database statistics.

        Returns database statistics in the user's preferred language (ES/EN).

        Returns:
            Database statistics as formatted text in user's language
        """
        try:
            from utils.db import fetchone

            lang = get_language()

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
                # Build localized statistics
                header = t("resource.database.stats.header", lang=lang)
                total = t("resource.database.stats.total_products", lang=lang,
                         total_products=result.get("total_products", 0))
                cats = t("resource.database.stats.categories", lang=lang,
                        categories=result.get("categories", 0))
                brands = t("resource.database.stats.brands", lang=lang,
                          brands=result.get("brands", 0))
                avg_p = t("resource.database.stats.avg_price", lang=lang,
                         avg_price=f"{result.get('avg_price', 0):.2f}")
                schema = t("resource.database.stats.schema", lang=lang,
                          schema=settings.SCHEMA_NAME)

                return f"{header}\n{total}\n{cats}\n{brands}\n{avg_p}\n{schema}\n"

            unable = t("resource.database.stats.unable_to_retrieve", lang=lang)
            return unable
        except Exception as e:
            logger.error(f"Error retrieving database stats: {str(e)}")
            return f"Error retrieving database stats: {str(e)}"

    @mcp.resource("tool-categories://products")  # type: ignore[union-attr]
    def get_product_tool_categories() -> str:
        """
        Resource providing list of product tool names for dynamic filtering.

        This resource enables clients to dynamically discover which tools belong
        to the product category without hardcoding tool lists in client code.

        Returns:
            JSON string containing list of product tool names
        """
        try:
            tool_names = product_handlers.get_product_tool_names()
            return json.dumps({"category": "products", "tools": tool_names, "count": len(tool_names)})
        except Exception as e:
            return json.dumps({"error": f"Error retrieving product tool names: {str(e)}"})

    @mcp.resource("tool-categories://bookings")  # type: ignore[union-attr]
    def get_booking_tool_categories() -> str:
        """
        Resource providing list of booking tool names for dynamic filtering.

        This resource enables clients to dynamically discover which tools belong
        to the booking category without hardcoding tool lists in client code.

        Returns:
            JSON string containing list of booking tool names
        """
        try:
            tool_names = booking_handlers.get_booking_tool_names()
            return json.dumps({"category": "bookings", "tools": tool_names, "count": len(tool_names)})
        except Exception as e:
            return json.dumps({"error": f"Error retrieving booking tool names: {str(e)}"})
