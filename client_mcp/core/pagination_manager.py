"""Pagination Manager - Client-side pagination for search results.

This module implements pagination following SOLID principles:
- Single Responsibility: Only handles pagination logic
- Dependency Inversion: Bot depends on this abstraction
- Open/Closed: Extensible for new detection patterns

Since MCP server doesn't support offset/page parameters, we implement
client-side pagination by fetching more results upfront and showing them
in chunks when the user requests "more".

Persistence:
- Hybrid strategy: Memory (fast) + PostgreSQL (persistent)
- Contexts survive bot restarts when persistence is enabled
- Graceful degradation if database is unavailable
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from core.pagination_db import PaginationDB

logger = logging.getLogger(__name__)


@dataclass
class SearchContext:
    """Context for client-side pagination of search results.

    Attributes:
        category: Category name (e.g., "bolsos", "computadora")
        tool: Tool used ("search_products" or "fuzzy_search_smart")
        query: Original query string
        page_size: Products per page
        current_page: Current page number (0-indexed)
        all_results: All products from initial fetch
        total_count: Total products fetched
    """

    category: str
    tool: str
    query: str
    page_size: int
    current_page: int
    all_results: list[dict[str, Any]]
    total_count: int

    @property
    def has_more(self) -> bool:
        """Check if there are more results to show."""
        next_start = (self.current_page + 1) * self.page_size
        return next_start < len(self.all_results)

    def get_current_page(self) -> list[dict[str, Any]]:
        """Get products for current page."""
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.all_results[start:end]

    def get_next_page(self) -> list[dict[str, Any]] | None:
        """Advance to next page and return products."""
        if not self.has_more:
            return None
        self.current_page += 1
        return self.get_current_page()

    def remaining_count(self) -> int:
        """Count of products not yet shown."""
        shown = (self.current_page + 1) * self.page_size
        return max(0, len(self.all_results) - shown)


class PaginationManager:
    """Manages client-side pagination for search results.

    This class follows the Single Responsibility Principle by focusing
    solely on pagination logic, separate from the main bot logic.

    Example:
        manager = PaginationManager()

        # Save search results for pagination
        manager.save_search("bolsos", "search_products", "bolsos",
                          products_list, page_size=4)

        # Check if user wants more
        if manager.is_show_more_request("muéstrame más"):
            products = manager.get_next_page("bolsos")
    """

    # Patterns that indicate user wants to see more results
    SHOW_MORE_PATTERNS = [
        "más",
        "more",
        "otras opciones",
        "other options",
        "qué más",
        "what else",
        "ver más",
        "see more",
        "dame más",
        "show me more",
        "muéstrame más",
        "siguiente",
        "next",
        "continuar",
        "continue",
    ]

    def __init__(self, session_id: UUID | None = None):
        """Initialize pagination manager.

        Args:
            session_id: Optional UUID for session tracking (enables persistence).
                       If None, only in-memory pagination is used.
        """
        self._contexts: dict[str, SearchContext] = {}
        self._session_id = session_id
        self._db = PaginationDB() if session_id else None

        if self._db and self._db.is_enabled and session_id:
            logger.info("💾 Pagination persistence enabled for session %s", session_id)

    def save_search(
        self,
        category: str,
        tool: str,
        query: str,
        results: list[dict[str, Any]],
        page_size: int = 4,
    ) -> None:
        """Save search results for pagination.

        Hybrid strategy:
        1. Always save to memory (fast access)
        2. If persistence enabled, also save to PostgreSQL (survives restarts)

        Args:
            category: Category identifier (e.g., "bolsos")
            tool: Tool name used for search
            query: Original query string
            results: Complete list of products
            page_size: Number of products to show per page
        """
        # Save to memory (always)
        context = SearchContext(
            category=category,
            tool=tool,
            query=query,
            page_size=page_size,
            current_page=0,  # Start at first page
            all_results=results,
            total_count=len(results),
        )
        self._contexts[category] = context

        # Save to database (if persistence enabled)
        if self._db and self._db.is_enabled and self._session_id:
            self._db.save_context(
                session_id=self._session_id,
                category=category,
                tool_name=tool,
                query=query,
                products=results,
                current_page=0,
                page_size=page_size,
            )

    def is_show_more_request(self, message: str) -> bool:
        """Detect if user is asking to see more results.

        Args:
            message: User's message

        Returns:
            True if message matches "show more" patterns
        """
        message_lower = message.lower()
        return any(pattern in message_lower for pattern in self.SHOW_MORE_PATTERNS)

    def detect_category(self, message: str) -> str | None:
        """Detect which category the user wants more results for.

        Args:
            message: User's message

        Returns:
            Category name if detected, None otherwise
        """
        message_lower = message.lower()

        # Check if category is mentioned in message
        for category in self._contexts:
            if category.lower() in message_lower:
                return category

        # If only one category in context, assume that one
        if len(self._contexts) == 1:
            return list(self._contexts.keys())[0]

        return None

    def has_context(self, category: str) -> bool:
        """Check if we have pagination context for a category.

        Hybrid strategy:
        1. Check memory first (fast)
        2. If not in memory and persistence enabled, try loading from DB

        Args:
            category: Category name

        Returns:
            True if context exists (in memory or database)
        """
        # Check memory first
        if category in self._contexts:
            return True

        # Try loading from database if not in memory
        if self._db and self._db.is_enabled and self._session_id:
            loaded = self._load_from_db(category)
            return loaded is not None

        return False

    def _load_from_db(self, category: str) -> SearchContext | None:
        """Load pagination context from database.

        Args:
            category: Category name

        Returns:
            SearchContext if found in database, None otherwise
        """
        if not self._db or not self._db.is_enabled or not self._session_id:
            return None

        db_context = self._db.load_context(self._session_id, category)
        if not db_context:
            return None

        # Reconstruct SearchContext from database data
        context = SearchContext(
            category=category,
            tool=db_context["tool_name"],
            query=db_context["query"],
            page_size=db_context["page_size"],
            current_page=db_context["current_page"],
            all_results=db_context["products"],
            total_count=db_context["total_items"],
        )

        # Cache in memory for fast subsequent access
        self._contexts[category] = context
        logger.debug("📂 Loaded pagination context from DB: %s", category)
        return context

    def has_more_results(self, category: str) -> bool:
        """Check if category has more results to show.

        Args:
            category: Category name

        Returns:
            True if more results available
        """
        if category not in self._contexts:
            return False
        return self._contexts[category].has_more

    def get_next_page(self, category: str) -> list[dict[str, Any]] | None:
        """Get next page of results for a category.

        Args:
            category: Category name

        Returns:
            List of products for next page, or None if no more
        """
        # Try loading from DB if not in memory
        if category not in self._contexts:
            self._load_from_db(category)

        if category not in self._contexts:
            return None

        # Get next page
        next_page = self._contexts[category].get_next_page()

        # Update database with new current_page
        if next_page and self._db and self._db.is_enabled and self._session_id:
            context = self._contexts[category]
            self._db.save_context(
                session_id=self._session_id,
                category=category,
                tool_name=context.tool,
                query=context.query,
                products=context.all_results,
                current_page=context.current_page,
                page_size=context.page_size,
            )

        return next_page

    def get_current_page(self, category: str) -> list[dict[str, Any]] | None:
        """Get current page of results for a category.

        Args:
            category: Category name

        Returns:
            List of products for current page, or None if not found
        """
        if category not in self._contexts:
            return None
        return self._contexts[category].get_current_page()

    def get_remaining_count(self, category: str) -> int:
        """Get count of remaining (not yet shown) products.

        Args:
            category: Category name

        Returns:
            Number of remaining products, 0 if none or not found
        """
        if category not in self._contexts:
            return 0
        return self._contexts[category].remaining_count()

    def get_total_count(self, category: str) -> int:
        """Get total count of products for category.

        Args:
            category: Category name

        Returns:
            Total products, 0 if not found
        """
        if category not in self._contexts:
            return 0
        return self._contexts[category].total_count

    def get_all_categories(self) -> list[str]:
        """Get list of all categories with pagination context.

        Returns:
            List of category names
        """
        return list(self._contexts.keys())

    def clear_context(self, category: str | None = None) -> None:
        """Clear pagination context.

        Args:
            category: Specific category to clear, or None to clear all
        """
        # Clear from memory
        if category:
            self._contexts.pop(category, None)
        else:
            self._contexts.clear()

        # Clear from database
        if self._db and self._db.is_enabled and self._session_id:
            if category:
                self._db.delete_context(self._session_id, category)
            else:
                self._db.cleanup_session(self._session_id)

    def cleanup(self) -> None:
        """Cleanup resources (close database connections).

        Should be called when shutting down the bot.
        """
        if self._db:
            self._db.close()
            logger.debug("🔌 Pagination manager cleanup complete")

    def extract_category_from_query(self, query: str) -> str:
        """Extract category capturing user search intent.

        Extracts up to 4 significant words to better capture the search intent
        while keeping the category concise and meaningful.

        Args:
            query: Search query

        Returns:
            Category name (up to 4 meaningful words)

        Examples:
            >>> extract_category_from_query("laptop gaming barato estudiante")
            "laptop gaming barato estudiante"
            >>> extract_category_from_query("bolsos de mujer para oficina")
            "bolsos mujer oficina"
            >>> extract_category_from_query("mouse inalámbrico gaming RGB")
            "mouse inalámbrico gaming rgb"
        """
        # Extract first meaningful word(s) as category
        # Heuristic: take first 4 words to capture intent (product + type + features)
        words = query.strip().lower().split()
        if not words:
            return "general"

        # Filter out common words that don't add intent
        stopwords = {"de", "para", "con", "en", "el", "la", "los", "las", "un", "una", "y", "a"}
        meaningful_words = [w for w in words if w not in stopwords]

        if not meaningful_words:
            return words[0]

        # Return first 4 meaningful words to capture full intent
        return " ".join(meaningful_words[:4])

    @staticmethod
    def format_pagination_response(
        category: str,
        products: list[dict[str, Any]],
        remaining: int,
        spanish_mode: bool = True,
    ) -> str:
        """Format pagination response with products.

        Args:
            category: Category name
            products: List of products to display
            remaining: Number of remaining products
            spanish_mode: Use Spanish (True) or English (False)

        Returns:
            Formatted pagination response string

        Example:
            >>> products = [{"name": "Product 1", "description": "Desc", "sku": "SKU1",
            ...             "brand": "Brand", "price": 100.0}]
            >>> response = PaginationManager.format_pagination_response(
            ...     "laptops", products, 5, spanish_mode=True
            ... )
            >>> "laptops" in response
            True
        """
        response_lines = []

        # Header
        if spanish_mode:
            response_lines.append(f"🔍 Aquí están más opciones de {category}:\n")
        else:
            response_lines.append(f"🔍 Here are more options for {category}:\n")

        # Format each product
        for idx, product in enumerate(products, 1):
            name = product.get("name", "Sin nombre")
            description = product.get("description", "Sin descripción")
            sku = product.get("sku", "N/A")
            brand = product.get("brand", "N/A")
            price = product.get("price", 0.0)

            response_lines.append(f"{idx}. 🛍️ **{name}**")
            response_lines.append(f"   📝 {description}")
            response_lines.append(f"   🏷️ SKU: {sku}")

            if spanish_mode:
                response_lines.append(f"   🏭 Marca: {brand}")
                response_lines.append(f"   💰 Precio: ${price:.2f}\n")
            else:
                response_lines.append(f"   🏭 Brand: {brand}")
                response_lines.append(f"   💰 Price: ${price:.2f}\n")

        # Footer with remaining count
        if remaining > 0:
            if spanish_mode:
                response_lines.append(f"\n💡 Quedan {remaining} productos más. Escribe 'más' para verlos.")
            else:
                response_lines.append(f"\n💡 {remaining} more products available. Type 'more' to see them.")
        else:
            if spanish_mode:
                response_lines.append("\n✅ Esos son todos los resultados disponibles.")
            else:
                response_lines.append("\n✅ That's all the available results.")

        return "\n".join(response_lines)
