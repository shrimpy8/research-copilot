"""Unit tests for configuration module."""

import pytest


class TestSettings:
    """Tests for the Settings configuration class."""

    def test_settings_loads(self):
        """Test that settings loads without errors."""
        from src.utils.config import settings

        assert settings is not None
        assert settings.app_env in ("development", "production", "test")

    def test_default_ollama_settings(self):
        """Test default Ollama configuration values."""
        from src.utils.config import settings

        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.ollama_timeout_ms == 60000
        assert settings.ollama_max_retries == 3

    def test_default_mcp_settings(self):
        """Test default MCP configuration values."""
        from src.utils.config import settings

        assert settings.mcp_server_url == "http://localhost:3001"
        assert settings.mcp_server_timeout_ms == 30000

    def test_timeout_properties(self):
        """Test timeout conversion properties."""
        from src.utils.config import settings

        assert settings.ollama_timeout_seconds == settings.ollama_timeout_ms / 1000
        assert settings.mcp_timeout_seconds == settings.mcp_server_timeout_ms / 1000
        assert settings.search_timeout_seconds == settings.search_timeout_ms / 1000
        assert settings.fetch_timeout_seconds == settings.fetch_timeout_ms / 1000

    def test_environment_checks(self):
        """Test environment check properties."""
        from src.utils.config import settings

        # Only one should be true
        env_flags = [settings.is_development, settings.is_production, settings.is_test]
        assert sum(env_flags) == 1

    def test_feature_flags_default_true(self):
        """Test that feature flags default to enabled."""
        from src.utils.config import settings

        assert settings.enable_tool_trace is True
        assert settings.enable_note_saving is True
        assert settings.enable_deep_dive_mode is True

    def test_dev_flags_default_false(self):
        """Test that dev mock flags default to disabled."""
        from src.utils.config import settings

        assert settings.dev_mock_search is False
        assert settings.dev_mock_fetch is False
