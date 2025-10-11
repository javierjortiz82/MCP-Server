"""Integration tests for Context Caching functionality.

This module tests the Context Caching feature for Gemini 1.5+ models,
which reduces cost by 4x when reusing system instructions across requests.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from config.settings import settings
from core.odiseo_bot import OdiseoBot


class TestContextCaching:
    """Test suite for Context Caching integration."""

    @pytest.mark.asyncio
    async def test_cache_creation_enabled(self):
        """Test that cache is created when ENABLE_CONTEXT_CACHING=True."""
        with patch("config.settings.settings.ENABLE_CONTEXT_CACHING", True):
            with patch("config.settings.settings.GOOGLE_API_KEY", "test-key"):
                with patch("core.odiseo_bot.genai.Client") as mock_client_class:
                    # Setup mock cached content
                    mock_cached = MagicMock()
                    mock_cached.name = "cachedContents/test-123"
                    mock_cached.usage_metadata.total_token_count = 1700

                    # Setup client.caches.create mock
                    mock_client_instance = MagicMock()
                    mock_client_instance.caches.create = AsyncMock(return_value=mock_cached)
                    mock_client_class.return_value = mock_client_instance

                    bot = OdiseoBot()

                    # Initialize (will fail on MCP, but cache should be created)
                    try:
                        await bot.initialize()
                    except Exception:
                        pass  # Expected MCP failure in test

                    # Verify cache was created
                    assert bot.cached_content is not None
                    assert bot.cached_content.name == "cachedContents/test-123"
                    mock_client_instance.caches.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_creation_disabled(self):
        """Test that no cache is created when ENABLE_CONTEXT_CACHING=False."""
        with patch("config.settings.settings.ENABLE_CONTEXT_CACHING", False):
            with patch("config.settings.settings.GOOGLE_API_KEY", "test-key"):
                with patch("core.odiseo_bot.genai.Client") as mock_client_class:
                    mock_client_instance = MagicMock()
                    mock_client_instance.caches.create = AsyncMock()
                    mock_client_class.return_value = mock_client_instance

                    bot = OdiseoBot()

                    # Initialize (will fail on MCP, but cache should NOT be created)
                    try:
                        await bot.initialize()
                    except Exception:
                        pass  # Expected MCP failure in test

                    # Verify cache was NOT created
                    assert bot.cached_content is None
                    mock_client_instance.caches.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_generation_config_uses_cached_content(self):
        """Test that generation config uses cached_content when available."""
        with patch("config.settings.settings.ENABLE_CONTEXT_CACHING", True):
            with patch("config.settings.settings.GOOGLE_API_KEY", "test-key"):
                with patch("core.odiseo_bot.genai.Client") as mock_client_class:
                    # Setup mock cached content
                    mock_cached = MagicMock()
                    mock_cached.name = "cachedContents/test-456"
                    mock_cached.usage_metadata.total_token_count = 1700

                    mock_client_instance = MagicMock()
                    mock_client_instance.caches.create = AsyncMock(return_value=mock_cached)
                    mock_client_class.return_value = mock_client_instance

                    bot = OdiseoBot()

                    # Initialize (will fail on MCP connection)
                    try:
                        await bot.initialize()
                    except Exception:
                        pass

                    # Verify generation config uses cached content
                    assert bot._generation_config is not None
                    # Cached content should be used instead of system_instruction
                    assert bot._generation_config.cached_content == "cachedContents/test-456"

    @pytest.mark.asyncio
    async def test_generation_config_fallback_without_cache(self):
        """Test that generation config uses system_instruction when cache disabled."""
        with patch("config.settings.settings.ENABLE_CONTEXT_CACHING", False):
            with patch("config.settings.settings.GOOGLE_API_KEY", "test-key"):
                with patch("core.odiseo_bot.genai.Client") as mock_client_class:
                    mock_client_instance = MagicMock()
                    mock_client_class.return_value = mock_client_instance

                    bot = OdiseoBot()

                    # Initialize (will fail on MCP connection)
                    try:
                        await bot.initialize()
                    except Exception:
                        pass

                    # Verify generation config uses system_instruction
                    assert bot._generation_config is not None
                    assert bot._generation_config.system_instruction is not None
                    assert bot._generation_config.system_instruction == bot.system_prompt

    @pytest.mark.asyncio
    async def test_cache_cleanup_on_bot_cleanup(self):
        """Test that cache is deleted when bot cleanup() is called."""
        with patch("config.settings.settings.ENABLE_CONTEXT_CACHING", True):
            with patch("config.settings.settings.GOOGLE_API_KEY", "test-key"):
                with patch("core.odiseo_bot.genai.Client") as mock_client_class:
                    # Setup mock cached content with delete method
                    mock_cached = MagicMock()
                    mock_cached.name = "cachedContents/test-789"
                    mock_cached.usage_metadata.total_token_count = 1700
                    mock_cached.delete = AsyncMock()

                    mock_client_instance = MagicMock()
                    mock_client_instance.caches.create = AsyncMock(return_value=mock_cached)
                    mock_client_class.return_value = mock_client_instance

                    bot = OdiseoBot()

                    # Initialize
                    try:
                        await bot.initialize()
                    except Exception:
                        pass

                    # Verify cache exists
                    assert bot.cached_content is not None

                    # Cleanup bot
                    await bot.cleanup()

                    # Verify cache delete was called
                    mock_cached.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_creation_with_ttl(self):
        """Test that cache is created with correct TTL from settings."""
        with patch("config.settings.settings.ENABLE_CONTEXT_CACHING", True):
            with patch("config.settings.settings.CACHE_TTL_MINUTES", 120):
                with patch("config.settings.settings.GOOGLE_API_KEY", "test-key"):
                    with patch("core.odiseo_bot.genai.Client") as mock_client_class:
                        mock_cached = MagicMock()
                        mock_cached.name = "cachedContents/test-ttl"
                        mock_cached.usage_metadata.total_token_count = 1700

                        mock_client_instance = MagicMock()
                        mock_client_instance.caches.create = AsyncMock(return_value=mock_cached)
                        mock_client_class.return_value = mock_client_instance

                        bot = OdiseoBot()

                        try:
                            await bot.initialize()
                        except Exception:
                            pass

                        # Verify create was called with correct TTL
                        call_args = mock_client_instance.caches.create.call_args
                        assert call_args is not None
                        # TTL should be timedelta(minutes=120)
                        ttl_arg = call_args.kwargs.get("ttl")
                        assert ttl_arg is not None
                        assert ttl_arg.total_seconds() == 120 * 60  # 120 minutes in seconds

    @pytest.mark.asyncio
    async def test_cache_creation_failure_graceful_fallback(self):
        """Test that bot falls back gracefully when cache creation fails."""
        with patch("config.settings.settings.ENABLE_CONTEXT_CACHING", True):
            with patch("config.settings.settings.GOOGLE_API_KEY", "test-key"):
                with patch("core.odiseo_bot.genai.Client") as mock_client_class:
                    # Simulate cache creation failure
                    mock_client_instance = MagicMock()
                    mock_client_instance.caches.create = AsyncMock(side_effect=Exception("Cache creation failed"))
                    mock_client_class.return_value = mock_client_instance

                    bot = OdiseoBot()

                    # Initialize should not crash despite cache failure
                    try:
                        await bot.initialize()
                    except Exception:
                        pass

                    # Verify bot falls back to no cache
                    assert bot.cached_content is None

                    # Verify generation config still works with system_instruction
                    assert bot._generation_config is not None
                    assert bot._generation_config.system_instruction is not None
