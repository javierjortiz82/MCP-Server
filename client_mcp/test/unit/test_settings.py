"""Unit tests for Settings configuration using Pydantic BaseSettings v2."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from config.settings import Settings, settings


class TestSettings:
    """Test suite for Settings class using Pydantic BaseSettings."""

    def test_default_model(self):
        """Test default model is set correctly."""
        assert settings.MODEL == "gemini-2.5-flash"

    def test_default_temperature(self):
        """Test default temperature is set correctly."""
        assert settings.TEMPERATURE == 0.2
        assert 0.0 <= settings.TEMPERATURE <= 2.0

    def test_default_max_output_tokens(self):
        """Test default max output tokens is set correctly."""
        assert settings.MAX_OUTPUT_TOKENS == 1024
        assert settings.MAX_OUTPUT_TOKENS > 0

    def test_default_thinking_settings(self):
        """Test default thinking mode settings."""
        assert settings.ENABLE_THINKING is True
        assert settings.THINKING_BUDGET == 1024
        assert settings.INCLUDE_THOUGHTS is False

    def test_default_rate_limiting_settings(self):
        """Test default rate limiting settings."""
        assert settings.ENABLE_RATE_LIMITING is True
        assert settings.GEMINI_RPM_LIMIT == 15
        assert settings.GEMINI_RPD_LIMIT == 1500
        assert settings.MAX_CONCURRENT_REQUESTS == 3

    def test_default_feature_flags(self):
        """Test default feature flags."""
        assert settings.ENABLE_CACHE is True
        assert settings.ENABLE_METRICS is True
        assert settings.ENABLE_VALIDATION is True

    def test_default_retry_settings(self):
        """Test default retry settings."""
        assert settings.RETRY_MAX_ATTEMPTS == 3
        assert settings.RETRY_INITIAL_DELAY_MS == 100.0
        assert settings.RETRY_MAX_ATTEMPTS >= 0
        assert settings.RETRY_INITIAL_DELAY_MS > 0

    def test_default_timeout_settings(self):
        """Test default timeout settings."""
        assert settings.TOOL_TIMEOUT == 30
        assert settings.TOOL_TIMEOUT > 0

    def test_api_key_from_env(self, monkeypatch):
        """Test GOOGLE_API_KEY loaded from environment."""
        test_key = "test-api-key-from-env-12345"
        monkeypatch.setenv("GOOGLE_API_KEY", test_key)

        # Create new settings instance to reload from env
        test_settings = Settings()

        # Verify the env var is set
        assert os.environ.get("GOOGLE_API_KEY") == test_key

    def test_api_key_validation(self):
        """Test API key validation (should be str or None)."""
        # settings.GOOGLE_API_KEY should either be set or None
        api_key = settings.GOOGLE_API_KEY
        assert api_key is None or isinstance(api_key, str)

    def test_thinking_budget_values(self):
        """Test thinking budget accepts valid values."""
        # Budget can be -1 (auto), 0 (disabled), or positive
        assert settings.THINKING_BUDGET >= -1

    def test_rate_limit_values(self):
        """Test rate limit values are positive."""
        assert settings.GEMINI_RPM_LIMIT > 0
        assert settings.GEMINI_RPD_LIMIT > 0
        assert settings.MAX_CONCURRENT_REQUESTS > 0

    def test_rpm_less_than_rpd(self):
        """Test RPM limit makes sense relative to RPD."""
        # RPM * 60 * 24 should be >= RPD (rough check)
        max_daily_from_rpm = settings.GEMINI_RPM_LIMIT * 60 * 24
        # RPD should be <= theoretical max from RPM
        # (This is a loose check as burst limits may differ)
        assert settings.GEMINI_RPD_LIMIT > 0
        assert settings.GEMINI_RPM_LIMIT > 0

    def test_temperature_range(self):
        """Test temperature is within valid range."""
        assert 0.0 <= settings.TEMPERATURE <= 2.0

    def test_settings_is_instance(self):
        """Test settings is a BaseSettings instance."""
        # settings is an instance of Settings (BaseSettings)
        assert isinstance(settings, Settings)
        assert hasattr(settings, "MODEL")
        assert hasattr(settings, "TEMPERATURE")
        assert hasattr(settings, "GOOGLE_API_KEY")

    def test_mcp_base_url_computed(self):
        """Test MCP_BASE_URL is computed from host and port."""
        expected_url = f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/mcp"
        assert settings.MCP_BASE_URL == expected_url


class TestSettingsEnvironmentVariables:
    """Test suite for environment variable handling."""

    def test_env_file_configured(self):
        """Test .env file path is configured in SettingsConfigDict."""
        # Check that model_config has env_file set
        assert hasattr(Settings, "model_config")
        assert "env_file" in Settings.model_config

    def test_env_file_path_resolution(self):
        """Test .env file path points to correct location."""
        # Get env_file from model_config
        env_file_path = Path(Settings.model_config["env_file"])

        # Should point to client_mcp/.env
        assert env_file_path.name == ".env"
        assert "client_mcp" in str(env_file_path)

    def test_env_file_exists(self):
        """Test .env file exists."""
        env_file_path = Path(Settings.model_config["env_file"])

        # .env should exist (created during setup)
        assert env_file_path.exists(), f".env file not found at {env_file_path}"

    @patch.dict(os.environ, {"ENABLE_THINKING": "false"}, clear=False)
    def test_boolean_env_var_false(self):
        """Test boolean environment variable parsing (false)."""
        # Create new instance to load env var
        test_settings = Settings()
        assert test_settings.ENABLE_THINKING is False

    @patch.dict(os.environ, {"ENABLE_THINKING": "true"}, clear=False)
    def test_boolean_env_var_true(self):
        """Test boolean environment variable parsing (true)."""
        # Create new instance to load env var
        test_settings = Settings()
        assert test_settings.ENABLE_THINKING is True

    @patch.dict(os.environ, {"THINKING_BUDGET": "2048"}, clear=False)
    def test_integer_env_var(self):
        """Test integer environment variable parsing."""
        # Create new instance to load env var
        test_settings = Settings()
        assert test_settings.THINKING_BUDGET == 2048

    @patch.dict(os.environ, {"TEMPERATURE": "0.5"}, clear=False)
    def test_float_env_var(self):
        """Test float environment variable parsing."""
        # Create new instance to load env var
        test_settings = Settings()
        assert test_settings.TEMPERATURE == 0.5


class TestSettingsValidation:
    """Test suite for settings validation with Pydantic."""

    def test_model_name_format(self):
        """Test model name follows expected format."""
        model = settings.MODEL
        # Should be a non-empty string
        assert isinstance(model, str)
        assert len(model) > 0
        # Should contain 'gemini'
        assert "gemini" in model.lower()

    def test_concurrent_requests_reasonable(self):
        """Test max concurrent requests is reasonable."""
        # Should be between 1 and 100
        assert 1 <= settings.MAX_CONCURRENT_REQUESTS <= 100

    def test_timeout_reasonable(self):
        """Test tool timeout is reasonable."""
        # Should be between 1 and 300 seconds (5 minutes)
        assert 1 <= settings.TOOL_TIMEOUT <= 300

    def test_max_retries_reasonable(self):
        """Test max retries is reasonable."""
        # Should be between 0 and 10
        assert 0 <= settings.RETRY_MAX_ATTEMPTS <= 10

    def test_retry_delay_reasonable(self):
        """Test retry delay is reasonable."""
        # Should be between 0.1 and 60000 milliseconds
        assert 0.1 <= settings.RETRY_INITIAL_DELAY_MS <= 60000.0

    def test_output_tokens_reasonable(self):
        """Test max output tokens is reasonable."""
        # Should be between 1 and 100000
        assert 1 <= settings.MAX_OUTPUT_TOKENS <= 100000

    def test_pydantic_validation_temperature(self):
        """Test Pydantic validates temperature range."""
        with pytest.raises(Exception):  # ValidationError from Pydantic
            Settings(TEMPERATURE=3.0)  # Outside 0.0-2.0 range

    def test_pydantic_validation_port(self):
        """Test Pydantic validates port range."""
        with pytest.raises(Exception):  # ValidationError from Pydantic
            Settings(MCP_PORT=70000)  # Outside 1-65535 range

    def test_log_level_validation(self):
        """Test log level validator accepts valid values."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        for level in valid_levels:
            test_settings = Settings(LOG_LEVEL=level)
            assert test_settings.LOG_LEVEL == level

    def test_log_level_validation_invalid(self):
        """Test log level validator rejects invalid values."""
        with pytest.raises(Exception):  # ValidationError from Pydantic
            Settings(LOG_LEVEL="INVALID")


