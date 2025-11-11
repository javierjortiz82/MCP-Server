"""Tests for GeminiAgent class."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gemini_agent import GeminiAgent


class TestGeminiAgent:
    """Test suite for GeminiAgent class."""

    def test_agent_initialization(self, sample_api_key):
        """Test that GeminiAgent can be initialized with an API key."""
        agent = GeminiAgent(api_key=sample_api_key)

        assert agent is not None
        assert agent.api_key == sample_api_key
        assert agent.client is None  # Not initialized yet
        assert agent.conversation_history == []

    def test_agent_initialization_with_model(self, sample_api_key):
        """Test that GeminiAgent can be initialized with a custom model."""
        model_name = "gemini-1.5-pro"
        agent = GeminiAgent(api_key=sample_api_key, model_name=model_name)

        assert agent.model_name == model_name

    def test_clear_history(self, sample_api_key):
        """Test that conversation history can be cleared."""
        agent = GeminiAgent(api_key=sample_api_key)

        # Add some dummy history
        agent.conversation_history = ["msg1", "msg2"]

        # Clear history
        agent.clear_history()

        assert agent.conversation_history == []

    def test_agent_initialization_with_generation_params(self, sample_api_key):
        """Test that GeminiAgent can be initialized with custom generation params."""
        agent = GeminiAgent(api_key=sample_api_key, temperature=0.5, top_k=50, top_p=0.95)

        assert agent._generation_params["temperature"] == 0.5
        assert agent._generation_params["top_k"] == 50
        assert agent._generation_params["top_p"] == 0.95
