# How It Works

Research Copilot is a local AI research assistant that demonstrates modern AI agent architecture patterns. This document explains the key concepts and how the system works.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Interface (Streamlit)                  │
│                                                                 │
│  ┌──────────────┐  ┌─────────────────────────────────────────┐  │
│  │   Sidebar    │  │          Research Trail                 │  │
│  │              │  │          - Tool calls                   │  │
│  │  - Settings  │  │          - Timing info                  │  │
│  │  - Notes     │  │          - MCP details                  │  │
│  │  - Status    │  ├─────────────────────────────────────────┤  │
│  │              │  │          Chat Panel                     │  │
│  │              │  │          - Questions & Answers          │  │
│  │              │  │          - Citations                    │  │
│  │              │  │          - Follow-up suggestions        │  │
│  └──────────────┘  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator (Python)                  │
│                                                                 │
│  1. Receives user query                                         │
│  2. Builds context with system prompt + tool definitions        │
│  3. Sends to LLM → Parses response for tool calls               │
│  4. Executes tools via MCP → Feeds results back to LLM          │
│  5. Repeats until LLM provides final answer                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
          │                                       │
          ▼                                       ▼
┌─────────────────────┐              ┌─────────────────────────────┐
│   Ollama (Local)    │              │    MCP Server (Node.js)     │
│                     │              │                             │
│  LLM inference      │              │  ┌─────────┐ ┌───────────┐  │
│  runs entirely      │              │  │web_search│ │fetch_page │  │
│  on your machine    │              │  └─────────┘ └───────────┘  │
│                     │              │  ┌─────────┐ ┌───────────┐  │
│  No cloud calls     │              │  │save_note│ │list_notes │  │
│  No data leaves     │              │  └─────────┘ └───────────┘  │
│                     │              │  ┌─────────┐                │
│                     │              │  │get_note │  SQLite+FTS5   │
│                     │              │  └─────────┘                │
└─────────────────────┘              └─────────────────────────────┘
```

---

## Key Concepts

### 1. AI Agent with Tool Calling

Unlike simple chatbots that only generate text, Research Copilot is an **AI agent** that can take actions:

```
Traditional Chatbot:
  User → LLM → Response

AI Agent (Research Copilot):
  User → LLM → "I need to search for X" → Tool Execution → Result → LLM → Response
                     ↑                                              │
                     └──────────── Loop until answer ready ─────────┘
```

The LLM decides *when* and *which* tools to use based on the user's question. This is called **autonomous tool calling**.

### 2. Model Context Protocol (MCP)

MCP is a standardized way for AI agents to access tools. Think of it as a "USB for AI tools":

- **Standardized Interface**: Any MCP-compatible tool works with any MCP-compatible agent
- **JSON-RPC 2.0**: Industry-standard protocol for remote procedure calls
- **Tool Discovery**: Agents can query what tools are available and their parameters

```
┌─────────────┐         JSON-RPC 2.0          ┌─────────────┐
│   Agent     │  ──────────────────────────►  │  MCP Server │
│             │  {"method": "web_search",     │             │
│             │   "params": {"query": "..."}} │  Tools:     │
│             │  ◄──────────────────────────  │  - search   │
│             │  {"result": {...}}            │  - fetch    │
└─────────────┘                               │  - notes    │
                                              └─────────────┘
```

### 3. Local-First Architecture

Everything runs on your machine:

| Component | Location | Purpose |
|-----------|----------|---------|
| Ollama | Local | LLM inference (no cloud AI) |
| MCP Server | Local | Tool execution |
| SQLite | Local | Notes storage |
| Streamlit | Local | User interface |

**Only external calls**: Web search API and fetching web pages (transparent in Research Trail)

### 4. Transparency Through Traceability

Every action is visible:

- **Research Trail**: Shows all MCP tool calls with timing
- **Source Citations**: Inline numbered references [1], [2], [3]
- **Tool Arguments**: Expandable details for each tool call

This builds trust by showing *exactly* what the AI did to answer your question.

---

## The Research Flow

When you ask a question, here's what happens:

### Step 1: Query Analysis
The LLM analyzes your question and decides what tools to use:
- "What is quantum computing?" → Needs web search + page fetch
- "Summarize this URL: ..." → Needs page fetch only
- "Find my notes about AI" → Needs notes search

### Step 2: Tool Execution Loop

```python
while not has_final_answer:
    # 1. LLM generates response (may include tool calls)
    response = llm.generate(messages)

    # 2. Parse for tool calls
    tool_calls = parse_tool_calls(response)

    # 3. If tools requested, execute them
    if tool_calls:
        for tool in tool_calls:
            result = mcp.execute(tool.name, tool.args)
            messages.append(tool_result)
    else:
        # No more tools needed - this is the final answer
        has_final_answer = True
