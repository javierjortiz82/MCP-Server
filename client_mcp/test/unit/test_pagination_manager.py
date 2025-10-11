"""Unit tests for core/pagination_manager.py."""

import pytest
from core.pagination_manager import PaginationManager, SearchContext


class TestSearchContext:
    """Test SearchContext dataclass."""

    def test_search_context_initialization(self):
        """Test SearchContext initializes correctly."""
        products = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]
        context = SearchContext(
            category="laptops",
            tool="search_products",
            query="laptops gaming",
            page_size=2,
            current_page=0,
            all_results=products,
            total_count=5
        )

        assert context.category == "laptops"
        assert context.tool == "search_products"
        assert context.query == "laptops gaming"
        assert context.page_size == 2
        assert context.current_page == 0
        assert len(context.all_results) == 5
        assert context.total_count == 5

    def test_has_more_true(self):
        """Test has_more returns True when more results available."""
        products = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
        context = SearchContext(
            category="test",
            tool="search_products",
            query="test",
            page_size=2,
            current_page=0,  # Showing products 0-1, have 2-3 left
            all_results=products,
            total_count=4
        )

        assert context.has_more is True

    def test_has_more_false(self):
        """Test has_more returns False when no more results."""
        products = [{"id": 1}, {"id": 2}, {"id": 3}]
        context = SearchContext(
            category="test",
            tool="search_products",
            query="test",
            page_size=2,
            current_page=1,  # Showing products 2, no more left
            all_results=products,
            total_count=3
        )

        assert context.has_more is False

    def test_get_current_page(self):
        """Test get_current_page returns correct products."""
        products = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
        context = SearchContext(
            category="test",
            tool="search_products",
            query="test",
            page_size=2,
            current_page=1,  # Second page
            all_results=products,
            total_count=4
        )

        page = context.get_current_page()
        assert len(page) == 2
        assert page[0]["id"] == 3
        assert page[1]["id"] == 4

    def test_get_next_page_success(self):
        """Test get_next_page advances and returns products."""
        products = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
        context = SearchContext(
            category="test",
            tool="search_products",
            query="test",
            page_size=2,
            current_page=0,
            all_results=products,
            total_count=4
        )

        next_page = context.get_next_page()
        assert next_page is not None
        assert len(next_page) == 2
        assert next_page[0]["id"] == 3
        assert next_page[1]["id"] == 4
        assert context.current_page == 1  # Page advanced

    def test_get_next_page_no_more(self):
        """Test get_next_page returns None when no more pages."""
        products = [{"id": 1}, {"id": 2}]
        context = SearchContext(
            category="test",
            tool="search_products",
            query="test",
            page_size=2,
            current_page=0,
            all_results=products,
            total_count=2
        )

        next_page = context.get_next_page()
        assert next_page is None
        assert context.current_page == 0  # Page not advanced

    def test_remaining_count(self):
        """Test remaining_count calculates correctly."""
        products = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]
        context = SearchContext(
            category="test",
            tool="search_products",
            query="test",
            page_size=2,
            current_page=0,  # Shown: 2, Remaining: 3
            all_results=products,
            total_count=5
        )

        assert context.remaining_count() == 3

    def test_remaining_count_zero(self):
        """Test remaining_count returns 0 when all shown."""
        products = [{"id": 1}, {"id": 2}]
        context = SearchContext(
            category="test",
            tool="search_products",
            query="test",
            page_size=2,
            current_page=0,
            all_results=products,
            total_count=2
        )

        assert context.remaining_count() == 0


class TestPaginationManagerInit:
    """Test PaginationManager initialization."""

    def test_manager_initialization(self):
        """Test PaginationManager initializes correctly."""
        manager = PaginationManager()
        assert manager._contexts == {}

    def test_show_more_patterns_defined(self):
        """Test SHOW_MORE_PATTERNS are defined."""
        assert len(PaginationManager.SHOW_MORE_PATTERNS) > 0
        assert "más" in PaginationManager.SHOW_MORE_PATTERNS
        assert "more" in PaginationManager.SHOW_MORE_PATTERNS