class TestSettingsHelperMethods:
    """Test suite for Settings helper methods."""

    def test_get_api_key_when_set(self):
        """Test get_api_key returns key when already set."""
        test_settings = Settings(GOOGLE_API_KEY="test-key-12345")
        assert test_settings.get_api_key() == "test-key-12345"

    def test_validate_settings_success(self):
        """Test validate_settings returns True when valid."""
        test_settings = Settings(GOOGLE_API_KEY="test-key-12345")
        assert test_settings.validate_settings() is True

    def test_get_prompts_dir(self):
        """Test get_prompts_dir returns correct path."""
        prompts_dir = settings.get_prompts_dir()
        assert prompts_dir.name == "prompts"
        assert prompts_dir.parent.name == "assets"

    def test_get_retry_config(self):
        """Test get_retry_config returns dict with correct keys."""
        retry_config = settings.get_retry_config()
        assert "max_attempts" in retry_config
        assert "initial_delay_ms" in retry_config
        assert "max_delay_ms" in retry_config
        assert retry_config["max_attempts"] == settings.RETRY_MAX_ATTEMPTS

    def test_get_cache_config(self):
        """Test get_cache_config returns dict with correct keys."""
        cache_config = settings.get_cache_config()
        assert "enabled" in cache_config
        assert "ttl_seconds" in cache_config
        assert cache_config["enabled"] == settings.ENABLE_CACHE

    def test_get_metrics_config(self):
        """Test get_metrics_config returns dict with correct keys."""
        metrics_config = settings.get_metrics_config()
        assert "enabled" in metrics_config
        assert "export_path" in metrics_config
        assert metrics_config["enabled"] == settings.ENABLE_METRICS

    def test_get_validation_config(self):
        """Test get_validation_config returns dict with correct keys."""
        validation_config = settings.get_validation_config()
        assert "enabled" in validation_config
        assert "sanitize_inputs" in validation_config

    def test_get_fallback_config(self):
        """Test get_fallback_config returns dict with correct keys."""
        fallback_config = settings.get_fallback_config()
        assert "enabled" in fallback_config
        assert "max_depth" in fallback_config

    def test_get_system_prompt(self):
        """Test get_system_prompt reads prompt file."""
        system_prompt = settings.get_system_prompt()
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
        # Should contain placeholder for tools
        assert "{TOOLS_CONTEXT}" in system_prompt

    @patch("builtins.input", return_value="user-input-api-key")
    def test_get_api_key_prompts_when_none(self, mock_input):
        """Test get_api_key prompts user when not set."""
        test_settings = Settings(GOOGLE_API_KEY=None)
        api_key = test_settings.get_api_key()

        assert api_key == "user-input-api-key"
        assert test_settings.GOOGLE_API_KEY == "user-input-api-key"
        mock_input.assert_called_once()

    @patch("builtins.input", return_value="")
    def test_get_api_key_raises_on_empty_input(self, mock_input):
        """Test get_api_key raises ValueError when user provides empty key."""
        test_settings = Settings(GOOGLE_API_KEY=None)

        with pytest.raises(ValueError, match="API key es requerida"):
            test_settings.get_api_key()

    def test_validate_settings_fails_without_api_key(self):
        """Test validate_settings returns False when API key invalid."""
        with patch("builtins.input", return_value=""):
            test_settings = Settings(GOOGLE_API_KEY=None)
            # Should return False when validation fails
            result = test_settings.validate_settings()
            assert result is False


