# Research Copilot API Documentation

> Complete API reference for the Research Copilot Python components.

---

## Table of Contents

1. [Orchestrator](#orchestrator)
2. [Ollama Client](#ollama-client)
3. [MCP Client](#mcp-client)
4. [Models](#models)
5. [Error Handling](#error-handling)
6. [Configuration](#configuration)

---

## Orchestrator

The `Orchestrator` class manages the tool-calling loop between the LLM and MCP tools.

### Location
`src/agent/orchestrator.py`

### Basic Usage

```python
import asyncio
from src.agent.orchestrator import Orchestrator

async def main():
    # Create orchestrator with default settings
    orch = Orchestrator(research_mode="quick")

    # Execute a research query
    response = await orch.research("What is the MCP protocol?")

    print(response.content)
    print(f"Sources: {len(response.sources)}")
    print(f"Tool calls: {len(response.tool_trace)}")

asyncio.run(main())
```

### Constructor

```python
Orchestrator(
    ollama_client: Optional[OllamaClient] = None,
    mcp_client: Optional[MCPClient] = None,
    model: Optional[str] = None,
    research_mode: str = "quick"
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ollama_client` | `OllamaClient` | `None` | Custom Ollama client (creates one if not provided) |
| `mcp_client` | `MCPClient` | `None` | Custom MCP client (creates one if not provided) |
| `model` | `str` | Config default | LLM model to use (e.g., `llama3.2:3b`) |
| `research_mode` | `str` | `"quick"` | Research mode: `"quick"` or `"deep"` |

### Methods

#### `research()`

Execute a research query with tool-calling support.

```python
async def research(
    query: str,
    on_tool_start: Optional[Callable[[str, Dict], None]] = None,
    on_tool_complete: Optional[Callable[[str, Dict, bool], None]] = None,
    on_text_chunk: Optional[Callable[[str], None]] = None
) -> ResearchResponse
```

**Parameters:**
- `query`: The user's research question
- `on_tool_start`: Callback when a tool starts executing
- `on_tool_complete`: Callback when a tool completes
- `on_text_chunk`: Callback for streaming text chunks

**Returns:** `ResearchResponse` with content, sources, and tool trace

**Example with callbacks:**

```python
def on_tool_start(tool_name, args):
    print(f"Starting: {tool_name}")

def on_tool_complete(tool_name, result, success):
    print(f"Completed: {tool_name} (success={success})")

response = await orch.research(
    "What is Python?",
    on_tool_start=on_tool_start,
    on_tool_complete=on_tool_complete
)
```

#### `research_stream()`

Streaming version that yields chunks as they arrive.

```python
async def research_stream(
    query: str,
    on_tool_start: Optional[Callable[[str, Dict], None]] = None,
    on_tool_complete: Optional[Callable[[str, Dict, bool], None]] = None
) -> AsyncIterator[str]
```

**Example:**

```python
async for chunk in orch.research_stream("What is AI?"):
    print(chunk, end="", flush=True)
```

#### `health_check()`

Check availability of Ollama and MCP services.

```python
async def health_check() -> Dict[str, Any]
```

**Returns:**

```python
{
    "ollama": {
        "available": True,
        "model": "llama3.2:3b"
    },
    "mcp": {
        "available": True,
        "tools": ["web_search", "fetch_page", "save_note", "list_notes", "get_note"]
    }
}
```

#### `set_research_mode()`

Change the research mode dynamically.

```python
def set_research_mode(mode: str) -> None
```

### Response Types

#### `ResearchResponse`

```python
@dataclass
class ResearchResponse:
    content: str                    # The research answer
    tool_trace: List[ToolExecution] # Record of all tool calls
    sources: List[Source]           # Extracted source URLs
    request_id: str                 # Unique request identifier
    total_duration_ms: float        # Total processing time
    model: str                      # LLM model used
    can_save_as_note: bool          # Whether response can be saved
    suggested_title: str            # Suggested title for notes
```

#### `ToolExecution`

```python
@dataclass
class ToolExecution:
    tool_name: str              # Tool that was called
    arguments: Dict[str, Any]   # Arguments passed to tool
    result: Optional[Dict]      # Tool result data
    error: Optional[str]        # Error message if failed
    success: bool               # Whether tool succeeded
    duration_ms: float          # Execution time
    timestamp: str              # ISO timestamp
```

#### `Source`

```python
@dataclass
class Source:
    url: str    # Source URL
    title: str  # Page title
    tool: str   # Tool that provided this source
```

---

## Ollama Client

Async HTTP client for Ollama API with streaming support.

### Location
`src/clients/ollama_client.py`

### Basic Usage

```python
from src.clients.ollama_client import OllamaClient

async def main():
    client = OllamaClient()

    # Check health
    health = await client.health()
    print(f"Available: {health.available}")

    # Chat completion
    response = await client.chat(
        messages=[
            {"role": "user", "content": "Hello!"}
        ],
        model="llama3.2:3b"
    )
    print(response.message.content)

    await client.close()
```

### Constructor

```python
OllamaClient(
    base_url: Optional[str] = None,
    timeout_ms: Optional[int] = None
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | From config | Ollama API URL (default: `http://localhost:11434`) |
| `timeout_ms` | `int` | From config | Request timeout in milliseconds |

### Methods

#### `health()`

Check Ollama server availability.

```python
async def health() -> OllamaHealth
```

**Returns:**

```python
@dataclass
class OllamaHealth:
    available: bool
    version: Optional[str] = None
    error: Optional[str] = None
```

#### `chat()`

Non-streaming chat completion.

```python
async def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    stream: bool = False,
    options: Optional[Dict] = None
) -> ChatResponse
```

**Returns:**

```python
@dataclass
class ChatResponse:
    model: str
    message: ChatMessage
    done: bool
    total_duration: Optional[int] = None
    eval_count: Optional[int] = None
```

#### `chat_stream()`

Streaming chat completion.

```python
async def chat_stream(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    options: Optional[Dict] = None
) -> AsyncIterator[str]
```

**Example:**

```python
async for chunk in client.chat_stream(messages):
    print(chunk, end="")
```

#### `list_models()`

List available models.

```python
async def list_models() -> List[str]
```

---

## MCP Client

JSON-RPC 2.0 client for MCP server communication.

### Location
`src/clients/mcp_client.py`

### Basic Usage

```python
from src.clients.mcp_client import MCPClient

async def main():
    client = MCPClient()

    # Check health
    health = await client.health()
    print(f"Available: {health.available}")
    print(f"Tools: {health.tools}")

    # Call a tool
    result = await client.web_search("Python programming")
    if result.success:
        print(result.data)

    await client.close()
```

### Constructor

```python
MCPClient(
    base_url: Optional[str] = None,
    timeout_seconds: Optional[float] = None
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | From config | MCP server URL (default: `http://localhost:3001`) |
| `timeout_seconds` | `float` | From config | Request timeout |

### Methods

#### `health()`

Check MCP server health and discover tools.

```python
async def health() -> MCPHealthStatus
```

**Returns:**

```python
@dataclass
class MCPHealthStatus:
    available: bool
    tools: Optional[List[str]] = None
    error: Optional[str] = None
```

#### `call_tool()`

Call any MCP tool by name.

```python
async def call_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    request_id: Optional[str] = None
) -> ToolResult
```

**Returns:**

```python
@dataclass
class ToolResult:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0
```

### Convenience Methods

#### `web_search()`

```python
async def web_search(
    query: str,
    limit: int = 3,
    request_id: Optional[str] = None
) -> ToolResult
```

#### `fetch_page()`

```python
async def fetch_page(
    url: str,
    max_chars: int = 8000,
    request_id: Optional[str] = None
) -> ToolResult
```

#### `save_note()`

```python
async def save_note(
    title: str,
    content: str,
    tags: List[str],
    source_urls: Optional[List[str]] = None,
    request_id: Optional[str] = None
) -> ToolResult
```

#### `list_notes()`

```python
async def list_notes(
    query: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 20,
    request_id: Optional[str] = None
) -> ToolResult
```

#### `get_note()`

```python
async def get_note(
    note_id: str,
    request_id: Optional[str] = None
) -> ToolResult
```

---

## Models

### Research Mode Configuration

Single source of truth for research mode settings.

**Location:** `src/models/research_mode.py`

```python
from src.models import QUICK_MODE, DEEP_MODE, get_mode_by_key

# Get mode configuration
mode = get_mode_by_key("quick")
print(mode.search_limit)    # 3
print(mode.fetch_limit)     # 2
print(mode.description)     # "Quick summary with 3 sources..."
```

#### `ResearchModeConfig`

```python
@dataclass
class ResearchModeConfig:
    key: str            # "quick" or "deep"
    ui_label: str       # Display label
    search_limit: int   # Max search results
    fetch_limit: int    # Max pages to fetch
    description: str    # User-facing description
    prompt_context: str # Added to system prompt
```

### Note Models

**Location:** `src/models/notes.py`

```python
@dataclass
class Note:
    id: str
    title: str
    content: str
    tags: List[str]
    source_urls: List[str]
    created_at: str
    updated_at: str

@dataclass
class NoteCreate:
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)
```

### Response Models

**Location:** `src/models/responses.py`

```python
@dataclass
class ApiResponse:
    success: bool
    data: Optional[Dict] = None
    error: Optional[ApiError] = None
    meta: Optional[ResponseMeta] = None

@dataclass
class ApiError:
    code: str
    message: str
    type: str
    param: Optional[str] = None
    details: Optional[Dict] = None
    suggestion: Optional[str] = None
```

---

## Error Handling

### Error Codes

**Location:** `src/errors/codes.py`

```python
class ErrorCodes:
    # Validation errors
    INVALID_REQUEST = "invalid_request"
    MISSING_PARAMETER = "missing_parameter"
    INVALID_URL = "invalid_url"

    # Search errors
    SEARCH_FAILED = "search_failed"
    SEARCH_TIMEOUT = "search_timeout"
    SEARCH_NO_RESULTS = "search_no_results"
    SEARCH_RATE_LIMITED = "search_rate_limited"

    # Fetch errors
    FETCH_FAILED = "fetch_failed"
    FETCH_TIMEOUT = "fetch_timeout"
    FETCH_BLOCKED = "fetch_blocked"
    FETCH_INVALID_URL = "fetch_invalid_url"
    FETCH_CONTENT_TYPE = "fetch_content_type"

    # Note errors
    NOTE_NOT_FOUND = "note_not_found"
    NOTE_SAVE_FAILED = "note_save_failed"
    NOTE_TITLE_REQUIRED = "note_title_required"
    NOTE_CONTENT_REQUIRED = "note_content_required"
    NOTE_TITLE_TOO_LONG = "note_title_too_long"
    NOTE_TOO_MANY_TAGS = "note_too_many_tags"
    NOTES_DB_UNAVAILABLE = "notes_db_unavailable"
    NOTES_QUERY_FAILED = "notes_query_failed"

    # Service errors
    OLLAMA_UNAVAILABLE = "ollama_unavailable"
    OLLAMA_MODEL_NOT_FOUND = "ollama_model_not_found"
    OLLAMA_TIMEOUT = "ollama_timeout"
    MCP_SERVER_UNAVAILABLE = "mcp_server_unavailable"
    MCP_TOOL_FAILED = "mcp_tool_failed"

    # Internal errors
    INTERNAL_ERROR = "internal_error"
    ORCHESTRATION_FAILED = "orchestration_failed"
```

### Exception Classes

**Location:** `src/errors/exceptions.py`

```python
class ResearchError(Exception):
    """Base exception for research errors."""
    def __init__(self, code: str, message: str, suggestion: Optional[str] = None):
        self.code = code
        self.message = message
        self.suggestion = suggestion

class OllamaError(ResearchError):
    """Ollama-specific errors."""
    pass

class MCPError(ResearchError):
    """MCP-specific errors."""
    pass

class NoteError(ResearchError):
    """Note-specific errors."""
    pass
```

### Error Handling Example

```python
from src.errors import OllamaError, MCPError, normalize_error

try:
    response = await orchestrator.research("query")
except OllamaError as e:
    print(f"Ollama error: {e.message}")
    print(f"Suggestion: {e.suggestion}")
except MCPError as e:
    print(f"MCP error: {e.message}")
except Exception as e:
    error = normalize_error(e)
    print(f"Error: {error.message}")
```

---

## Configuration

### Settings

**Location:** `src/utils/config.py`

All settings can be overridden via environment variables.

```python
from src.utils.config import settings

# Access settings
print(settings.ollama_base_url)        # http://localhost:11434
print(settings.mcp_server_url)         # http://localhost:3001
print(settings.ollama_default_model)   # llama3.1:8b
print(settings.search_provider)        # duckduckgo
```

### Available Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `OLLAMA_BASE_URL` | str | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_DEFAULT_MODEL` | str | `llama3.1:8b` | Default LLM model |
| `OLLAMA_TIMEOUT_MS` | int | `60000` | Ollama timeout |
| `MCP_SERVER_URL` | str | `http://localhost:3001` | MCP server URL |
| `MCP_SERVER_TIMEOUT_MS` | int | `30000` | MCP timeout |
| `SEARCH_PROVIDER` | str | `duckduckgo` | Search provider |
| `SEARCH_API_KEY` | str | `None` | Serper API key (if using) |
| `LOG_LEVEL` | str | `info` | Log level |
| `LOG_FORMAT` | str | `pretty` | Log format (`pretty` or `json`) |

### Environment File

Create `.env` in project root:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.2:3b
MCP_SERVER_URL=http://localhost:3001
SEARCH_PROVIDER=duckduckgo
LOG_LEVEL=info
LOG_FORMAT=pretty
```

---

## Full Example

```python
import asyncio
from src.agent.orchestrator import Orchestrator
from src.clients.mcp_client import MCPClient
from src.errors import ResearchError

async def main():
    # Initialize orchestrator
    orch = Orchestrator(research_mode="quick")

    # Check services
    health = await orch.health_check()
    if not health["ollama"]["available"]:
        print("Ollama not available!")
        return
    if not health["mcp"]["available"]:
        print("MCP server not available!")
        return

    try:
        # Execute research
        response = await orch.research(
            "What are the key features of Python 3.12?",
            on_tool_start=lambda name, args: print(f"  -> {name}"),
            on_tool_complete=lambda name, result, ok: print(f"  <- {name} ({'ok' if ok else 'failed'})")
        )

        # Print response
        print("\n" + "="*60)
        print(response.content)
        print("="*60)

        # Print sources
        print(f"\nSources ({len(response.sources)}):")
        for src in response.sources:
            print(f"  - {src.title}: {src.url}")

        # Save as note if valuable
        if response.can_save_as_note:
            mcp = MCPClient()
            result = await mcp.save_note(
                title=response.suggested_title or "Python 3.12 Features",
                content=response.content,
                tags=["python", "programming"],
                source_urls=[s.url for s in response.sources]
            )
            if result.success:
                print(f"\nNote saved: {result.data['note']['id']}")
            await mcp.close()

    except ResearchError as e:
        print(f"Research failed: {e.message}")
        if e.suggestion:
            print(f"Suggestion: {e.suggestion}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

*Last updated: January 12, 2026*
