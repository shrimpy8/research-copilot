"""
Configuration management for Research Copilot.

Uses Pydantic Settings for type-safe configuration with environment variable support.
All configuration is loaded from environment variables with sensible defaults.
"""

from pathlib import Path
from typing import Literal, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings.

    All settings can be overridden via environment variables.
    Environment variables are case-insensitive and use underscore notation.

    Example:
        OLLAMA_BASE_URL=http://localhost:11434
        LOG_LEVEL=debug
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "production", "test"] = "development"
    log_level: Literal["debug", "info", "warn", "error"] = "info"
    log_format: Literal["json", "pretty"] = "pretty"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "ministral-3:8b"
    ollama_timeout_ms: int = 120000  # Increased from 60s to 120s for complex research queries
    ollama_max_retries: int = 3
    ollama_temperature: float = 0.4  # LLM temperature (0.0-1.0, lower = more focused)

    # MCP Server
    mcp_server_url: str = "http://localhost:3001"
    mcp_server_timeout_ms: int = 30000

    # Search
    search_provider: Literal["duckduckgo", "serper"] = "duckduckgo"
    search_api_key: Optional[str] = None
    search_max_results: int = 5
    search_timeout_ms: int = 30000  # 30 seconds for search requests

    # Fetch
    fetch_max_page_size: int = 50000
    fetch_timeout_ms: int = 30000  # 30 seconds for page fetches
    fetch_user_agent: str = "ResearchCopilot/1.0"

    # Notes
    notes_db_path: str = "./data/notes.db"

    # Feature Flags
    enable_tool_trace: bool = True
    enable_note_saving: bool = True
    enable_deep_dive_mode: bool = True

    # Development
    dev_mock_search: bool = False
    dev_mock_fetch: bool = False

    @field_validator("search_api_key")
    @classmethod
    def validate_search_api_key(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that API key is provided for providers that require it."""
        # Get the search_provider from the data being validated
        provider = info.data.get("search_provider", "duckduckgo")
        if provider == "serper" and not v:
            raise ValueError("SEARCH_API_KEY is required when using the serper provider")
        return v

    @field_validator("notes_db_path")
    @classmethod
    def ensure_db_directory(cls, v: str) -> str:
        """Ensure the database directory exists."""
        path = Path(v)
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @property
    def ollama_timeout_seconds(self) -> float:
        """Get Ollama timeout in seconds."""
        return self.ollama_timeout_ms / 1000

    @property
    def mcp_timeout_seconds(self) -> float:
        """Get MCP server timeout in seconds."""
        return self.mcp_server_timeout_ms / 1000

    @property
    def search_timeout_seconds(self) -> float:
        """Get search timeout in seconds."""
        return self.search_timeout_ms / 1000

    @property
    def fetch_timeout_seconds(self) -> float:
        """Get fetch timeout in seconds."""
        return self.fetch_timeout_ms / 1000

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.app_env == "test"


# Singleton instance - import this in other modules
settings = Settings()
