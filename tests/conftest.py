"""
Pytest configuration and shared fixtures for Research Copilot tests.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings(monkeypatch):
    """
    Fixture to provide mock settings for testing.

    Usage:
        def test_something(mock_settings):
            mock_settings(ollama_base_url="http://test:11434")
    """
    def _mock_settings(**kwargs):
        from src.utils.config import settings
        for key, value in kwargs.items():
            monkeypatch.setattr(settings, key, value)
    return _mock_settings


@pytest.fixture
async def ollama_client() -> AsyncGenerator:
    """
    Fixture to provide an Ollama client instance.

    Note: Requires Ollama to be running for integration tests.
    """
    from src.clients.ollama_client import OllamaClient

    client = OllamaClient()
    async with client:
        yield client


@pytest.fixture
async def mcp_client() -> AsyncGenerator:
    """
    Fixture to provide an MCP client instance.

    Note: Requires MCP server to be running for integration tests.
    """
    from src.clients.mcp_client import MCPClient

    client = MCPClient()
    async with client:
        yield client


@pytest.fixture
def sample_messages():
    """Fixture providing sample chat messages for testing."""
    return [
        {"role": "system", "content": "You are a helpful research assistant."},
        {"role": "user", "content": "What is the MCP protocol?"},
    ]


@pytest.fixture
def sample_note_data():
    """Fixture providing sample note data for testing."""
    return {
        "title": "Test Note",
        "content": "This is test content for the note.",
        "tags": ["test", "sample"],
        "source_urls": ["https://example.com"],
    }