```

### Step 3: Source Synthesis
The LLM combines information from multiple sources:
- Extracts key facts from each page
- Identifies agreements/disagreements between sources
- Synthesizes a coherent answer with citations

### Step 4: Response Delivery
- Formatted answer with inline citations
- Source list with clickable links
- Follow-up question suggestions
- Option to save as a note

---

## Research Modes

| Mode | Search Limit | Fetch Limit | Best For |
|------|-------------|-------------|----------|
| **Quick Summary** | 5 results | 3 pages | Fast answers, simple questions |
| **Deep Dive** | 7 results | 5 pages | Complex topics, thorough research |

---

## UI Settings

The sidebar provides configurable options that affect LLM behavior and research quality:

| Setting | Range | Default | Description |
|---------|-------|---------|-------------|
| **Model** | Installed models | `ministral-3:8b` | Ollama model to use for inference |
| **Research Mode** | Quick / Deep | Quick | Controls search and fetch limits |
| **Fetch Format** | text / markdown | text | Output format for fetched pages |
| **Temperature** | 0.0 - 1.0 | 0.4 | LLM creativity/randomness |

### Temperature Control

Temperature affects how the LLM generates responses:

- **Lower (0.0 - 0.3)**: More focused, deterministic, consistent answers. Best for factual research where you want reliable, repeatable results.
- **Medium (0.4 - 0.6)**: Balanced creativity and focus. Default of 0.4 provides good research quality while allowing some variation.
- **Higher (0.7 - 1.0)**: More creative, varied responses. May be useful for brainstorming or exploring different perspectives, but less reliable for factual research.

Temperature can be set via:
1. **UI slider** in the sidebar (persists for session)
2. **Environment variable** `OLLAMA_TEMPERATURE` in `.env` (sets default)

---

## MCP Tools Reference

### `web_search`
Searches the web using Serper API or DuckDuckGo.
```json
{"query": "quantum computing basics", "limit": 5}
```

### `fetch_page`
Reads and extracts content from a URL.
```json
{"url": "https://example.com/article", "max_chars": 8000}
```

### `save_note`
Saves research findings for later.
```json
{"title": "Quantum Computing Notes", "content": "...", "tags": ["physics", "computing"]}
```

### `list_notes`
Searches saved notes with full-text search.
```json
{"query": "quantum", "limit": 10}
```

### `get_note`
Retrieves a specific note by ID.
```json
{"id": "uuid-here"}
```

---

## Why This Architecture?

### Modularity
Each component has a single responsibility:
- Streamlit: User interface only
- Orchestrator: Conversation flow only
- MCP Server: Tool execution only
- Ollama: LLM inference only

### Extensibility
Adding new tools is simple:
1. Implement tool in MCP server
2. Add to tool definitions in `prompts/system_prompt.md`
3. The LLM automatically learns to use it

Note: System prompts are externalized in the `prompts/` directory for easy editing without code changes.

### Privacy
- No data sent to cloud AI services
- Notes stored locally in SQLite
- Only web searches/fetches leave your machine (and are logged)

### Transparency
- Every tool call is visible
- Every source is cited
- Users can verify any claim

---

## Technical Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Streamlit | Rapid Python UI development |
| Agent | Python + asyncio | Orchestration and parsing |
| LLM | Ollama | Local model inference |
| Tools | Node.js + TypeScript | MCP server implementation |
| Database | SQLite + FTS5 | Notes with full-text search |
| Protocol | JSON-RPC 2.0 | MCP communication |

---

## API Design

Research Copilot uses a layered API architecture with consistent patterns across all services.

### Design Philosophy

The APIs follow **Stripe-style response patterns** - consistent, predictable, and self-documenting:

```python
# Every API response follows this structure
{
    "success": True,           # Boolean: did the operation succeed?
    "data": {...},             # Payload (null on error)
    "error": None,             # Error details (null on success)
    "meta": {                  # Request metadata
        "request_id": "abc123",
        "timestamp": "2024-01-15T10:30:00Z",
        "duration_ms": 245
    }
}
```

**Key Principles:**
- **Predictable Structure**: Same response shape for all endpoints
- **Explicit Success/Failure**: Never guess if something worked
- **Rich Metadata**: Request tracing, timing, and debugging info
- **Actionable Errors**: Error messages include recovery suggestions

### API Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                      Streamlit UI (app.py)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Python Client Layer                          │
│  ┌──────────────────┐         ┌──────────────────────────────┐  │
│  │  OllamaClient    │         │       MCPClient              │  │
│  │  - health()      │         │  - call_tool(name, args)     │  │
│  │  - generate()    │         │  - web_search(query)         │  │
│  │  - chat()        │         │  - fetch_page(url)           │  │
│  │  - list_models() │         │  - save_note(title, content) │  │
│  └──────────────────┘         │  - list_notes(query)         │  │
│         │                     │  - get_note(id)              │  │
│         │                     └──────────────────────────────┘  │
│         │                                    │                  │
└─────────│────────────────────────────────────│──────────────────┘
          │                                    │
          ▼                                    ▼
┌─────────────────────┐         ┌─────────────────────────────────┐
│  Ollama REST API    │         │     MCP Server (JSON-RPC 2.0)   │
│  localhost:11434    │         │     localhost:3001/mcp          │
└─────────────────────┘         └─────────────────────────────────┘
```

