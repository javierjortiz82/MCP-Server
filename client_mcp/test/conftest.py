"""Pytest configuration and shared fixtures for client_mcp tests."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add client_mcp to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from config.settings import Settings

    # Just create an instance with overridden values (Pydantic v2 way)
    return Settings(
        GOOGLE_API_KEY="test-api-key-12345",
        ENABLE_THINKING=True,
        THINKING_BUDGET=1024,
        INCLUDE_THOUGHTS=False,
        ENABLE_RATE_LIMITING=False,  # Disable for tests
        ENABLE_CACHE=False,
        ENABLE_METRICS=True,
        ENABLE_VALIDATION=True,
    )


@pytest.fixture
def mock_gemini_client():
    """Mock Google Gemini client."""
    mock_client = MagicMock()
    mock_client.models.generate_content = AsyncMock()
    return mock_client


@pytest.fixture
def mock_mcp_connector():
    """Mock MCP connector."""
    connector = AsyncMock()
    connector.list_tools = AsyncMock(return_value=[])
    connector.call_tool = AsyncMock(return_value={"result": "test"})
    return connector


@pytest.fixture
def sample_mcp_tools():
    """Sample MCP tool definitions."""
    return [
        {
            "name": "search_products",
            "description": "Search for products by query",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "fetch_by_sku",
            "description": "Fetch product by SKU",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sku": {"type": "string", "description": "Product SKU"},
                },
                "required": ["sku"],
            },
        },
    ]


@pytest.fixture
def sample_gemini_response():
    """Sample Gemini API response."""
    from google.genai import types

    mock_part = MagicMock()
    mock_part.text = "Test response from Gemini"
    mock_part.function_call = None

    mock_content = MagicMock()
    mock_content.parts = [mock_part]

    mock_candidate = MagicMock()
    mock_candidate.content = mock_content

    mock_response = MagicMock()
    mock_response.candidates = [mock_candidate]

    return mock_response


@pytest.fixture
def sample_product():
    """Sample product data."""
    return {
        "id": 1,
        "sku": "LAPTOP-001",
        "name": "Gaming Laptop Pro",
        "description": "High-performance gaming laptop",
        "price": 1299.99,
        "category": "Laptops",
        "stock": 10,
    }


@pytest.fixture
def sample_products():
    """Sample list of products."""
    return [
        {
            "id": 1,
            "sku": "LAPTOP-001",
            "name": "Gaming Laptop Pro",
            "price": 1299.99,
        },
        {
            "id": 2,
            "sku": "LAPTOP-002",
            "name": "Business Laptop",
            "price": 899.99,
        },
        {
            "id": 3,
            "sku": "MOUSE-001",
            "name": "Gaming Mouse",
            "price": 49.99,
        },
    ]