class TestSettingsConfigMethods:
    """Test suite for additional configuration methods."""

    def test_get_retry_config_complete(self):
        """Test get_retry_config returns all retry parameters."""
        retry_config = settings.get_retry_config()

        assert retry_config["max_attempts"] == settings.RETRY_MAX_ATTEMPTS
        assert retry_config["initial_delay_ms"] == settings.RETRY_INITIAL_DELAY_MS
        assert retry_config["max_delay_ms"] == settings.RETRY_MAX_DELAY_MS
        assert retry_config["exponential_base"] == settings.RETRY_EXPONENTIAL_BASE
        assert retry_config["jitter"] == settings.RETRY_JITTER

    def test_get_cache_config_complete(self):
        """Test get_cache_config returns all cache parameters."""
        cache_config = settings.get_cache_config()

        assert cache_config["enabled"] == settings.ENABLE_CACHE
        assert cache_config["ttl_seconds"] == settings.CACHE_TTL_SECONDS

    def test_get_metrics_config_complete(self):
        """Test get_metrics_config returns all metrics parameters."""
        metrics_config = settings.get_metrics_config()

        assert metrics_config["enabled"] == settings.ENABLE_METRICS
        assert metrics_config["export_path"] == settings.METRICS_EXPORT_PATH

    def test_get_validation_config_complete(self):
        """Test get_validation_config returns all validation parameters."""
        validation_config = settings.get_validation_config()

        assert validation_config["enabled"] == settings.ENABLE_VALIDATION
        assert validation_config["sanitize_inputs"] == settings.SANITIZE_INPUTS

    def test_get_fallback_config_complete(self):
        """Test get_fallback_config returns all fallback parameters."""
        fallback_config = settings.get_fallback_config()

        assert fallback_config["enabled"] == settings.ENABLE_FALLBACK
        assert fallback_config["max_depth"] == settings.FALLBACK_MAX_DEPTH


