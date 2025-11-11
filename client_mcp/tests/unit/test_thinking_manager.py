"""Unit tests for ThinkingManager."""

from unittest.mock import MagicMock

from core.thinking_manager import ThinkingManager


class TestThinkingManager:
    """Test suite for ThinkingManager class."""

    def test_initialization_enabled(self):
        """Test ThinkingManager initialization with thinking enabled."""
        manager = ThinkingManager(enable_thinking=True, thinking_budget=1024, include_thoughts=False)

        assert manager.enable_thinking is True
        assert manager.thinking_budget == 1024
        assert manager.include_thoughts is False

    def test_initialization_disabled(self):
        """Test ThinkingManager initialization with thinking disabled."""
        manager = ThinkingManager(enable_thinking=False, thinking_budget=0, include_thoughts=False)

        assert manager.enable_thinking is False
        assert manager.thinking_budget == 0

    def test_get_thinking_config_enabled(self):
        """Test get_thinking_config returns ThinkingConfig when enabled."""
        manager = ThinkingManager(enable_thinking=True, thinking_budget=1024, include_thoughts=False)

        config = manager.get_thinking_config()

        assert config is not None
        assert config.thinking_budget == 1024
        assert config.include_thoughts is False

    def test_get_thinking_config_disabled(self):
        """Test get_thinking_config returns None when disabled."""
        manager = ThinkingManager(enable_thinking=False, thinking_budget=0, include_thoughts=False)

        config = manager.get_thinking_config()

        assert config is None

    def test_extract_thoughts_with_thoughts(self):
        """Test extracting thoughts from response with thoughts."""
        manager = ThinkingManager(enable_thinking=True, thinking_budget=1024, include_thoughts=True)

        # Mock response with thoughts
        mock_part = MagicMock()
        mock_part.thought = True
        mock_part.text = "This is my reasoning process"

        mock_content = MagicMock()
        mock_content.parts = [mock_part]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        thoughts = manager.extract_thoughts(mock_response)

        assert len(thoughts) == 1
        assert thoughts[0] == "This is my reasoning process"

    def test_extract_thoughts_without_thoughts(self):
        """Test extracting thoughts from response without thoughts."""
        manager = ThinkingManager(enable_thinking=True, thinking_budget=1024, include_thoughts=True)

        # Mock response without thoughts
        mock_part = MagicMock()
        mock_part.thought = False
        mock_part.text = "Regular response"

        mock_content = MagicMock()
        mock_content.parts = [mock_part]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        thoughts = manager.extract_thoughts(mock_response)

        assert len(thoughts) == 0

    def test_extract_thoughts_empty_response(self):
        """Test extracting thoughts from empty response."""
        manager = ThinkingManager(enable_thinking=True, thinking_budget=1024, include_thoughts=True)

        thoughts = manager.extract_thoughts(None)
        assert len(thoughts) == 0

    def test_format_thoughts_for_display(self):
        """Test formatting thoughts for display."""
        manager = ThinkingManager(enable_thinking=True, thinking_budget=1024, include_thoughts=True)

        thoughts = ["First thought", "Second thought", "Third thought"]

        formatted = manager.format_thoughts_for_display(thoughts)

        assert "💭 Model Reasoning:" in formatted
        assert "1. First thought" in formatted
        assert "2. Second thought" in formatted
        assert "3. Third thought" in formatted

    def test_format_thoughts_empty_list(self):
        """Test formatting empty thoughts list."""
        manager = ThinkingManager(enable_thinking=True, thinking_budget=1024, include_thoughts=True)

        formatted = manager.format_thoughts_for_display([])
        assert formatted == ""

    def test_is_thinking_enabled(self):
        """Test is_thinking_enabled method."""
        manager_enabled = ThinkingManager(enable_thinking=True, thinking_budget=1024, include_thoughts=False)
        assert manager_enabled.is_thinking_enabled() is True

        manager_disabled = ThinkingManager(enable_thinking=False, thinking_budget=0, include_thoughts=False)
        assert manager_disabled.is_thinking_enabled() is False

        manager_zero_budget = ThinkingManager(enable_thinking=True, thinking_budget=0, include_thoughts=False)
        assert manager_zero_budget.is_thinking_enabled() is False

    def test_get_stats(self):
        """Test get_stats returns correct statistics."""
        manager = ThinkingManager(enable_thinking=True, thinking_budget=1024, include_thoughts=False)

        stats = manager.get_stats()

        assert stats["thinking_enabled"] is True
        assert stats["thinking_budget"] == 1024
        assert stats["include_thoughts"] is False
        assert stats["budget_type"] == "fixed"

    def test_get_stats_auto_budget(self):
        """Test get_stats with auto budget."""
        manager = ThinkingManager(enable_thinking=True, thinking_budget=-1, include_thoughts=False)

        stats = manager.get_stats()
        assert stats["budget_type"] == "auto"

    def test_get_stats_disabled(self):
        """Test get_stats when disabled."""
        manager = ThinkingManager(enable_thinking=False, thinking_budget=0, include_thoughts=False)

        stats = manager.get_stats()
        assert stats["budget_type"] == "disabled"
