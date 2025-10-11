"""Unit tests for FallbackStrategy."""

import logging
import pytest
from unittest.mock import AsyncMock, MagicMock

from strategies.fallback import (
    FallbackRule,
    FallbackStrategy,
    create_default_fallback_strategy,
)


class TestFallbackRule:
    """Test suite for FallbackRule dataclass."""

    def test_basic_creation(self):
        """Test basic FallbackRule creation."""
        rule = FallbackRule(primary_tool="tool_a", fallback_tool="tool_b")

        assert rule.primary_tool == "tool_a"
        assert rule.fallback_tool == "tool_b"
        assert rule.param_mapping is None
        assert rule.condition is None

    def test_creation_with_param_mapping(self):
        """Test FallbackRule with parameter mapping."""
        mapping = {"query": "search_term", "limit": "max_results"}
        rule = FallbackRule(
            primary_tool="search",
            fallback_tool="fuzzy_search",
            param_mapping=mapping,
        )

        assert rule.param_mapping == mapping
        assert rule.param_mapping["query"] == "search_term"

    def test_creation_with_condition(self):
        """Test FallbackRule with conditional function."""

        def is_timeout_error(exc: Exception) -> bool:
            return "timeout" in str(exc).lower()

        rule = FallbackRule(
            primary_tool="api_call",
            fallback_tool="cached_call",
            condition=is_timeout_error,
        )

        assert rule.condition is not None
        assert rule.condition(Exception("Connection timeout")) is True
        assert rule.condition(Exception("Invalid parameter")) is False