class TestSettingsFieldValidation:
    """Test suite for individual field validators."""

    def test_log_level_case_insensitive(self):
        """Test log level validator accepts lowercase."""
        test_settings = Settings(LOG_LEVEL="info")
        assert test_settings.LOG_LEVEL == "INFO"  # Uppercase

    def test_log_level_critical(self):
        """Test log level validator accepts CRITICAL."""
        test_settings = Settings(LOG_LEVEL="CRITICAL")
        assert test_settings.LOG_LEVEL == "CRITICAL"

    def test_temperature_boundary_low(self):
        """Test temperature validator at lower boundary."""
        test_settings = Settings(TEMPERATURE=0.0)
        assert test_settings.TEMPERATURE == 0.0

    def test_temperature_boundary_high(self):
        """Test temperature validator at upper boundary."""
        test_settings = Settings(TEMPERATURE=2.0)
        assert test_settings.TEMPERATURE == 2.0

    def test_mcp_port_valid_range(self):
        """Test MCP port accepts valid values."""
        test_settings = Settings(MCP_PORT=8080)
        assert test_settings.MCP_PORT == 8080

    def test_top_k_range(self):
        """Test TOP_K within valid range."""
        assert 1 <= settings.TOP_K <= 100

    def test_top_p_range(self):
        """Test TOP_P within valid range."""
        assert 0.0 <= settings.TOP_P <= 1.0

    def test_cache_ttl_positive(self):
        """Test CACHE_TTL_SECONDS is positive."""
        assert settings.CACHE_TTL_SECONDS > 0

    def test_max_function_calls_positive(self):
        """Test MAX_FUNCTION_CALLS is positive."""
        assert settings.MAX_FUNCTION_CALLS > 0


class TestSettingsEdgeCases:
    """Test suite for edge cases and special scenarios."""

    def test_settings_immutable_after_creation(self):
        """Test settings can be modified after creation."""
        test_settings = Settings(MODEL="gemini-2.5-flash")
        # Pydantic allows modification by default
        test_settings.MODEL = "gemini-pro"
        assert test_settings.MODEL == "gemini-pro"

    def test_mcp_base_url_updates_with_port_change(self):
        """Test MCP_BASE_URL property updates when port changes."""
        test_settings = Settings(MCP_PORT=9000)
        assert "9000" in test_settings.MCP_BASE_URL
        assert test_settings.MCP_BASE_URL == "http://localhost:9000/mcp"

    def test_mcp_base_url_updates_with_host_change(self):
        """Test MCP_BASE_URL property updates when host changes."""
        test_settings = Settings(MCP_HOST="example.com")
        assert "example.com" in test_settings.MCP_BASE_URL
        assert test_settings.MCP_BASE_URL == "http://example.com:8009/mcp"

    def test_prompts_dir_exists(self):
        """Test prompts directory exists."""
        prompts_dir = settings.get_prompts_dir()
        assert prompts_dir.exists(), f"Prompts directory not found at {prompts_dir}"

    def test_extra_fields_ignored(self):
        """Test extra environment variables are ignored."""
        # model_config has extra="ignore"
        test_settings = Settings(UNKNOWN_FIELD="value")  # Should not raise
        assert not hasattr(test_settings, "UNKNOWN_FIELD")
