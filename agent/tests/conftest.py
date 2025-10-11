"""Pytest configuration and shared fixtures for Gemini Agent tests."""

import pytest


@pytest.fixture
def sample_api_key():
    """Provide a sample API key for testing."""
    return "test_api_key_123456789"


@pytest.fixture
def sample_prompt():
    """Provide a sample prompt for testing."""
    return "What is the capital of France?"


@pytest.fixture
def sample_system_prompt():
    """Provide a sample system prompt for testing."""
    return "You are a helpful assistant."
