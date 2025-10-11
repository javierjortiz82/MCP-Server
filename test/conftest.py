"""
Pytest configuration and shared fixtures for Odiseo Bot tests.
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def mock_mcp_tools():
    """Mock MCP tools response for testing."""
    return [
        {
            "name": "search_products",
            "description": "Search for products in the database",
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
            "name": "get_product_details",
            "description": "Get product details by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID"}
                },
                "required": ["product_id"],
            },
        },
    ]


@pytest.fixture
def sample_product_data():
    """Sample product data for testing."""
    return {
        "id": "LAPTOP001",
        "name": "Gaming Laptop Pro",
        "price": 1299.99,
        "specs": {"cpu": "Intel i7", "ram": "16GB", "storage": "512GB SSD"},
        "in_stock": True,
    }


@pytest.fixture
def sample_products_list():
    """Sample products list for testing."""
    return [
        {"id": "LAPTOP001", "name": "Gaming Laptop", "price": 1299.99},
        {"id": "LAPTOP002", "name": "Business Laptop", "price": 899.99},
        {"id": "LAPTOP003", "name": "Budget Laptop", "price": 499.99},
    ]
