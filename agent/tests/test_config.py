"""Tests for configuration settings."""

import pytest

from gemini_agent.config import settings


class TestSettings:
    """Test suite for Settings class."""

    def test_settings_exists(self):
        """Test that settings object is available."""
        assert settings is not None

    def test_model_name_default(self):
        """Test that MODEL_NAME has a default value."""
        assert settings.MODEL_NAME is not None
        assert isinstance(settings.MODEL_NAME, str)

    def test_temperature_default(self):
        """Test that TEMPERATURE has a valid default value."""
        assert settings.TEMPERATURE is not None
        assert 0.0 <= settings.TEMPERATURE <= 2.0

    def test_log_level_default(self):
        """Test that LOG_LEVEL has a valid default value."""
        assert settings.LOG_LEVEL is not None
        assert settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def test_allowed_origins_list_property(self):
        """Test that allowed_origins_list property returns a list."""
        origins = settings.allowed_origins_list
        assert isinstance(origins, list)
        assert len(origins) > 0

    def test_log_max_bytes_property(self):
        """Test that log_max_bytes property returns correct byte value."""
        max_bytes = settings.log_max_bytes
        assert isinstance(max_bytes, int)
        assert max_bytes > 0
        # Should be MB converted to bytes
        assert max_bytes == settings.LOG_MAX_SIZE_MB * 1024 * 1024
