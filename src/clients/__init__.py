"""External service clients for Research Copilot."""

from src.clients.mcp_client import MCPClient, MCPHealthStatus, ToolResult
from src.clients.ollama_client import (
    ChatMessage,
    ChatResponse,
    OllamaClient,
    OllamaHealthStatus,
)

__all__ = [
    "OllamaClient",
    "OllamaHealthStatus",
    "ChatMessage",
    "ChatResponse",
    "MCPClient",
    "MCPHealthStatus",
    "ToolResult",
]
