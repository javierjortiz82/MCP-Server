"""Integration tests for the complete Lab01-MCP system."""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parents[1] / "agent"))
sys.path.insert(0, str(Path(__file__).parents[1] / "client_mcp" / "src"))

from agent import GeminiAgent


class TestSystemIntegration:
    """Test complete system integration."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        agent = GeminiAgent(api_key="test-key")

        with patch("agent.gemini_agent.genai.Client"):
            await agent.initialize()
            assert agent.client is not None
            assert agent._generation_config is not None

    @pytest.mark.asyncio
    async def test_agent_response_generation(self):
        """Test agent can generate responses."""
        agent = GeminiAgent(api_key="test-key")

        with patch("agent.gemini_agent.genai.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Setup mock response
            mock_response = AsyncMock()
            mock_response.candidates = [
                Mock(content=Mock(parts=[Mock(text="Test response")])),
            ]

            mock_client.aio.models.generate_content = AsyncMock(
                return_value=mock_response,
            )

            await agent.initialize()

            # Test response generation
            response = await agent.generate_response(
                prompt="Test prompt",
                system_prompt="Test system",
            )

            assert response.candidates[0].content.parts[0].text == "Test response"

    @pytest.mark.asyncio
    async def test_conversation_history_management(self):
        """Test that conversation history is properly managed."""
        agent = GeminiAgent(api_key="test-key")

        # Initialize with mock
        with patch("agent.gemini_agent.genai.Client"):
            await agent.initialize()

        # Clear history
        agent.clear_history()
        assert len(agent.conversation_history) == 0

        # Simulate adding history
        from google.genai import types

        for i in range(25):
            user_msg = types.Content(
                role="user",
                parts=[types.Part(text=f"Message {i}")],
            )
            model_msg = types.Content(
                role="model",
                parts=[types.Part(text=f"Response {i}")],
            )
            agent.add_to_history(user_msg, model_msg)

        # Should maintain max 20 messages
        assert len(agent.conversation_history) == 20

    @pytest.mark.asyncio
    async def test_configuration_updates(self):
        """Test that configuration can be updated dynamically."""
        agent = GeminiAgent(api_key="test-key")

        with patch("agent.gemini_agent.genai.Client"):
            await agent.initialize()

        # Update configuration
        agent.update_generation_config(
            temperature=0.8,
            top_k=50,
            top_p=0.95,
            max_output_tokens=4096,
        )

        assert agent._generation_config.temperature == 0.8
        assert agent._generation_config.top_k == 50
        assert agent._generation_config.top_p == 0.95
        assert agent._generation_config.max_output_tokens == 4096

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test that cleanup properly releases resources."""
        agent = GeminiAgent(api_key="test-key")

        with patch("agent.gemini_agent.genai.Client"):
            await agent.initialize()

            # Add some state
            agent.conversation_history = ["test"]

            # Cleanup
            await agent.cleanup()

            assert agent.client is None
            assert agent._generation_config is None
            assert len(agent.conversation_history) == 0

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in agent."""
        agent = GeminiAgent(api_key="test-key")

        # Test without initialization
        with pytest.raises(RuntimeError, match="Gemini client not initialized"):
            await agent.generate_response("test")

        # Test initialization failure
        with (
            patch(
                "agent.gemini_agent.genai.Client",
                side_effect=Exception("API Error"),
            ),
            pytest.raises(Exception, match="API Error"),
        ):
            await agent.initialize()


class TestEndToEnd:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="No API key for E2E tests",
    )
    async def test_real_agent_flow(self):
        """Test real agent flow with actual API (requires API key)."""
        api_key = os.getenv("GOOGLE_API_KEY")

        agent = GeminiAgent(api_key=api_key)

        try:
            # Initialize
            await agent.initialize()

            # Generate simple response
            response = await agent.generate_response(
                prompt="Say 'Hello, World!' and nothing else",
                include_history=False,
            )

            # Check response
            assert response is not None
            assert response.candidates is not None
            assert len(response.candidates) > 0

        finally:
            # Always cleanup
            await agent.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling concurrent requests."""
        agent = GeminiAgent(api_key="test-key")

        with patch("agent.gemini_agent.genai.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Setup mock for concurrent responses
            async def mock_generate(model, contents, config, tools, tool_config):
                await asyncio.sleep(0.1)  # Simulate delay
                return AsyncMock(
                    candidates=[Mock(content=Mock(parts=[Mock(text="Response")]))],
                )

            mock_client.aio.models.generate_content = mock_generate

            await agent.initialize()

            # Launch concurrent requests
            tasks = [agent.generate_response(f"Query {i}") for i in range(5)]

            responses = await asyncio.gather(*tasks)

            assert len(responses) == 5
            for response in responses:
                assert response is not None


class TestValidation:
    """Validation tests for the integrated system."""

    def test_imports(self):
        """Test that all required modules can be imported."""
        try:
            # Test imports - not actually using them, just checking availability
            import google.genai  # noqa: F401

            import agent  # noqa: F401

            assert True
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_environment_variables(self):
        """Test that required environment variables are documented."""
        env_example = Path(__file__).parents[1] / ".env.example"
        assert env_example.exists(), ".env.example not found"

        with open(env_example) as f:
            content = f.read()

        required_vars = ["GOOGLE_API_KEY", "MCP_HOST", "MCP_PORT", "DB_HOST", "DB_PORT"]

        for var in required_vars:
            assert var in content, f"{var} not found in .env.example"

    def test_project_structure(self):
        """Test that project structure is correct."""
        project_root = Path(__file__).parents[1]

        required_dirs = [
            "agent",
            "client_mcp",
            "mcp",
            "SQL",
            "DockerConfig",
            "docs",
            "test",
            "scripts",
        ]

        for dir_name in required_dirs:
            dir_path = project_root / dir_name
            assert dir_path.exists(), f"Directory {dir_name} not found"
            assert dir_path.is_dir(), f"{dir_name} is not a directory"

    def test_key_files_exist(self):
        """Test that key files exist in the project."""
        project_root = Path(__file__).parents[1]

        key_files = [
            "README.md",
            "requirements.txt",
            ".env.example",
            "agent/gemini_agent.py",
            "agent/__init__.py",
            "scripts/deploy.sh",
        ]

        for file_path in key_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"File {file_path} not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
