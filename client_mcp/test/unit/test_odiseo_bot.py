"""Unit tests for core/odiseo_bot.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types

from core.odiseo_bot import OdiseoBot


class TestOdiseoBotInit:
    """Test OdiseoBot initialization."""

    def test_bot_initialization_default(self):
        """Test bot initializes with default parameters."""
        bot = OdiseoBot()
        assert bot.debug_mode is False
        assert bot.client is None
        assert bot.system_prompt == ""
        assert bot.mcp_client is None
        assert bot.mcp_tools == []
        assert bot.tool_executor is None
        assert bot.conversation_history == []
        assert bot._generation_config is None
        assert bot.cached_content is None

    def test_bot_initialization_debug_mode(self):
        """Test bot initializes in debug mode."""
        bot = OdiseoBot(debug_mode=True)
        assert bot.debug_mode is True

    def test_bot_thinking_manager_initialized(self):
        """Test ThinkingManager is initialized."""
        bot = OdiseoBot()
        assert bot.thinking_manager is not None

    def test_bot_rate_limiter_not_initialized_when_disabled(self):
        """Test rate limiter not initialized when disabled."""
        with patch("core.odiseo_bot.settings") as mock_settings:
            mock_settings.ENABLE_RATE_LIMITING = False
            bot = OdiseoBot()
            assert bot.rate_limiter is None


class TestOdiseoBotInitialize:
    """Test initialize method."""

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful initialization."""
        bot = OdiseoBot()

        with patch("core.odiseo_bot.settings") as mock_settings:
            mock_settings.get_api_key.return_value = "test_api_key"
            mock_settings.MODEL = "gemini-2.0-flash-exp"
            mock_settings.ENABLE_CONTEXT_CACHING = False
            mock_settings.TEMPERATURE = 0.7
            mock_settings.TOP_K = 40
            mock_settings.TOP_P = 0.95
            mock_settings.MCP_HOST = "localhost"
            mock_settings.MCP_PORT = "3000"

            with patch("core.odiseo_bot.genai.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                with patch.object(bot, "_connect_mcp_official", new_callable=AsyncMock):
                    with patch.object(
                        bot, "_build_dynamic_system_prompt", return_value="test prompt"
                    ):
                        with patch.object(
                            bot, "_build_generation_config", return_value=MagicMock()
                        ):
                            await bot.initialize()

        assert bot.client is not None
        assert bot.system_prompt == "test prompt"
        assert bot._generation_config is not None

    @pytest.mark.asyncio
    async def test_initialize_api_key_error(self):
        """Test initialization fails with API key error."""
        bot = OdiseoBot()

        with patch("core.odiseo_bot.settings") as mock_settings:
            mock_settings.get_api_key.side_effect = Exception("API key error")

            with pytest.raises(Exception, match="API key error"):
                await bot.initialize()

    @pytest.mark.asyncio
    async def test_initialize_with_context_caching(self):
        """Test initialization with context caching enabled."""
        bot = OdiseoBot()

        with patch("core.odiseo_bot.settings") as mock_settings:
            mock_settings.get_api_key.return_value = "test_api_key"
            mock_settings.MODEL = "gemini-2.0-flash-exp"
            mock_settings.ENABLE_CONTEXT_CACHING = True
            mock_settings.CACHE_TTL_MINUTES = 30
            mock_settings.MCP_HOST = "localhost"
            mock_settings.MCP_PORT = "3000"

            with patch("core.odiseo_bot.genai.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_cached_content = MagicMock()
                mock_cached_content.usage_metadata.total_token_count = 1000
                mock_client.caches.create = AsyncMock(return_value=mock_cached_content)
                mock_client_class.return_value = mock_client

                with patch.object(bot, "_connect_mcp_official", new_callable=AsyncMock):
                    with patch.object(
                        bot, "_build_dynamic_system_prompt", return_value="test prompt"
                    ):
                        with patch.object(
                            bot, "_build_generation_config", return_value=MagicMock()
                        ):
                            await bot.initialize()

        assert bot.cached_content is not None

    @pytest.mark.asyncio
    async def test_initialize_context_caching_failure(self):
        """Test initialization continues when context caching fails."""
        bot = OdiseoBot()

        with patch("core.odiseo_bot.settings") as mock_settings:
            mock_settings.get_api_key.return_value = "test_api_key"
            mock_settings.MODEL = "gemini-2.0-flash-exp"
            mock_settings.ENABLE_CONTEXT_CACHING = True
            mock_settings.CACHE_TTL_MINUTES = 30
            mock_settings.MCP_HOST = "localhost"
            mock_settings.MCP_PORT = "3000"

            with patch("core.odiseo_bot.genai.Client") as mock_client_class:
                mock_client = MagicMock()
                # caches.create is NOT async (fixed earlier)
                mock_client.caches.create = MagicMock(
                    side_effect=Exception("Cache error")
                )
                mock_client_class.return_value = mock_client

                with patch.object(bot, "_connect_mcp_official", new_callable=AsyncMock):
                    with patch.object(
                        bot, "_build_dynamic_system_prompt", return_value="test prompt"
                    ):
                        with patch.object(
                            bot, "_build_generation_config", return_value=MagicMock()
                        ):
                            await bot.initialize()

        assert bot.cached_content is None  # Should be None but initialization continues


class TestConnectMCPOfficial:
    """Test _connect_mcp_official method."""

    @pytest.mark.asyncio
    async def test_connect_mcp_healthy_server(self):
        """Test connecting to healthy MCP server."""
        bot = OdiseoBot()

        with patch("core.odiseo_bot.settings") as mock_settings:
            mock_settings.MCP_HOST = "localhost"
            mock_settings.MCP_PORT = "3000"

            health_response = {
                "status": "healthy",
                "checks": {
                    "database": {
                        "status": "healthy",
                        "product_count": 100,
                        "extensions": ["unaccent", "pg_trgm"],
                    }
                },
            }

            with patch("core.odiseo_bot.MCPConnector") as mock_connector_class:
                mock_connector_class.check_server_health = AsyncMock(
                    return_value=health_response
                )
                mock_connector = MagicMock()
                mock_connector.__aenter__ = AsyncMock()
                mock_connector.list_tools = AsyncMock(
                    return_value=[{"name": "test_tool"}]
                )
                mock_connector_class.return_value = mock_connector

                with patch.object(
                    bot, "_convert_tools_to_genai", return_value=[MagicMock()]
                ):
                    await bot._connect_mcp_official()

        assert bot.mcp_client is not None
        assert len(bot.mcp_tools) == 1

    @pytest.mark.asyncio
    async def test_connect_mcp_unreachable_server(self):
        """Test graceful degradation when server is unreachable."""
        bot = OdiseoBot()

        with patch("core.odiseo_bot.settings") as mock_settings:
            mock_settings.MCP_HOST = "localhost"
            mock_settings.MCP_PORT = "3000"

            health_response = {
                "status": "unreachable",
                "error": "Connection refused",
                "url": "http://localhost:3000/mcp",
            }

            with patch("core.odiseo_bot.MCPConnector") as mock_connector_class:
                mock_connector_class.check_server_health = AsyncMock(
                    return_value=health_response
                )

                # Should NOT raise - graceful degradation
                await bot._connect_mcp_official()

                # Bot should continue without MCP client
                assert bot.mcp_client is None
                assert bot.mcp_tools == []

    @pytest.mark.asyncio
    async def test_connect_mcp_unhealthy_server(self):
        """Test graceful degradation when server is unhealthy."""
        bot = OdiseoBot()

        with patch("core.odiseo_bot.settings") as mock_settings:
            mock_settings.MCP_HOST = "localhost"
            mock_settings.MCP_PORT = "3000"

            health_response = {
                "status": "unhealthy",
                "checks": {
                    "database": {"status": "unhealthy", "error": "Connection failed"}
                },
            }

            with patch("core.odiseo_bot.MCPConnector") as mock_connector_class:
                mock_connector_class.check_server_health = AsyncMock(
                    return_value=health_response
                )

                # Should NOT raise - graceful degradation
                await bot._connect_mcp_official()

                # Bot should continue without MCP client
                assert bot.mcp_client is None
                assert bot.mcp_tools == []

    @pytest.mark.asyncio
    async def test_connect_mcp_degraded_server(self):
        """Test connection continues with degraded server."""
        bot = OdiseoBot()

        with patch("core.odiseo_bot.settings") as mock_settings:
            mock_settings.MCP_HOST = "localhost"
            mock_settings.MCP_PORT = "3000"

            health_response = {
                "status": "degraded",
                "checks": {
                    "database": {
                        "status": "degraded",
                        "warning": "Some extensions missing",
                    }
                },
            }

            with patch("core.odiseo_bot.MCPConnector") as mock_connector_class:
                mock_connector_class.check_server_health = AsyncMock(
                    return_value=health_response
                )
                mock_connector = MagicMock()
                mock_connector.__aenter__ = AsyncMock()
                mock_connector.list_tools = AsyncMock(return_value=[])
                mock_connector_class.return_value = mock_connector

                with patch.object(bot, "_convert_tools_to_genai", return_value=[]):
                    await bot._connect_mcp_official()

        assert bot.mcp_client is not None


class TestConvertToolsToGenai:
    """Test _convert_tools_to_genai method."""

    def test_convert_empty_tools(self):
        """Test converting empty tools list."""
        bot = OdiseoBot()
        result = bot._convert_tools_to_genai([])
        assert result == []

    def test_convert_single_tool(self):
        """Test converting single tool."""
        bot = OdiseoBot()
        tools = [
            {
                "name": "search_products",
                "description": "Search for products",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"],
                },
            }
        ]

        result = bot._convert_tools_to_genai(tools)
        assert len(result) == 1
        assert result[0].name == "search_products"

    def test_convert_multiple_tools(self):
        """Test converting multiple tools."""
        bot = OdiseoBot()
        tools = [
            {
                "name": "tool1",
                "description": "Tool 1",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "tool2",
                "description": "Tool 2",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
        ]

        result = bot._convert_tools_to_genai(tools)
        assert len(result) == 2


class TestBuildDynamicSystemPrompt:
    """Test _build_dynamic_system_prompt method."""

    def test_build_prompt_with_tools(self):
        """Test building prompt with MCP tools."""
        bot = OdiseoBot()
        bot.mcp_tools = [
            MagicMock(name="search_products"),
            MagicMock(name="get_product_details"),
        ]

        prompt = bot._build_dynamic_system_prompt()

        assert "Odiseo" in prompt
        assert "search_products" in prompt
        assert "get_product_details" in prompt

    def test_build_prompt_without_tools(self):
        """Test building prompt without tools."""
        bot = OdiseoBot()
        bot.mcp_tools = []

        prompt = bot._build_dynamic_system_prompt()

        assert "Odiseo" in prompt


class TestBuildGenerationConfig:
    """Test _build_generation_config method."""

    def test_build_config_without_cache(self):
        """Test building config without context cache."""
        bot = OdiseoBot()

        # Create a real FunctionDeclaration (no mocking needed for this simple case)
        bot.mcp_tools = [
            types.FunctionDeclaration(
                name="test_tool",
                description="Test tool description",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING, description="Query param"
                        )
                    },
                    required=["query"],
                ),
            )
        ]
        bot.cached_content = None
        bot.system_prompt = "Test prompt"

        with patch("core.odiseo_bot.settings") as mock_settings:
            mock_settings.MODEL = "gemini-2.0-flash-exp"
            mock_settings.TEMPERATURE = 0.7
            mock_settings.TOP_K = 40
            mock_settings.TOP_P = 0.95
            mock_settings.MAX_OUTPUT_TOKENS = 8192
            mock_settings.CANDIDATE_COUNT = 1

            config = bot._build_generation_config()

        assert config is not None

    def test_build_config_with_cache(self):
        """Test building config with context cache."""
        bot = OdiseoBot()

        # Create a real FunctionDeclaration
        bot.mcp_tools = [
            types.FunctionDeclaration(
                name="test_tool",
                description="Test tool description",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING, description="Query param"
                        )
                    },
                    required=["query"],
                ),
            )
        ]

        # Create proper CachedContent mock
        mock_cache = MagicMock()
        mock_cache.name = "test_cache_name"  # Must be a string, not MagicMock
        bot.cached_content = mock_cache
        bot.system_prompt = "Test prompt"

        with patch("core.odiseo_bot.settings") as mock_settings:
            mock_settings.MODEL = "gemini-2.0-flash-exp"
            mock_settings.TEMPERATURE = 0.7
            mock_settings.TOP_K = 40
            mock_settings.TOP_P = 0.95
            mock_settings.MAX_OUTPUT_TOKENS = 8192
            mock_settings.CANDIDATE_COUNT = 1

            config = bot._build_generation_config()

        assert config is not None


