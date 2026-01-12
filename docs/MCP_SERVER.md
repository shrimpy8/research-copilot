# MCP Server Documentation

> Model Context Protocol server providing research tools via JSON-RPC 2.0.

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [API Reference](#api-reference)
5. [Tools](#tools)
6. [Database](#database)
7. [Rate Limiting](#rate-limiting)
8. [Error Handling](#error-handling)

---

## Overview

The MCP Server is a Node.js/TypeScript application that implements the Model Context Protocol, providing tools for web search, page fetching, and note management via JSON-RPC 2.0.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                   MCP Server                         │
├─────────────────────────────────────────────────────┤
│  Express HTTP Server                                 │
│  ├─ /health     → Health check endpoint             │
│  └─ /mcp        → JSON-RPC 2.0 endpoint             │
├─────────────────────────────────────────────────────┤
│  Middleware                                          │
│  └─ Rate Limiter (sliding window per category)      │
├─────────────────────────────────────────────────────┤
│  Tools                                               │
│  ├─ web_search  → DuckDuckGo / Serper search        │
│  ├─ fetch_page  → Content extraction with SSRF      │
│  ├─ save_note   → SQLite persistence                │
│  ├─ list_notes  → FTS5 full-text search             │
│  └─ get_note    → UUID-based retrieval              │
├─────────────────────────────────────────────────────┤
│  Database                                            │
│  └─ SQLite + FTS5 (full-text search)                │
└─────────────────────────────────────────────────────┘
```

### Tech Stack

- **Runtime:** Node.js 18+
- **Language:** TypeScript 5.x
- **Framework:** Express.js
- **Database:** SQLite with FTS5
- **Validation:** Zod
- **Testing:** Vitest

---

## Installation

### Prerequisites

- Node.js 18 or higher
- npm 9 or higher

### Setup

```bash
# Navigate to MCP server directory
cd mcp_server

# Install dependencies
npm install

# Build TypeScript
npm run build

# Start server
npm start
```

### Development Mode

```bash
# Watch mode with auto-rebuild
npm run dev
```

### Running Tests

```bash
# Run all tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage
```

---

## Configuration

### Environment Variables

Create a `.env` file in the `mcp_server/` directory:

```env
# Server
PORT=3001
HOST=localhost
LOG_LEVEL=info

# Search
SEARCH_PROVIDER=duckduckgo
SERPER_API_KEY=           # Required if using serper
MAX_SEARCH_RESULTS=5
SEARCH_TIMEOUT_MS=10000

# Fetch
MAX_PAGE_SIZE=50000
FETCH_TIMEOUT_MS=15000
USER_AGENT=ResearchCopilot/1.0

# Database
DB_PATH=./data/notes.db

# Rate Limiting (requests per minute)
RATE_LIMIT_SEARCH=10
RATE_LIMIT_FETCH=30
RATE_LIMIT_NOTES=50
```

### Configuration Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PORT` | number | `3001` | Server port |
| `HOST` | string | `localhost` | Server host |
| `LOG_LEVEL` | string | `info` | Log level: debug, info, warn, error |
| `SEARCH_PROVIDER` | string | `duckduckgo` | Search provider: duckduckgo, serper |
| `SERPER_API_KEY` | string | - | Serper API key (required for serper) |
| `MAX_SEARCH_RESULTS` | number | `5` | Maximum search results |
| `SEARCH_TIMEOUT_MS` | number | `10000` | Search timeout |
| `MAX_PAGE_SIZE` | number | `50000` | Maximum page content size |
| `FETCH_TIMEOUT_MS` | number | `15000` | Fetch timeout |
| `USER_AGENT` | string | `ResearchCopilot/1.0` | HTTP User-Agent |
| `DB_PATH` | string | `./data/notes.db` | SQLite database path |
| `RATE_LIMIT_SEARCH` | number | `10` | Search requests per minute |
| `RATE_LIMIT_FETCH` | number | `30` | Fetch requests per minute |
| `RATE_LIMIT_NOTES` | number | `50` | Note operations per minute |

---

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/mcp` | POST | JSON-RPC 2.0 endpoint |

### Health Check

```bash
curl http://localhost:3001/health
```

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2026-01-11T12:00:00.000Z",
  "version": "1.0.0"
}
```

### JSON-RPC 2.0 Protocol

All tool calls use JSON-RPC 2.0 format:

**Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": { ... }
  },
  "id": "unique-request-id"
}
```

**Success Response:**

```json
{
  "jsonrpc": "2.0",
  "result": { ... },
  "id": "unique-request-id"
}
```

**Error Response:**

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32000,
    "message": "Error description",
    "data": {
      "code": "error_code",
      "details": { ... }
    }
  },
  "id": "unique-request-id"
}
```

### List Available Tools

```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": "1"
  }'
```

---

## Tools

### web_search

Search the web using DuckDuckGo or Serper.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `limit` | number | No | `3` | Max results (1-5) |
| `provider` | string | No | Config | Search provider |

**Example:**

```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "web_search",
      "arguments": {
        "query": "Python programming",
        "limit": 3
      }
    },
    "id": "1"
  }'
```

**Response:**

```json
{
  "results": [
    {
      "title": "Python.org",
      "url": "https://www.python.org/",
      "snippet": "Python is a programming language..."
    }
  ],
  "provider": "duckduckgo",
  "query": "Python programming"
}
```

### fetch_page

Fetch and extract content from a web page.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `url` | string | Yes | - | URL to fetch |
| `max_chars` | number | No | `8000` | Max content length |
| `extract_mode` | string | No | `text` | Output format (`text` or `markdown`) |

**Example:**

```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "fetch_page",
      "arguments": {
        "url": "https://docs.python.org/3/",
        "max_chars": 10000,
        "extract_mode": "text"
      }
    },
    "id": "1"
  }'
```

**Response:**

```json
{
  "url": "https://docs.python.org/3/",
  "title": "Python 3.12 Documentation",
  "content": "Welcome to Python documentation...",
  "content_length": 5432,
  "truncated": false
}
```

**Security:**

- SSRF protection blocks private IP ranges
- DNS rebinding protection
- Redirect validation
- Content-Type verification

### save_note

Save a research note with tags and sources.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `title` | string | Yes | - | Note title (max 200 chars) |
| `content` | string | Yes | - | Note content (max 50000 chars) |
| `tags` | string[] | No | `[]` | Tags for categorization (max 10) |
| `source_urls` | string[] | No | `[]` | Source URLs (max 20) |

**Example:**

```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "save_note",
      "arguments": {
        "title": "Python Overview",
        "content": "Python is a versatile programming language...",
        "tags": ["python", "programming"],
        "source_urls": ["https://python.org"]
      }
    },
    "id": "1"
  }'
```

**Response:**

```json
{
  "note": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Python Overview",
    "content": "Python is a versatile programming language...",
    "tags": ["python", "programming"],
    "source_urls": ["https://python.org"],
    "created_at": "2026-01-11T12:00:00.000Z",
    "updated_at": "2026-01-11T12:00:00.000Z"
  }
}
```

### list_notes

List notes with optional search and filtering.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | No | - | Full-text search query |
| `tags` | string[] | No | - | Filter by tags (AND logic) |
| `limit` | number | No | `20` | Max results (1-100) |
| `offset` | number | No | `0` | Pagination offset |

**Example:**

```bash
# Search notes
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "list_notes",
      "arguments": {
        "query": "python",
        "limit": 10,
        "offset": 0
      }
    },
    "id": "1"
  }'

# Filter by tags
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "list_notes",
      "arguments": {
        "tags": ["programming"]
      }
    },
    "id": "1"
  }'
```

**Response:**

```json
{
  "notes": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Python Overview",
      "tags": ["python", "programming"],
      "created_at": "2026-01-11T12:00:00.000Z",
      "snippet": "Python is a versatile programming language..."
    }
  ],
  "count": 1,
  "total_count": 1,
  "has_more": false,
  "limit": 10,
  "offset": 0
}
```

### get_note

Retrieve a specific note by ID.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | Yes | Note UUID |

**Example:**

```bash
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_note",
      "arguments": {
        "id": "550e8400-e29b-41d4-a716-446655440000"
      }
    },
    "id": "1"
  }'
```

**Response:**

```json
{
  "note": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Python Overview",
    "content": "Python is a versatile programming language...",
    "tags": ["python", "programming"],
    "source_urls": ["https://python.org"],
    "created_at": "2026-01-11T12:00:00.000Z",
    "updated_at": "2026-01-11T12:00:00.000Z"
  }
}
```

---

## Database

### Schema

The MCP server uses SQLite with FTS5 for full-text search.

**Notes Table:**

```sql
CREATE TABLE notes (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '[]',         -- JSON array
  source_urls TEXT NOT NULL DEFAULT '[]',  -- JSON array
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

**Full-Text Search Index:**

```sql
CREATE VIRTUAL TABLE notes_fts USING fts5(
  title,
  content,
  content='notes',
  content_rowid='rowid'
);
```

**Auto-Sync Triggers:**

The database automatically keeps the FTS index in sync:

- `notes_ai` - After INSERT trigger
- `notes_ad` - After DELETE trigger
- `notes_au` - After UPDATE trigger

### Database Location

Default: `./data/notes.db`

Override with `DB_PATH` environment variable.

### Backup

```bash
# Backup database
cp ./data/notes.db ./data/notes.db.backup

# Or use SQLite CLI
sqlite3 ./data/notes.db ".backup ./data/backup.db"
```

---

## Rate Limiting

The server implements sliding window rate limiting per tool category.

### Categories

| Category | Default Limit | Tools |
|----------|---------------|-------|
| search | 10/min | `web_search` |
| fetch | 30/min | `fetch_page` |
| notes | 50/min | `save_note`, `list_notes`, `get_note` |

### Rate Limit Response

When rate limited, the server returns:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32000,
    "message": "Rate limit exceeded",
    "data": {
      "code": "rate_limit_exceeded",
      "details": {
        "category": "search",
        "limit": 10,
        "window": "1 minute",
        "retryAfter": 30
      }
    }
  }
}
```

---

## Error Handling

### Error Codes

| Code | Description |
|------|-------------|
| `search_failed` | Search provider error |
| `search_no_results` | No search results found |
| `fetch_failed` | Failed to fetch URL |
| `fetch_timeout` | Fetch operation timed out |
| `fetch_invalid_url` | Invalid or blocked URL |
| `note_not_found` | Note ID not found |
| `note_save_failed` | Failed to save note |
| `note_invalid` | Invalid note data |
| `rate_limit_exceeded` | Rate limit hit |
| `validation_error` | Input validation failed |

### Error Response Format

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32000,
    "message": "Human-readable error message",
    "data": {
      "code": "error_code",
      "details": {
        "field": "Additional context"
      }
    }
  },
  "id": "request-id"
}
```

---

## Development

### Project Structure

```
mcp_server/
├── src/
│   ├── index.ts           # Entry point
│   ├── server.ts          # Express server setup
│   ├── config/
│   │   └── index.ts       # Configuration management
│   ├── tools/
│   │   ├── index.ts       # Tool registry
│   │   ├── webSearch.ts   # Search implementation
│   │   ├── fetchPage.ts   # Fetch implementation
│   │   ├── saveNote.ts    # Save note
│   │   ├── listNotes.ts   # List notes
│   │   └── getNote.ts     # Get note
│   ├── db/
│   │   ├── index.ts       # Database exports
│   │   ├── client.ts      # Database client
│   │   └── schema.ts      # Schema management
│   ├── services/
│   │   └── notesService.ts # Note operations
│   ├── middleware/
│   │   └── rateLimit.ts   # Rate limiter
│   └── errors/
│       └── index.ts       # Error definitions
├── tests/
│   └── *.test.ts          # Test files
├── package.json
├── tsconfig.json
└── vitest.config.ts
```

### Adding a New Tool

1. Create tool file in `src/tools/`:

```typescript
// src/tools/myTool.ts
import { ErrorCodes, ToolError } from '../errors/index.js';

export interface MyToolParams {
  param1: string;
  param2?: number;
}

export interface MyToolResponse {
  result: string;
}

export async function myTool(params: MyToolParams): Promise<MyToolResponse> {
  // Validate
  if (!params.param1) {
    throw new ToolError(ErrorCodes.VALIDATION_ERROR, 'param1 is required');
  }

  // Implement
  return { result: 'success' };
}
```

2. Register in `src/tools/index.ts`:

```typescript
import { myTool } from './myTool.js';

export const tools = {
  // ... existing tools
  my_tool: {
    handler: myTool,
    schema: {
      name: 'my_tool',
      description: 'Description of my tool',
      inputSchema: {
        type: 'object',
        properties: {
          param1: { type: 'string', description: 'First parameter' },
          param2: { type: 'number', description: 'Second parameter' }
        },
        required: ['param1']
      }
    },
    rateCategory: 'notes' // or 'search', 'fetch'
  }
};
```

3. Add tests in `tests/myTool.test.ts`

---

*Last updated: January 11, 2026*
