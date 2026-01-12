# Research Copilot

A local AI research assistant that searches, reads, summarizes, and remembers—all through transparent tool calls and zero cloud dependencies.

## Features

- **Web Search & Fetch**: Search the web (Serper/DuckDuckGo) and read page content with source attribution
- **Research Notes**: Save, tag, and search your research findings locally
- **Transparent Tool Calls**: See exactly what the AI is doing (Research Trail with last 3 queries)
- **Source Citations**: Inline numbered citations with clickable links
- **Local-First**: Runs entirely on your machine using Ollama
- **MCP Protocol**: Standardized tool access via Model Context Protocol (JSON-RPC 2.0)
- **LLM-Generated Follow-ups**: Contextual follow-up question suggestions after each response
- **Multi-Query Research Trail**: View MCP tool calls grouped by query with timing and success metrics
- **How It Works Tab**: In-app documentation explaining the architecture and key concepts

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI (app.py)                     │
│                                                                  │
│  ┌─────────────┐  ┌───────────────────────────────────────────┐ │
│  │   Sidebar   │  │           Research Trail                  │ │
│  │             │  │           - Tool executions               │ │
│  │  - Settings │  │           - Source badges                 │ │
│  │  - Notes    │  │           - Timing info                   │ │
│  │  - Modes    │  ├───────────────────────────────────────────┤ │
│  │  - Status   │  │           Chat Panel                      │ │
│  │             │  │           - Messages                      │ │
│  │             │  │           - Citations                     │ │
│  │             │  │           - Follow-up suggestions         │ │
│  └─────────────┘  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Prompts   │  │   Parser    │  │     Orchestration       │  │
│  │   Builder   │  │  Tool Calls │  │        Loop             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                                       │
          ▼                                       ▼
┌─────────────────────┐              ┌─────────────────────────────┐
│   Ollama Client     │              │       MCP Client            │
│   (Local LLM)       │              │   (JSON-RPC 2.0)            │
└─────────────────────┘              └─────────────────────────────┘
                                                  │
                                                  ▼
                                     ┌─────────────────────────────┐
                                     │      MCP Server (Node.js)   │
                                     │  ┌─────────┐ ┌───────────┐  │
                                     │  │web_search│ │fetch_page │  │
                                     │  └─────────┘ └───────────┘  │
                                     │  ┌─────────┐ ┌───────────┐  │
                                     │  │save_note│ │list_notes │  │
                                     │  └─────────┘ └───────────┘  │
                                     │  ┌─────────┐                │
                                     │  │get_note │  SQLite+FTS5   │
                                     │  └─────────┘                │
                                     └─────────────────────────────┘
```

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Ollama** with a model installed (e.g., `llama3.1:8b`)

## Quick Start

### 1. Clone and Install Python Dependencies

```bash
cd research-copilot
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install and Start MCP Server

```bash
cd mcp_server
npm install
npm run build
npm start  # Runs on port 3001
```

### 3. Start Ollama

```bash
# In a separate terminal
ollama serve
ollama pull llama3.1:8b  # Or your preferred model
```

### 4. Run the Application

```bash
# In the project root, with .venv activated
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
research-copilot/
├── app.py                    # Streamlit entry point
├── src/
│   ├── agent/                # LLM orchestration
│   │   ├── orchestrator.py   # Tool-calling loop
│   │   ├── parser.py         # Tool call extraction
│   │   ├── prompts.py        # System prompt builder
│   │   └── citations.py      # Citation formatting
│   ├── clients/              # External service clients
│   │   ├── ollama_client.py  # Ollama API client
│   │   └── mcp_client.py     # MCP JSON-RPC client
│   ├── models/               # Data models
│   │   ├── research_mode.py  # Research mode config (single source of truth)
│   │   ├── notes.py          # Note models
│   │   └── responses.py      # API response models
│   ├── ui/                   # Streamlit components
│   │   ├── components.py     # Reusable UI components
│   │   ├── design_tokens.py  # Centralized design values
│   │   └── state.py          # Session state management
│   ├── api/                  # API layer
│   │   ├── research.py       # Research operations
│   │   └── notes.py          # Notes operations
│   ├── errors/               # Error handling
│   └── utils/                # Utilities
│       ├── config.py         # Pydantic settings
│       ├── logger.py         # Structured logging
│       └── validators.py     # URL validation
├── mcp_server/               # MCP Server (Node.js/TypeScript)
│   ├── src/
│   │   ├── tools/            # Tool implementations
│   │   │   ├── webSearch.ts  # DuckDuckGo/Serper search
│   │   │   ├── fetchPage.ts  # Page content extraction
│   │   │   ├── saveNote.ts   # Note persistence
│   │   │   ├── listNotes.ts  # Note listing/search
│   │   │   └── getNote.ts    # Note retrieval
│   │   ├── db/               # SQLite + FTS5
│   │   ├── middleware/       # Rate limiting
│   │   └── server.ts         # Express + JSON-RPC
│   └── tests/                # Vitest tests
├── tests/                    # Python tests (pytest)
├── scripts/
│   └── validate_env.py       # Environment validation
└── docs/                     # Documentation
    ├── HOW_IT_WORKS.md       # Architecture overview
    ├── SETUP.md              # Installation guide
    ├── API.md                # Python API reference
    ├── MCP_SERVER.md         # MCP tools reference
    ├── PERFORMANCE.md        # Performance analysis
    └── SECURITY.md           # Security audit
```