### Python Clients

#### OllamaClient

Communicates with the local Ollama instance for LLM inference:

```python
from src.clients.ollama_client import OllamaClient

client = OllamaClient()

# Check if Ollama is running
health = await client.health()
# Returns: OllamaHealth(available=True, models=["ministral-3:8b", "mistral:7b"])

# Generate a response
response = await client.chat(
    model="ministral-3:8b",
    messages=[
        {"role": "user", "content": "What is Python?"}
    ]
)
# Returns: OllamaResponse(message=Message(content="Python is..."))
```

#### MCPClient

Communicates with the MCP server for tool execution:

```python
from src.clients.mcp_client import MCPClient

client = MCPClient()

# Call any tool dynamically
result = await client.call_tool("web_search", {"query": "AI news", "limit": 5})

# Or use typed convenience methods
search_result = await client.web_search("AI news", limit=5)
page_result = await client.fetch_page("https://example.com")
note_result = await client.save_note("My Research", "Content here", tags=["ai"])
```

### MCP Server API (JSON-RPC 2.0)

The MCP server exposes tools via JSON-RPC 2.0 over HTTP:

**Endpoint:** `POST /mcp`

#### Request Format
```json
{
    "jsonrpc": "2.0",
    "id": "req_123",
    "method": "tools/call",
    "params": {
        "name": "web_search",
        "arguments": {
            "query": "quantum computing",
            "limit": 5
        }
    }
}
```

#### Success Response
```json
{
    "jsonrpc": "2.0",
    "id": "req_123",
    "result": {
        "content": [{
            "type": "text",
            "text": "{\"results\": [{\"title\": \"...\", \"url\": \"...\"}]}"
        }]
    }
}
```

#### Error Response
```json
{
    "jsonrpc": "2.0",
    "id": "req_123",
    "error": {
        "code": -32602,
        "message": "Invalid params: query is required"
    }
}
```

### Error Handling Design

Errors are designed to be **actionable**, not just informative:

```python
# Error structure
{
    "code": "search_failed",        # Machine-readable code
    "type": "tool_error",           # Error category
    "message": "Web search failed", # Human-readable message
    "suggestion": "Check your internet connection or try again"  # Recovery hint
}
```

**Error Categories:**
| Type | Description | Example Codes |
|------|-------------|---------------|
| `service_error` | External service unavailable | `ollama_unavailable`, `mcp_server_unavailable` |
| `tool_error` | Tool execution failed | `search_failed`, `fetch_timeout` |
| `validation_error` | Invalid input | `invalid_url`, `missing_query` |
| `not_found` | Resource doesn't exist | `note_not_found` |

### Request Tracing

Every request is traceable through the system:

```
User Query: "What is quantum computing?"
    │
    ├── request_id: "req_abc123"
    │
    ├── Tool Call 1: web_search
    │   ├── mcp_request_id: "mcp_1"
    │   ├── duration: 712ms
    │   └── result: 5 search results
    │
    ├── Tool Call 2: fetch_page
    │   ├── mcp_request_id: "mcp_2"
    │   ├── duration: 523ms
    │   └── result: Page content (8000 chars)
    │
    └── Final Response
        ├── total_duration: 2847ms
        └── sources: 5 cited
```

This tracing enables:
- **Debugging**: Find exactly where something failed
- **Performance**: Identify slow operations
- **Transparency**: Show users what happened (Research Trail)

### Data Models

Key data structures used across the APIs:

```python
# Research response from orchestrator
@dataclass
class ResearchResponse:
    content: str                    # The answer
    sources: List[Source]           # Cited sources
    tool_trace: List[ToolExecution] # What tools were used
    request_id: str                 # Tracing ID
    can_save_as_note: bool          # UI hint
    suggested_title: str            # For save dialog
    followup_questions: List[str]   # Suggested next questions

# Source citation
@dataclass
class Source:
    url: str
    title: str
    tool: str      # "web_search" or "fetch_page"
    quality: str   # "docs", "blog", "news", etc.

# Tool execution record
@dataclass
class ToolExecution:
    tool_name: str
    arguments: Dict[str, Any]
    success: bool
    duration_ms: float
    result: Optional[Dict]
    error: Optional[str]
    request_id: Optional[str]
```

---

## Learn More

- [MCP Specification](https://modelcontextprotocol.io) - Official MCP documentation
- [Ollama](https://ollama.ai) - Local LLM runtime
- [Streamlit](https://streamlit.io) - Python web framework

---

*This project demonstrates AI agent patterns that can be applied to more complex applications like code assistants, data analysis tools, and workflow automation.*