class TestSaveSearch:
    """Test save_search method."""

    def test_save_search_basic(self):
        """Test saving search results."""
        manager = PaginationManager()
        products = [{"id": 1}, {"id": 2}, {"id": 3}]

        manager.save_search(
            category="laptops",
            tool="search_products",
            query="gaming laptops",
            results=products,
            page_size=2
        )

        assert manager.has_context("laptops")
        assert manager.get_total_count("laptops") == 3

    def test_save_search_default_page_size(self):
        """Test save_search uses default page_size."""
        manager = PaginationManager()
        products = [{"id": 1}, {"id": 2}]

        manager.save_search(
            category="test",
            tool="search_products",
            query="test",
            results=products
        )

        context = manager._contexts["test"]
        assert context.page_size == 4  # Default value

    def test_save_search_overwrites_existing(self):
        """Test saving search overwrites existing context."""
        manager = PaginationManager()

        manager.save_search("test", "tool1", "query1", [{"id": 1}])
        manager.save_search("test", "tool2", "query2", [{"id": 2}, {"id": 3}])

        assert manager.get_total_count("test") == 2


class TestIsShowMoreRequest:
    """Test is_show_more_request method."""

    def test_is_show_more_spanish(self):
        """Test detects Spanish 'show more' patterns."""
        manager = PaginationManager()

        assert manager.is_show_more_request("muéstrame más") is True
        assert manager.is_show_more_request("ver más opciones") is True
        assert manager.is_show_more_request("dame más") is True
        assert manager.is_show_more_request("siguiente") is True

    def test_is_show_more_english(self):
        """Test detects English 'show more' patterns."""
        manager = PaginationManager()

        assert manager.is_show_more_request("show me more") is True
        assert manager.is_show_more_request("see more") is True
        assert manager.is_show_more_request("what else") is True
        assert manager.is_show_more_request("next") is True

    def test_is_show_more_case_insensitive(self):
        """Test detection is case insensitive."""
        manager = PaginationManager()

        assert manager.is_show_more_request("MÁS") is True
        assert manager.is_show_more_request("MORE") is True
        assert manager.is_show_more_request("Next") is True

    def test_is_show_more_false(self):
        """Test returns False for non-pagination messages."""
        manager = PaginationManager()

        assert manager.is_show_more_request("busco laptops") is False
        assert manager.is_show_more_request("cuál es el precio") is False
        assert manager.is_show_more_request("hello") is False


class TestDetectCategory:
    """Test detect_category method."""

    def test_detect_category_by_name(self):
        """Test detects category when mentioned in message."""
        manager = PaginationManager()
        manager.save_search("laptops", "search_products", "laptops", [{"id": 1}])
        manager.save_search("phones", "search_products", "phones", [{"id": 2}])

        category = manager.detect_category("muéstrame más laptops")
        assert category == "laptops"

    def test_detect_category_single_context(self):
        """Test returns single category when only one exists."""
        manager = PaginationManager()
        manager.save_search("laptops", "search_products", "laptops", [{"id": 1}])

        category = manager.detect_category("más")
        assert category == "laptops"

    def test_detect_category_case_insensitive(self):
        """Test detection is case insensitive."""
        manager = PaginationManager()
        manager.save_search("laptops", "search_products", "laptops", [{"id": 1}])

        category = manager.detect_category("más LAPTOPS")
        assert category == "laptops"

    def test_detect_category_none(self):
        """Test returns None when category cannot be detected."""
        manager = PaginationManager()
        manager.save_search("laptops", "search_products", "laptops", [{"id": 1}])
        manager.save_search("phones", "search_products", "phones", [{"id": 2}])

        category = manager.detect_category("más")  # Ambiguous
        assert category is None

    def test_detect_category_no_contexts(self):
        """Test returns None when no contexts exist."""
        manager = PaginationManager()

        category = manager.detect_category("más laptops")
        assert category is None


class TestHasContext:
    """Test has_context method."""

    def test_has_context_true(self):
        """Test has_context returns True when exists."""
        manager = PaginationManager()
        manager.save_search("laptops", "search_products", "laptops", [{"id": 1}])

        assert manager.has_context("laptops") is True

    def test_has_context_false(self):
        """Test has_context returns False when not exists."""
        manager = PaginationManager()

        assert manager.has_context("laptops") is False


class TestHasMoreResults:
    """Test has_more_results method."""

    def test_has_more_results_true(self):
        """Test has_more_results returns True when more available."""
        manager = PaginationManager()
        products = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
        manager.save_search("test", "search_products", "test", products, page_size=2)

        assert manager.has_more_results("test") is True

    def test_has_more_results_false(self):
        """Test has_more_results returns False when no more."""
        manager = PaginationManager()
        products = [{"id": 1}, {"id": 2}]
        manager.save_search("test", "search_products", "test", products, page_size=2)

        assert manager.has_more_results("test") is False

    def test_has_more_results_no_context(self):
        """Test has_more_results returns False when no context."""
        manager = PaginationManager()

        assert manager.has_more_results("nonexistent") is False


