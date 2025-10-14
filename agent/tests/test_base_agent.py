"""Unit tests for BaseAgent abstract class.

This test suite validates the core functionality of BaseAgent including:
- Abstract methods enforcement
- Initialization and lifecycle
- Conversation history management
- Generation configuration
- Error handling

Author: Lab01-MCP Team
Created: 2025-10-11
"""

# Add src to path
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

agent_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(agent_src))

from gemini_agent.base_agent import BaseAgent
from gemini_agent.config import settings

# ============================================================================
# Test Fixtures and Helper Classes
# ============================================================================


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    @property
    def agent_name(self) -> str:
        return "test_agent"

    def get_system_prompt(self, **kwargs) -> str:
        return "Test system prompt for testing"


class TestBaseAgent:
    """Test suite for BaseAgent class."""

    # ========================================================================
    # Test: Abstract Methods Enforcement
    # ========================================================================

    def test_cannot_instantiate_abstract_base(self):
        """Test that BaseAgent cannot be instantiated directly."""
        with pytest.raises(TypeError) as excinfo:
            BaseAgent()  # Should fail - abstract class

        assert "abstract" in str(excinfo.value).lower()

    def test_must_implement_agent_name(self):
        """Test that subclass must implement agent_name property."""

        class IncompleteAgent(BaseAgent):
            def get_system_prompt(self, **kwargs) -> str:
                return "prompt"

        with pytest.raises(TypeError) as excinfo:
            IncompleteAgent()

        assert "agent_name" in str(excinfo.value).lower()

    def test_must_implement_get_system_prompt(self):
        """Test that subclass must implement get_system_prompt method."""

        class IncompleteAgent(BaseAgent):
            @property
            def agent_name(self) -> str:
                return "test"

        with pytest.raises(TypeError) as excinfo:
            IncompleteAgent()

        assert "get_system_prompt" in str(excinfo.value).lower()

    # ========================================================================
    # Test: Initialization
    # ========================================================================

    def test_initialization_default_values(self):
        """Test that agent initializes with default values."""
        agent = ConcreteAgent()

        assert agent.api_key == settings.GOOGLE_API_KEY
        assert agent.model_name == settings.MODEL
        assert agent.mcp_tools == []
        assert agent.client is None
        assert agent.generation_config is None
        assert agent.conversation_history == []

    def test_initialization_custom_values(self):
        """Test that agent initializes with custom values."""
        custom_tools = [MagicMock(spec=types.FunctionDeclaration)]
        agent = ConcreteAgent(
            api_key="custom-key",
            model_name="custom-model",
            mcp_tools=custom_tools,
            temperature=0.8,
        )

        assert agent.api_key == "custom-key"
        assert agent.model_name == "custom-model"
        assert agent.mcp_tools == custom_tools
        assert agent._generation_params["temperature"] == 0.8

    def test_logger_initialized(self):
        """Test that logger is initialized with agent name."""
        agent = ConcreteAgent()

        assert agent.logger is not None
        # Logger name should include agent_name
        assert hasattr(agent.logger, "name")

    # ========================================================================
    # Test: Agent Properties
    # ========================================================================

    def test_agent_name_property(self):
        """Test that agent_name property returns correct value."""
        agent = ConcreteAgent()
        assert agent.agent_name == "test_agent"

    def test_get_system_prompt_returns_string(self):
        """Test that get_system_prompt returns a string."""
        agent = ConcreteAgent()
        prompt = agent.get_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert prompt == "Test system prompt for testing"

    # ========================================================================
    # Test: Client Initialization
    # ========================================================================

    @pytest.mark.asyncio
    async def test_initialize_creates_client(self):
        """Test that initialize() creates Gemini client."""
        agent = ConcreteAgent()

        with patch("google.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            await agent.initialize()

            # Verify client was created
            mock_client_class.assert_called_once_with(api_key=settings.GOOGLE_API_KEY)
            assert agent.client == mock_client

    @pytest.mark.asyncio
    async def test_initialize_creates_generation_config(self):
        """Test that initialize() creates generation config."""
        agent = ConcreteAgent()

        with patch("google.genai.Client"):
            await agent.initialize()

            # Verify generation config was created
            assert agent.generation_config is not None
            assert isinstance(agent.generation_config, types.GenerateContentConfig)

    # ========================================================================
    # Test: Conversation History Management
    # ========================================================================

    def test_clear_history(self):
        """Test that clear_history() clears conversation history."""
        agent = ConcreteAgent()

        # Add some history
        agent.conversation_history = [
            types.Content(role="user", parts=[types.Part(text="test1")]),
            types.Content(role="model", parts=[types.Part(text="test2")]),
        ]

        assert len(agent.conversation_history) == 2

        # Clear history
        agent.clear_history()

        assert len(agent.conversation_history) == 0

    def test_get_history_length(self):
        """Test that get_history_length() returns correct count."""
        agent = ConcreteAgent()

        assert agent.get_history_length() == 0

        # Add history
        agent.conversation_history = [
            types.Content(role="user", parts=[types.Part(text="test1")]),
            types.Content(role="model", parts=[types.Part(text="test2")]),
            types.Content(role="user", parts=[types.Part(text="test3")]),
        ]

        assert agent.get_history_length() == 3

    # ========================================================================
    # Test: Generation Configuration
    # ========================================================================

    def test_build_generation_config_default_params(self):
        """Test that _build_generation_config uses default settings."""
        agent = ConcreteAgent()
        config = agent._build_generation_config()

        assert config.temperature == settings.TEMPERATURE
        assert config.top_k == settings.TOP_K
        assert config.top_p == settings.TOP_P
        assert config.max_output_tokens == settings.MAX_OUTPUT_TOKENS

    def test_build_generation_config_custom_params(self):
        """Test that _build_generation_config uses custom params."""
        agent = ConcreteAgent()
        config = agent._build_generation_config(
            temperature=0.9, top_k=100, top_p=0.99, max_output_tokens=4096
        )

        assert config.temperature == 0.9
        assert config.top_k == 100
        assert config.top_p == 0.99
        assert config.max_output_tokens == 4096

    def test_build_generation_config_no_tools_by_default(self):
        """Test that config has no tools by default."""
        agent = ConcreteAgent()
        config = agent._build_generation_config()

        # BaseAgent default config should not have tools
        assert config.tools is None

    # ========================================================================
    # Test: Content Building
    # ========================================================================

    def test_build_contents_includes_system_prompt(self):
        """Test that _build_contents includes system prompt."""
        agent = ConcreteAgent()
        contents = agent._build_contents(query="Test query", include_history=False)

        # Should have at least 3 contents: system, acknowledgment, query
        assert len(contents) >= 3

        # First should be system prompt
        assert contents[0].role == "user"
        assert "Test system prompt" in contents[0].parts[0].text

        # Second should be model acknowledgment
        assert contents[1].role == "model"

        # Last should be user query
        assert contents[-1].role == "user"
        assert contents[-1].parts[0].text == "Test query"

    def test_build_contents_includes_history(self):
        """Test that _build_contents includes conversation history."""
        agent = ConcreteAgent()

        # Add history
        agent.conversation_history = [
            types.Content(role="user", parts=[types.Part(text="previous query")]),
            types.Content(role="model", parts=[types.Part(text="previous response")]),
        ]

        contents = agent._build_contents(query="New query", include_history=True)

        # Should include history (system + ack + 2 history + query = 5)
        assert len(contents) == 5

        # Check history is included
        assert contents[2].parts[0].text == "previous query"
        assert contents[3].parts[0].text == "previous response"

    def test_build_contents_excludes_history_when_requested(self):
        """Test that _build_contents excludes history when include_history=False."""
        agent = ConcreteAgent()

        # Add history
        agent.conversation_history = [
            types.Content(role="user", parts=[types.Part(text="previous query")]),
            types.Content(role="model", parts=[types.Part(text="previous response")]),
        ]

        contents = agent._build_contents(query="New query", include_history=False)

        # Should not include history (system + ack + query = 3)
        assert len(contents) == 3

    # ========================================================================
    # Test: Cleanup
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cleanup_clears_resources(self):
        """Test that cleanup() clears all resources."""
        agent = ConcreteAgent()

        # Set up some state
        agent.conversation_history = [
            types.Content(role="user", parts=[types.Part(text="test")]),
        ]
        agent.client = MagicMock()
        agent.generation_config = MagicMock()

        # Cleanup
        await agent.cleanup()

        # Verify cleanup
        assert len(agent.conversation_history) == 0
        assert agent.client is None
        assert agent.generation_config is None

    # ========================================================================
    # Test: String Representation
    # ========================================================================

    def test_repr(self):
        """Test that __repr__ returns meaningful string."""
        agent = ConcreteAgent()
        repr_str = repr(agent)

        assert "ConcreteAgent" in repr_str
        assert agent.model_name in repr_str

    # ========================================================================
    # Test: Error Handling
    # ========================================================================

    @pytest.mark.asyncio
    async def test_generate_response_requires_initialization(self):
        """Test that generate_response raises error if not initialized."""
        agent = ConcreteAgent()

        with pytest.raises(RuntimeError) as excinfo:
            await agent.generate_response("Test query")

        assert "not initialized" in str(excinfo.value).lower()

    # ========================================================================
    # Test: History Trimming (Auto-limit to 20 items)
    # ========================================================================

    def test_history_auto_trim_in_build_contents(self):
        """Test that history is automatically trimmed when building contents."""
        agent = ConcreteAgent()

        # Add 25 items to history (exceeds limit of 20)
        for i in range(25):
            role = "user" if i % 2 == 0 else "model"
            agent.conversation_history.append(
                types.Content(role=role, parts=[types.Part(text=f"msg{i}")])
            )

        assert len(agent.conversation_history) == 25

        # Build contents should not trim (trimming happens in generate_response)
        contents = agent._build_contents("test", include_history=True)

        # Contents should include all history + system + ack + query
        assert len(contents) == 25 + 3

    # ========================================================================
    # Test: Custom Generation Parameters
    # ========================================================================

    def test_custom_generation_params_stored(self):
        """Test that custom generation params are stored."""
        agent = ConcreteAgent(temperature=0.5, top_k=25, top_p=0.85)

        assert agent._generation_params["temperature"] == 0.5
        assert agent._generation_params["top_k"] == 25
        assert agent._generation_params["top_p"] == 0.85
