"""
MCP (Model Context Protocol) client for Research Copilot.

Provides async communication with the MCP server via JSON-RPC 2.0 over HTTP POST.
Supports all MCP tools: web_search, fetch_page, save_note, list_notes, get_note.
"""

import uuid
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from src.errors import ErrorCodes, MCPError
from src.utils.validators import sanitize_search_query, validate_url
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger("research_copilot.mcp")


@dataclass
class MCPHealthStatus:
    """Status of the MCP server."""

    available: bool
    tools: list[str] | None = None
    error: Optional[str] = None
    search_provider: Optional[str] = None  # "duckduckgo" or "serper"


@dataclass
class ToolResult:
    """Result from executing an MCP tool."""

    success: bool
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0


class MCPClient:
    """
    Async client for MCP server communication via JSON-RPC 2.0.

    Provides methods for:
    - Health checking and tool discovery
    - Executing MCP tools with proper error handling
    - Request tracing with request IDs

    Usage:
        client = MCPClient()
        async with client:
            if await client.is_available():
                result = await client.call_tool("web_search", {"query": "MCP protocol"})
    """

    # Known MCP tools (validated against server on connect)
    TOOLS = ["web_search", "fetch_page", "save_note", "list_notes", "get_note"]

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        """
        Initialize the MCP client.

        Args:
            base_url: MCP server base URL (default from settings)
            timeout_seconds: Request timeout in seconds (default from settings)
        """
        self.base_url = base_url or settings.mcp_server_url
        self.timeout_seconds = timeout_seconds or settings.mcp_timeout_seconds
        self._client: Optional[httpx.AsyncClient] = None
        self._available_tools: list[str] = []

    async def __aenter__(self) -> "MCPClient":
        """Enter async context and create HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout_seconds),
            headers={"Content-Type": "application/json"},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context and close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get the HTTP client, creating one if necessary."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout_seconds),
                headers={"Content-Type": "application/json"},
            )
        return self._client

    def _make_jsonrpc_request(
        self,
        method: str,
        params: dict[str, Any],
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a JSON-RPC 2.0 request object.

        Args:
            method: The method name (tool name)
            params: The method parameters
            request_id: Optional request ID (generated if not provided)

        Returns:
            JSON-RPC 2.0 request dictionary
        """
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id or str(uuid.uuid4()),
        }

    def _parse_jsonrpc_response(
        self,
        response_data: dict[str, Any],
    ) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        """
        Parse a JSON-RPC 2.0 response.

        Args:
            response_data: The response data from the server

        Returns:
            Tuple of (result, error_message)
        """
        if "error" in response_data:
            error = response_data["error"]
            error_message = error.get("message", "Unknown error")
            if "data" in error:
                error_message += f": {error['data']}"
            return None, error_message

        return response_data.get("result"), None

    async def health(self) -> MCPHealthStatus:
        """
        Check MCP server health and discover available tools.

        Returns:
            MCPHealthStatus with availability and tool list

        Note:
            Does not raise exceptions - returns status with available=False on error
        """
        try:
            client = self._get_client()

            # Send a list_tools request to check health and discover tools
            request = self._make_jsonrpc_request("tools/list", {})
            response = await client.post("/mcp", json=request)

            if response.status_code != 200:
                return MCPHealthStatus(
                    available=False,
                    error=f"Unexpected status code: {response.status_code}",
                )

            data = response.json()
            result, error = self._parse_jsonrpc_response(data)

            if error:
                return MCPHealthStatus(
                    available=False,
                    error=error,
                )

            # Extract tool names from the response
            tools = []
            if result and "tools" in result:
                tools = [tool.get("name") for tool in result["tools"] if "name" in tool]

            self._available_tools = tools

            # Also fetch search provider from /health endpoint
            search_provider = None
            try:
                health_response = await client.get("/health")
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    search_provider = health_data.get("search_provider")
            except Exception:
                pass  # Non-critical, continue without search provider info

            return MCPHealthStatus(
                available=True,
                tools=tools,
                search_provider=search_provider,
            )

        except httpx.ConnectError as e:
            logger.debug(f"MCP server connection error: {e}")
            return MCPHealthStatus(
                available=False,
                error="Cannot connect to MCP server. Is it running?",
            )
        except httpx.TimeoutException:
            logger.debug("MCP server health check timed out")
            return MCPHealthStatus(
                available=False,
                error="Connection timed out",
            )
        except Exception as e:
            logger.exception("Unexpected error checking MCP server health")
            return MCPHealthStatus(
                available=False,
                error=str(e),
            )

    async def is_available(self) -> bool:
        """
        Quick check if MCP server is available.

        Returns:
            True if MCP server is responding, False otherwise
        """
        health = await self.health()
        return health.available

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        request_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Call an MCP tool with the given arguments.

        Args:
            tool_name: Name of the tool to call (e.g., "web_search")
            arguments: Tool-specific arguments
            request_id: Optional request ID for tracing

        Returns:
            ToolResult with success status, data, or error

        Raises:
            MCPError: If the tool call fails
        """
        import time

        start_time = time.time()
        request_id = request_id or str(uuid.uuid4())

        logger.info(
            f"Calling MCP tool: {tool_name}",
            extra={
                "request_id": request_id,
                "tool_name": tool_name,
                "arguments": arguments,
            },
        )

        try:
            client = self._get_client()

            # Create JSON-RPC request for tool execution
            request = self._make_jsonrpc_request(
                "tools/call",
                {"name": tool_name, "arguments": arguments},
                request_id,
            )

            response = await client.post("/mcp", json=request)
            duration_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                raise MCPError(
                    code=ErrorCodes.MCP_TOOL_FAILED,
                    message=f"MCP server returned status {response.status_code}",
                    tool=tool_name,
                )

            data = response.json()
            result, error = self._parse_jsonrpc_response(data)

            if error:
                logger.warning(
                    f"MCP tool error: {tool_name} - {error}",
                    extra={
                        "request_id": request_id,
                        "tool_name": tool_name,
                        "duration_ms": duration_ms,
                        "success": False,
                    },
                )
                return ToolResult(
                    success=False,
                    error=error,
                    duration_ms=duration_ms,
                )

            logger.info(
                f"MCP tool completed: {tool_name}",
                extra={
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "duration_ms": duration_ms,
                    "success": True,
                },
            )

            return ToolResult(
                success=True,
                data=result,
                duration_ms=duration_ms,
            )

        except MCPError:
            raise
        except httpx.ConnectError:
            raise MCPError(
                code=ErrorCodes.MCP_SERVER_UNAVAILABLE,
                message="Cannot connect to MCP server",
                suggestion="Make sure the MCP server is running: cd mcp_server && npm start",
            )
        except httpx.TimeoutException:
            raise MCPError(
                code=ErrorCodes.MCP_TOOL_FAILED,
                message=f"MCP tool '{tool_name}' timed out",
                tool=tool_name,
                suggestion="Try again or check MCP server logs",
            )

    # Convenience methods for specific tools

    async def web_search(
        self,
        query: str,
        limit: int = 3,
        request_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Search the web using the MCP web_search tool.

        Args:
            query: Search query
            limit: Maximum results (1-5)
            request_id: Optional request ID for tracing

        Returns:
            ToolResult with search results
        """
        sanitized = sanitize_search_query(query)
        return await self.call_tool(
            "web_search",
            {"query": sanitized, "limit": min(max(limit, 1), 5)},
            request_id,
        )

    async def fetch_page(
        self,
        url: str,
        max_chars: int = 8000,
        extract_mode: str = "text",
        request_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Fetch and extract content from a URL using the MCP fetch_page tool.

        Args:
            url: URL to fetch
            max_chars: Maximum content length
            extract_mode: Output format ("text" or "markdown")
            request_id: Optional request ID for tracing

        Returns:
            ToolResult with page content
        """
        valid, error = validate_url(url)
        if not valid:
            raise MCPError(
                code=ErrorCodes.INVALID_URL,
                message=error,
                suggestion="Provide a valid http(s) URL.",
            )

        return await self.call_tool(
            "fetch_page",
            {"url": url, "max_chars": max_chars, "extract_mode": extract_mode},
            request_id,
        )

    async def save_note(
        self,
        title: str,
        content: str,
        tags: list[str],
        source_urls: list[str] | None = None,
        request_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Save a research note using the MCP save_note tool.

        Args:
            title: Note title
            content: Note content
            tags: List of tags
            source_urls: Optional list of source URLs
            request_id: Optional request ID for tracing

        Returns:
            ToolResult with saved note info
        """
        return await self.call_tool(
            "save_note",
            {
                "title": title,
                "content": content,
                "tags": tags,
                "source_urls": source_urls or [],
            },
            request_id,
        )

    async def list_notes(
        self,
        query: Optional[str] = None,
        tags: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        request_id: Optional[str] = None,
    ) -> ToolResult:
        """
        List saved notes using the MCP list_notes tool.

        Args:
            query: Optional search query
            tags: Optional tag filter
            limit: Maximum results
            offset: Pagination offset
            request_id: Optional request ID for tracing

        Returns:
            ToolResult with note list
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if query:
            params["query"] = query
        if tags:
            params["tags"] = tags

        return await self.call_tool("list_notes", params, request_id)

    async def get_note(
        self,
        note_id: str,
        request_id: Optional[str] = None,
    ) -> ToolResult:
        """
        Get a specific note using the MCP get_note tool.

        Args:
            note_id: Note ID
            request_id: Optional request ID for tracing

        Returns:
            ToolResult with note content
        """
        return await self.call_tool(
            "get_note",
            {"id": note_id},
            request_id,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