class TestFallbackStrategy:
    """Test suite for FallbackStrategy class."""

    def test_initialization_default(self):
        """Test FallbackStrategy initialization with defaults."""
        strategy = FallbackStrategy()

        assert strategy.logger is not None
        assert strategy._rules == {}

    def test_initialization_custom_logger(self):
        """Test FallbackStrategy initialization with custom logger."""
        custom_logger = logging.getLogger("test")
        strategy = FallbackStrategy(logger=custom_logger)

        assert strategy.logger == custom_logger

    def test_add_rule_simple(self):
        """Test adding a simple fallback rule."""
        strategy = FallbackStrategy()

        strategy.add_rule(primary_tool="tool_a", fallback_tool="tool_b")

        assert "tool_a" in strategy._rules
        assert len(strategy._rules["tool_a"]) == 1
        assert strategy._rules["tool_a"][0].fallback_tool == "tool_b"

    def test_add_rule_with_mapping(self):
        """Test adding a rule with parameter mapping."""
        strategy = FallbackStrategy()
        mapping = {"old_param": "new_param"}

        strategy.add_rule(
            primary_tool="tool_a", fallback_tool="tool_b", param_mapping=mapping
        )

        rule = strategy._rules["tool_a"][0]
        assert rule.param_mapping == mapping

    def test_add_rule_with_condition(self):
        """Test adding a rule with condition."""
        strategy = FallbackStrategy()

        def condition(exc: Exception) -> bool:
            return "error" in str(exc)

        strategy.add_rule(
            primary_tool="tool_a", fallback_tool="tool_b", condition=condition
        )

        rule = strategy._rules["tool_a"][0]
        assert rule.condition is not None
        assert rule.condition(Exception("error occurred")) is True

    def test_add_multiple_rules_same_tool(self):
        """Test adding multiple fallback rules for the same tool."""
        strategy = FallbackStrategy()

        strategy.add_rule(primary_tool="tool_a", fallback_tool="tool_b")
        strategy.add_rule(primary_tool="tool_a", fallback_tool="tool_c")

        assert len(strategy._rules["tool_a"]) == 2
        assert strategy._rules["tool_a"][0].fallback_tool == "tool_b"
        assert strategy._rules["tool_a"][1].fallback_tool == "tool_c"

    @pytest.mark.asyncio
    async def test_execute_with_fallback_primary_succeeds(self):
        """Test execution when primary tool succeeds."""
        strategy = FallbackStrategy()
        strategy.add_rule(primary_tool="tool_a", fallback_tool="tool_b")

        mock_executor = MagicMock()
        mock_executor.execute_tool = AsyncMock(return_value={"result": "success"})

        result = await strategy.execute_with_fallback(
            primary_tool="tool_a", params={"param": "value"}, executor=mock_executor
        )

        assert result == {"result": "success"}
        mock_executor.execute_tool.assert_awaited_once_with(
            "tool_a", {"param": "value"}, _use_fallback=False
        )

    @pytest.mark.asyncio
    async def test_execute_with_fallback_primary_fails_fallback_succeeds(self):
        """Test execution when primary fails but fallback succeeds."""
        strategy = FallbackStrategy()
        strategy.add_rule(primary_tool="tool_a", fallback_tool="tool_b")

        mock_executor = MagicMock()
        mock_executor.execute_tool = AsyncMock(
            side_effect=[
                ValueError("Primary failed"),
                {"result": "fallback_success"},
            ]
        )

        result = await strategy.execute_with_fallback(
            primary_tool="tool_a", params={"param": "value"}, executor=mock_executor
        )

        assert result == {"result": "fallback_success"}
        assert mock_executor.execute_tool.await_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_fallback_param_mapping(self):
        """Test parameter mapping during fallback."""
        strategy = FallbackStrategy()
        strategy.add_rule(
            primary_tool="search",
            fallback_tool="fuzzy_search",
            param_mapping={"query": "search_term", "limit": "max_results"},
        )

        mock_executor = MagicMock()
        mock_executor.execute_tool = AsyncMock(
            side_effect=[
                ValueError("Primary failed"),
                {"result": "mapped_success"},
            ]
        )

        await strategy.execute_with_fallback(
            primary_tool="search",
            params={"query": "laptop", "limit": 10},
            executor=mock_executor,
        )

        # Check that second call used mapped parameters
        second_call_args = mock_executor.execute_tool.await_args_list[1]
        assert second_call_args[0][0] == "fuzzy_search"
        assert second_call_args[0][1]["search_term"] == "laptop"
        assert second_call_args[0][1]["max_results"] == 10

    @pytest.mark.asyncio
    async def test_execute_with_fallback_no_rules(self):
        """Test execution when no fallback rules are defined."""
        strategy = FallbackStrategy()

        mock_executor = MagicMock()
        mock_executor.execute_tool = AsyncMock(side_effect=ValueError("Tool failed"))

        with pytest.raises(ValueError, match="Tool failed"):
            await strategy.execute_with_fallback(
                primary_tool="tool_a", params={}, executor=mock_executor
            )

    @pytest.mark.asyncio
    async def test_execute_with_fallback_max_depth_reached(self):
        """Test execution when max fallback depth is reached."""
        strategy = FallbackStrategy()
        strategy.add_rule(primary_tool="tool_a", fallback_tool="tool_b")
        strategy.add_rule(primary_tool="tool_b", fallback_tool="tool_c")
        strategy.add_rule(primary_tool="tool_c", fallback_tool="tool_d")

        mock_executor = MagicMock()
        # All tools fail
        mock_executor.execute_tool = AsyncMock(side_effect=ValueError("Failed"))

        with pytest.raises(
            RuntimeError, match="Maximum fallback depth \\(2\\) reached"
        ):
            await strategy.execute_with_fallback(
                primary_tool="tool_a",
                params={},
                executor=mock_executor,
                max_fallback_depth=2,
            )

    @pytest.mark.asyncio
    async def test_execute_with_fallback_conditional_rule(self):
        """Test conditional fallback rule."""
        strategy = FallbackStrategy()

        def is_timeout(exc: Exception) -> bool:
            return "timeout" in str(exc).lower()

        strategy.add_rule(
            primary_tool="api_call",
            fallback_tool="cached_call",
            condition=is_timeout,
        )

        mock_executor = MagicMock()

        # First test: timeout error triggers fallback
        mock_executor.execute_tool = AsyncMock(
            side_effect=[
                ValueError("Connection timeout"),
                {"result": "from_cache"},
            ]
        )

        result = await strategy.execute_with_fallback(
            primary_tool="api_call", params={}, executor=mock_executor
        )

        assert result == {"result": "from_cache"}
        assert mock_executor.execute_tool.await_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_fallback_condition_not_met(self):
        """Test fallback when condition is not met."""
        strategy = FallbackStrategy()

        def is_timeout(exc: Exception) -> bool:
            return "timeout" in str(exc).lower()

        strategy.add_rule(
            primary_tool="api_call",
            fallback_tool="cached_call",
            condition=is_timeout,
        )

        mock_executor = MagicMock()
        # Non-timeout error - condition not met
        mock_executor.execute_tool = AsyncMock(
            side_effect=ValueError("Invalid parameter")
        )

        with pytest.raises(ValueError, match="Invalid parameter"):
            await strategy.execute_with_fallback(
                primary_tool="api_call", params={}, executor=mock_executor
            )

    def test_find_applicable_rule_no_condition(self):
        """Test finding applicable rule without condition."""
        strategy = FallbackStrategy()
        strategy.add_rule(primary_tool="tool_a", fallback_tool="tool_b")

        rule = strategy._find_applicable_rule("tool_a", ValueError("Any error"))

        assert rule is not None
        assert rule.fallback_tool == "tool_b"

    def test_find_applicable_rule_with_condition_match(self):
        """Test finding applicable rule with matching condition."""
        strategy = FallbackStrategy()

        def is_timeout(exc: Exception) -> bool:
            return "timeout" in str(exc).lower()

        strategy.add_rule(
            primary_tool="tool_a", fallback_tool="tool_b", condition=is_timeout
        )

        rule = strategy._find_applicable_rule("tool_a", ValueError("Connection timeout"))

        assert rule is not None
        assert rule.fallback_tool == "tool_b"

    def test_find_applicable_rule_with_condition_no_match(self):
        """Test finding applicable rule with non-matching condition."""
        strategy = FallbackStrategy()

        def is_timeout(exc: Exception) -> bool:
            return "timeout" in str(exc).lower()

        strategy.add_rule(
            primary_tool="tool_a", fallback_tool="tool_b", condition=is_timeout
        )

        rule = strategy._find_applicable_rule("tool_a", ValueError("Invalid parameter"))

        assert rule is None

    def test_find_applicable_rule_no_rules(self):
        """Test finding applicable rule when no rules exist."""
        strategy = FallbackStrategy()

        rule = strategy._find_applicable_rule("tool_a", ValueError("Error"))

        assert rule is None

    def test_map_parameters_simple(self):
        """Test simple parameter mapping."""
        strategy = FallbackStrategy()
        params = {"query": "laptop", "limit": 10}
        mapping = {"query": "search_term", "limit": "max_results"}

        mapped = strategy._map_parameters(params, mapping)

        assert mapped["search_term"] == "laptop"
        assert mapped["max_results"] == 10
        assert "query" not in mapped
        assert "limit" not in mapped

    def test_map_parameters_partial_mapping(self):
        """Test parameter mapping with unmapped parameters."""
        strategy = FallbackStrategy()
        params = {"query": "laptop", "category": "electronics", "limit": 10}
        mapping = {"query": "search_term"}  # Only map query

        mapped = strategy._map_parameters(params, mapping)

        assert mapped["search_term"] == "laptop"
        assert mapped["category"] == "electronics"  # Kept original name
        assert mapped["limit"] == 10  # Kept original name

    def test_map_parameters_empty(self):
        """Test parameter mapping with empty inputs."""
        strategy = FallbackStrategy()

        # Empty params
        assert strategy._map_parameters({}, {"a": "b"}) == {}

        # Empty mapping
        params = {"query": "test"}
        mapped = strategy._map_parameters(params, {})
        assert mapped == {"query": "test"}

    def test_get_fallback_chain_simple(self):
        """Test getting fallback chain for simple case."""
        strategy = FallbackStrategy()
        strategy.add_rule(primary_tool="tool_a", fallback_tool="tool_b")
        strategy.add_rule(primary_tool="tool_b", fallback_tool="tool_c")

        chain = strategy.get_fallback_chain("tool_a")

        assert chain == ["tool_a", "tool_b", "tool_c"]

    def test_get_fallback_chain_no_fallback(self):
        """Test getting fallback chain when no fallback exists."""
        strategy = FallbackStrategy()

        chain = strategy.get_fallback_chain("tool_a")

        assert chain == ["tool_a"]

    def test_get_fallback_chain_prevents_infinite_loop(self):
        """Test fallback chain prevents infinite loops."""
        strategy = FallbackStrategy()
        # Create circular dependency (shouldn't happen in practice, but test safety)
        strategy.add_rule(primary_tool="tool_a", fallback_tool="tool_b")
        strategy.add_rule(primary_tool="tool_b", fallback_tool="tool_a")

        chain = strategy.get_fallback_chain("tool_a")

        # Should stop at max length (10)
        assert len(chain) == 10

    def test_has_fallback_true(self):
        """Test has_fallback returns True when rules exist."""
        strategy = FallbackStrategy()
        strategy.add_rule(primary_tool="tool_a", fallback_tool="tool_b")

        assert strategy.has_fallback("tool_a") is True

    def test_has_fallback_false(self):
        """Test has_fallback returns False when no rules exist."""
        strategy = FallbackStrategy()

        assert strategy.has_fallback("tool_a") is False

    def test_clear_rules(self):
        """Test clearing all fallback rules."""
        strategy = FallbackStrategy()
        strategy.add_rule(primary_tool="tool_a", fallback_tool="tool_b")
        strategy.add_rule(primary_tool="tool_c", fallback_tool="tool_d")

        assert len(strategy._rules) == 2

        strategy.clear_rules()

        assert len(strategy._rules) == 0
        assert strategy.has_fallback("tool_a") is False


