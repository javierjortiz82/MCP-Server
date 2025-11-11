"""Tests for the separated Gemini Agent module."""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add agent module to path
sys.path.insert(0, str(Path(__file__).parents[1] / "agent"))

from agent import GeminiAgent


class TestGeminiAgent:
    """Test suite for GeminiAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a GeminiAgent instance for testing."""
        return GeminiAgent(api_key="test-key", model_name="test-model")

    def test_initialization(self, agent):
        """Test agent initialization with correct parameters."""
        assert agent.api_key == "test-key"
        assert agent.model_name == "test-model"
        assert agent.client is None
        assert agent.conversation_history == []
        assert agent._generation_config is None

    @pytest.mark.asyncio
    async def test_initialize_client(self, agent):
        """Test client initialization."""
        with patch("agent.gemini_agent.genai.Client") as mock_client:
            await agent.initialize()
            mock_client.assert_called_once_with(api_key="test-key")
            assert agent._generation_config is not None

    def test_build_generation_config(self, agent):
        """Test generation configuration building."""
        config = agent._build_generation_config(
            temperature=0.5,
            top_k=50,
            top_p=0.95,
            max_output_tokens=4096,
        )
        assert config.temperature == 0.5
        assert config.top_k == 50
        assert config.top_p == 0.95
        assert config.max_output_tokens == 4096

    def test_clear_history(self, agent):
        """Test conversation history clearing."""
        # Add mock history
        agent.conversation_history = ["message1", "message2"]

        # Clear history
        agent.clear_history()

        assert agent.conversation_history == []

    def test_update_generation_config(self, agent):
        """Test updating generation configuration."""
        # Initialize first
        agent._generation_config = agent._build_generation_config()

        # Update config
        agent.update_generation_config(temperature=0.7, top_k=60)

        assert agent._generation_config.temperature == 0.7
        assert agent._generation_config.top_k == 60

    @pytest.mark.asyncio
    async def test_generate_response_without_client(self, agent):
        """Test that generate_response fails without initialized client."""
        with pytest.raises(RuntimeError, match="Gemini client not initialized"):
            await agent.generate_response("test prompt")

    @pytest.mark.asyncio
    async def test_cleanup(self, agent):
        """Test cleanup method."""
        # Setup some state
        agent.conversation_history = ["message1"]
        agent.client = Mock()
        agent._generation_config = Mock()

        # Cleanup
        await agent.cleanup()

        assert agent.conversation_history == []
        assert agent.client is None
        assert agent._generation_config is None

    def test_history_management(self, agent):
        """Test conversation history size management."""
        # Add many messages to history
        for i in range(25):
            agent.conversation_history.append(f"message_{i}")

        # Trigger size management (simulated in add_to_history)
        if len(agent.conversation_history) > 20:
            agent.conversation_history = agent.conversation_history[-20:]

        assert len(agent.conversation_history) == 20
        assert agent.conversation_history[0] == "message_5"
        assert agent.conversation_history[-1] == "message_24"


class TestGeminiAgentIntegration:
    """Integration tests for GeminiAgent."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not os.getenv("GOOGLE_API_KEY"), reason="No API key provided")
    async def test_real_initialization(self):
        """Test real initialization with actual API key."""
        import os

        api_key = os.getenv("GOOGLE_API_KEY")

        agent = GeminiAgent(api_key=api_key)
        await agent.initialize()

        assert agent.client is not None
        assert agent._generation_config is not None

        await agent.cleanup()

    @pytest.mark.asyncio
    async def test_mock_generate_response(self):
        """Test generate_response with mocked client."""
        agent = GeminiAgent(api_key="test-key")

        # Mock the client and its methods
        with patch("agent.gemini_agent.genai.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock the aio.models.generate_content method
            mock_response = AsyncMock()
            mock_response.candidates = [
                Mock(content=Mock(parts=[Mock(text="Test response")])),
            ]

            mock_client.aio.models.generate_content = AsyncMock(
                return_value=mock_response,
            )

            # Initialize and generate
            await agent.initialize()

            # Mock response generation
            with patch.object(
                agent.client.aio.models,
                "generate_content",
                return_value=mock_response,
            ):
                response = await agent.generate_response(
                    prompt="Test prompt",
                    system_prompt="Test system",
                )

            assert response.candidates[0].content.parts[0].text == "Test response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