class TestCleanup:
    """Test cleanup method."""

    @pytest.mark.asyncio
    async def test_cleanup_without_mcp_client(self):
        """Test cleanup when no MCP client exists."""
        bot = OdiseoBot()
        await bot.cleanup()  # Should not raise

    @pytest.mark.asyncio
    async def test_cleanup_with_mcp_client(self):
        """Test cleanup with MCP client."""
        bot = OdiseoBot()
        mock_mcp_client = MagicMock()
        mock_mcp_client.__aexit__ = AsyncMock()
        bot.mcp_client = mock_mcp_client

        await bot.cleanup()

        mock_mcp_client.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_with_error(self):
        """Test cleanup handles errors gracefully."""
        bot = OdiseoBot()
        mock_mcp_client = MagicMock()
        mock_mcp_client.__aexit__ = AsyncMock(side_effect=Exception("Cleanup error"))
        bot.mcp_client = mock_mcp_client

        # Should not raise
        await bot.cleanup()


class TestConversationHistory:
    """Test conversation history handling."""

    def test_conversation_history_initialized_empty(self):
        """Test conversation history is initialized as empty list."""
        bot = OdiseoBot()
        assert bot.conversation_history == []
        assert isinstance(bot.conversation_history, list)

    def test_conversation_history_can_be_modified(self):
        """Test conversation history can be modified."""
        bot = OdiseoBot()
        mock_content1 = MagicMock()
        mock_content2 = MagicMock()
        bot.conversation_history.append(mock_content1)
        bot.conversation_history.append(mock_content2)

        assert len(bot.conversation_history) == 2
        assert bot.conversation_history[0] == mock_content1
        assert bot.conversation_history[1] == mock_content2