class TestCreateDefaultFallbackStrategy:
    """Test suite for create_default_fallback_strategy factory function."""

    def test_creates_strategy_instance(self):
        """Test that factory creates FallbackStrategy instance."""
        strategy = create_default_fallback_strategy()

        assert isinstance(strategy, FallbackStrategy)

    def test_has_default_rules(self):
        """Test that default strategy has pre-configured rules."""
        strategy = create_default_fallback_strategy()

        # Should have rules for search_products and fetch_by_sku
        assert strategy.has_fallback("search_products") is True
        assert strategy.has_fallback("fetch_by_sku") is True

    def test_search_products_fallback(self):
        """Test search_products fallback rule configuration."""
        strategy = create_default_fallback_strategy()

        rules = strategy._rules.get("search_products", [])
        assert len(rules) > 0

        rule = rules[0]
        assert rule.fallback_tool == "fuzzy_search_smart"
        assert rule.param_mapping is not None
        assert rule.param_mapping.get("query") == "search_term"

    def test_fetch_by_sku_fallback(self):
        """Test fetch_by_sku fallback rule configuration."""
        strategy = create_default_fallback_strategy()

        rules = strategy._rules.get("fetch_by_sku", [])
        assert len(rules) > 0

        rule = rules[0]
        assert rule.fallback_tool == "fetch_by_id"
        assert rule.param_mapping is not None
        assert rule.param_mapping.get("sku") == "product_id"

    def test_fallback_chains(self):
        """Test fallback chains in default strategy."""
        strategy = create_default_fallback_strategy()

        # Get chains for default tools
        search_chain = strategy.get_fallback_chain("search_products")
        sku_chain = strategy.get_fallback_chain("fetch_by_sku")

        assert "fuzzy_search_smart" in search_chain
        assert "fetch_by_id" in sku_chain