class TestGetNextPage:
    """Test get_next_page method."""

    def test_get_next_page_success(self):
        """Test get_next_page returns next page."""
        manager = PaginationManager()
        products = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
        manager.save_search("test", "search_products", "test", products, page_size=2)

        next_page = manager.get_next_page("test")
        assert next_page is not None
        assert len(next_page) == 2
        assert next_page[0]["id"] == 3
        assert next_page[1]["id"] == 4

    def test_get_next_page_no_more(self):
        """Test get_next_page returns None when no more."""
        manager = PaginationManager()
        products = [{"id": 1}, {"id": 2}]
        manager.save_search("test", "search_products", "test", products, page_size=2)

        next_page = manager.get_next_page("test")
        assert next_page is None

    def test_get_next_page_no_context(self):
        """Test get_next_page returns None when no context."""
        manager = PaginationManager()

        next_page = manager.get_next_page("nonexistent")
        assert next_page is None


class TestGetCurrentPage:
    """Test get_current_page method."""

    def test_get_current_page_success(self):
        """Test get_current_page returns current page."""
        manager = PaginationManager()
        products = [{"id": 1}, {"id": 2}, {"id": 3}]
        manager.save_search("test", "search_products", "test", products, page_size=2)

        current = manager.get_current_page("test")
        assert current is not None
        assert len(current) == 2
        assert current[0]["id"] == 1
        assert current[1]["id"] == 2

    def test_get_current_page_no_context(self):
        """Test get_current_page returns None when no context."""
        manager = PaginationManager()

        current = manager.get_current_page("nonexistent")
        assert current is None


class TestGetRemainingCount:
    """Test get_remaining_count method."""

    def test_get_remaining_count_success(self):
        """Test get_remaining_count returns correct count."""
        manager = PaginationManager()
        products = [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}]
        manager.save_search("test", "search_products", "test", products, page_size=2)

        remaining = manager.get_remaining_count("test")
        assert remaining == 3  # Showing 2, have 3 left

    def test_get_remaining_count_zero(self):
        """Test get_remaining_count returns 0 when all shown."""
        manager = PaginationManager()
        products = [{"id": 1}, {"id": 2}]
        manager.save_search("test", "search_products", "test", products, page_size=2)

        remaining = manager.get_remaining_count("test")
        assert remaining == 0

    def test_get_remaining_count_no_context(self):
        """Test get_remaining_count returns 0 when no context."""
        manager = PaginationManager()

        remaining = manager.get_remaining_count("nonexistent")
        assert remaining == 0


class TestGetTotalCount:
    """Test get_total_count method."""

    def test_get_total_count_success(self):
        """Test get_total_count returns correct count."""
        manager = PaginationManager()
        products = [{"id": 1}, {"id": 2}, {"id": 3}]
        manager.save_search("test", "search_products", "test", products)

        total = manager.get_total_count("test")
        assert total == 3

    def test_get_total_count_no_context(self):
        """Test get_total_count returns 0 when no context."""
        manager = PaginationManager()

        total = manager.get_total_count("nonexistent")
        assert total == 0


class TestGetAllCategories:
    """Test get_all_categories method."""

    def test_get_all_categories_empty(self):
        """Test get_all_categories returns empty list."""
        manager = PaginationManager()

        categories = manager.get_all_categories()
        assert categories == []

    def test_get_all_categories_multiple(self):
        """Test get_all_categories returns all categories."""
        manager = PaginationManager()
        manager.save_search("laptops", "search_products", "laptops", [{"id": 1}])
        manager.save_search("phones", "search_products", "phones", [{"id": 2}])

        categories = manager.get_all_categories()
        assert len(categories) == 2
        assert "laptops" in categories
        assert "phones" in categories


class TestClearContext:
    """Test clear_context method."""

    def test_clear_context_single(self):
        """Test clearing single category context."""
        manager = PaginationManager()
        manager.save_search("laptops", "search_products", "laptops", [{"id": 1}])
        manager.save_search("phones", "search_products", "phones", [{"id": 2}])

        manager.clear_context("laptops")

        assert manager.has_context("laptops") is False
        assert manager.has_context("phones") is True

    def test_clear_context_all(self):
        """Test clearing all contexts."""
        manager = PaginationManager()
        manager.save_search("laptops", "search_products", "laptops", [{"id": 1}])
        manager.save_search("phones", "search_products", "phones", [{"id": 2}])

        manager.clear_context()

        assert manager.has_context("laptops") is False
        assert manager.has_context("phones") is False
        assert len(manager.get_all_categories()) == 0

    def test_clear_context_nonexistent(self):
        """Test clearing nonexistent context doesn't error."""
        manager = PaginationManager()

        manager.clear_context("nonexistent")  # Should not raise