## Configuration

Copy the example environment files and customize as needed:

```bash
cp .env.example .env
cp mcp_server/.env.example mcp_server/.env
```

### Root `.env` (Streamlit App)

```env
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.1:8b

# MCP Server
MCP_SERVER_URL=http://localhost:3001

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=pretty  # or "json"
```

### MCP Server `.env` (Required for Serper API)

Create a `.env` file in `mcp_server/`:

```env
# Search Provider (duckduckgo or serper)
SEARCH_PROVIDER=serper

# Serper API Key (required if SEARCH_PROVIDER=serper)
SERPER_API_KEY=your_key_here
```

**Note:** The MCP server reads its own `.env` file for search configuration. DuckDuckGo is the default (no API key required) but may have rate limits. Serper provides more reliable results. See `mcp_server/.env.example` for all available options including rate limiting and timeouts.

## Research Modes

| Mode | Sources | Fetch | Description |
|------|---------|-------|-------------|
| **Quick Summary** | 5 max | 3 pages | Concise bullet points, < 250 words |
| **Deep Dive** | 7 max | 5 pages | Detailed analysis with recommendations |

**Notes:**
- Notes list pagination uses `limit` + `offset` in MCP, and the UI shows snippets for each note
- Model selection shows 4 preferred models: `llama3.1:8b` (default), `ministral-3:8b`, `mistral:7b`, `gemma3:4b`
- Research Trail displays tool calls for the last 3 queries with per-query and aggregate statistics
- Sidebar shows active search provider (🔍 Serper API or 🦆 DuckDuckGo)

## MCP Tools

| Tool | Purpose | Parameters |
|------|---------|------------|
| `web_search` | Search the web | `query`, `limit` (1-5), `provider` |
| `fetch_page` | Read page content | `url`, `max_chars`, `extract_mode` |
| `save_note` | Save research | `title`, `content`, `tags`, `source_urls` |
| `list_notes` | Find notes | `query`, `tags`, `limit`, `offset` |
| `get_note` | Retrieve note | `id` (UUID) |

## Research Trail

The Research Trail panel shows MCP tool calls for transparency and debugging:

```
🔬 Research Trail (12 MCP calls from 3 queries)
├── 🖥️ MCP Server Connection
│   ┌─────────┬───────────┬─────────────┬────────────┐
│   │ 3       │ 12        │ 83%         │ 3521ms     │
│   │ Queries │ Calls     │ Success     │ Total Time │
│   └─────────┴───────────┴─────────────┴────────────┘
│   MCP Endpoint: http://localhost:3001/mcp
│   Protocol: JSON-RPC 2.0
│
├── 🔵 Latest
│   Query: "What is quantum computing?"
│   📊 4 calls | ✅ 3 success | ⏱️ 1842ms
│   ├── ✅ 🔍 web_search `MCP TOOL`     [712ms]
│   └── ✅ 📄 fetch_page `MCP TOOL`     [523ms]
│
├── ⚪ Query 2
│   Query: "How does machine learning work?"
│   ...
```

**Features:**
- Shows last 3 queries with their tool traces (configurable)
- Per-query statistics (calls, success rate, timing)
- Expandable request details showing JSON-RPC 2.0 payloads
- Success/failure indicators with timing for each tool call

## Development

### Run Tests

```bash
# Python tests
pytest tests/ -v

# MCP Server tests
cd mcp_server && npm test
```

### Validate Environment

```bash
python scripts/validate_env.py
```

### Code Style

- Python: Black, isort, type hints
- TypeScript: ESLint, Prettier

## Key Design Principles

1. **Sources Over Assertions**: Every answer cites its sources
2. **Transparency Is Trust**: Users see all tool executions
3. **Local-First Always**: No cloud LLM dependencies
4. **Research Persists**: Notes survive app restarts
5. **Errors Guide Recovery**: Helpful error messages with suggestions

## Documentation

- **[How It Works](docs/HOW_IT_WORKS.md)**: Architecture overview and key concepts
- **[Setup Guide](docs/SETUP.md)**: Detailed installation and troubleshooting
- **[API Reference](docs/API.md)**: Python API documentation
- **[MCP Server](docs/MCP_SERVER.md)**: MCP tools and configuration
- **[Performance](docs/PERFORMANCE.md)**: Performance analysis and optimization
- **[Security](docs/SECURITY.md)**: Security audit report

## License

MIT

---

*Built as a demonstration of AI agent orchestration patterns with MCP protocol.*