class TestExtractCategoryFromQuery:
    """Test extract_category_from_query method."""

    def test_extract_category_simple(self):
        """Test extracts simple category."""
        manager = PaginationManager()

        category = manager.extract_category_from_query("laptops")
        assert category == "laptops"

    def test_extract_category_multiple_words(self):
        """Test extracts first 4 meaningful words."""
        manager = PaginationManager()

        category = manager.extract_category_from_query("gaming laptops high performance")
        assert category == "gaming laptops high performance"

    def test_extract_category_filters_stopwords(self):
        """Test filters out Spanish stopwords."""
        manager = PaginationManager()

        category = manager.extract_category_from_query("de los mejores laptops")
        assert category == "mejores laptops"

    def test_extract_category_empty(self):
        """Test handles empty query."""
        manager = PaginationManager()

        category = manager.extract_category_from_query("")
        assert category == "general"

    def test_extract_category_only_stopwords(self):
        """Test handles query with only stopwords."""
        manager = PaginationManager()

        category = manager.extract_category_from_query("de los el")
        assert category == "de"  # Falls back to first word

    def test_extract_category_captures_intent_four_words(self):
        """Test captures search intent with up to 4 words."""
        manager = PaginationManager()

        # Test cases demonstrating intent capture
        test_cases = [
            ("laptop gaming barato estudiante", "laptop gaming barato estudiante"),
            ("bolsos de mujer para oficina ejecutiva", "bolsos mujer oficina ejecutiva"),
            ("mouse inalámbrico gaming RGB profesional", "mouse inalámbrico gaming rgb"),
            ("zapatillas running Nike baratas originales", "zapatillas running nike baratas"),
        ]

        for query, expected in test_cases:
            category = manager.extract_category_from_query(query)
            assert category == expected, f"Failed for query: {query}"

    def test_extract_category_more_than_four_words(self):
        """Test limits to 4 words even with longer queries."""
        manager = PaginationManager()

        # Query with 6 meaningful words should extract only first 4
        category = manager.extract_category_from_query(
            "laptop gaming barato estudiante oferta especial navidad"
        )
        assert category == "laptop gaming barato estudiante"

    def test_extract_category_mixed_stopwords(self):
        """Test filters stopwords while preserving intent."""
        manager = PaginationManager()

        # "de" and "para" are stopwords, should be filtered
        category = manager.extract_category_from_query(
            "computadora de escritorio para gaming profesional"
        )
        assert category == "computadora escritorio gaming profesional"


class TestPaginationFlow:
    """Test complete pagination flow scenarios."""

    def test_full_pagination_flow(self):
        """Test complete pagination flow."""
        manager = PaginationManager()

        # Save search results
        products = [
            {"id": 1, "name": "Product 1"},
            {"id": 2, "name": "Product 2"},
            {"id": 3, "name": "Product 3"},
            {"id": 4, "name": "Product 4"},
            {"id": 5, "name": "Product 5"},
        ]
        manager.save_search("test", "search_products", "test products", products, page_size=2)

        # Check initial state
        assert manager.get_total_count("test") == 5
        assert manager.get_remaining_count("test") == 3
        assert manager.has_more_results("test") is True

        # Get first additional page
        page1 = manager.get_next_page("test")
        assert len(page1) == 2
        assert page1[0]["id"] == 3
        assert manager.get_remaining_count("test") == 1

        # Get second additional page
        page2 = manager.get_next_page("test")
        assert len(page2) == 1
        assert page2[0]["id"] == 5
        assert manager.get_remaining_count("test") == 0
        assert manager.has_more_results("test") is False

        # Try to get more (should return None)
        page3 = manager.get_next_page("test")
        assert page3 is None

    def test_multi_category_pagination(self):
        """Test pagination with multiple categories."""
        manager = PaginationManager()

        # Save two different categories
        laptops = [{"id": 1}, {"id": 2}, {"id": 3}]
        phones = [{"id": 10}, {"id": 11}]

        manager.save_search("laptops", "search_products", "laptops", laptops, page_size=2)
        manager.save_search("phones", "search_products", "phones", phones, page_size=2)

        # Check both contexts exist independently
        assert manager.has_context("laptops") is True
        assert manager.has_context("phones") is True
        assert manager.has_more_results("laptops") is True
        assert manager.has_more_results("phones") is False

        # Get next page for laptops
        next_laptops = manager.get_next_page("laptops")
        assert next_laptops is not None
        assert next_laptops[0]["id"] == 3

        # Phones should be unaffected
        assert manager.has_more_results("phones") is False
