# Research Copilot Setup Guide

> Complete setup instructions for getting Research Copilot running locally.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Installation](#detailed-installation)
4. [Configuration](#configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Setup](#advanced-setup)

---

## Prerequisites

### Required Software

| Software | Version | Check Command |
|----------|---------|---------------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Ollama | Latest | `ollama --version` |

### Install Prerequisites

**macOS (Homebrew):**

```bash
# Python
brew install python@3.12

# Node.js
brew install node

# Ollama
brew install ollama
```

**Ubuntu/Debian:**

```bash
# Python
sudo apt update
sudo apt install python3.12 python3.12-venv

# Node.js (using NodeSource)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs

# Ollama
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**

1. Python: Download from [python.org](https://www.python.org/downloads/)
2. Node.js: Download from [nodejs.org](https://nodejs.org/)
3. Ollama: Download from [ollama.ai](https://ollama.ai/download)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/research-copilot.git
cd research-copilot

# 2. Run setup script
./scripts/setup.sh  # Or manually follow steps below
```

---

## Detailed Installation

### Step 1: Python Environment

```bash
# Navigate to project root
cd research-copilot

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

**Verify Python setup:**

```bash
python -c "import streamlit; print('Streamlit OK')"
python -c "import httpx; print('HTTPX OK')"
python -c "import pydantic; print('Pydantic OK')"
```

### Step 2: MCP Server

```bash
# Navigate to MCP server directory
cd mcp_server

# Install dependencies
npm install

# Build TypeScript
npm run build

# Verify build
ls dist/  # Should show compiled JS files
```

**Verify MCP server:**

```bash
# Start server (in mcp_server directory)
npm start

# In another terminal, check health
curl http://localhost:3001/health
# Should return: {"status":"ok",...}

# Stop with Ctrl+C
```

### Step 3: Ollama

```bash
# Start Ollama service (runs in background)
ollama serve

# Pull a model (choose one)
ollama pull ministral-3:8b      # Smaller, faster (2GB)
ollama pull ministral-3:8b      # Better quality (4.7GB)
ollama pull mistral          # Alternative (4.1GB)

# Verify model is available
ollama list
```

**Verify Ollama:**

```bash
# Quick test
ollama run ministral-3:8b "Say hello in one word"
```

### Step 4: Configuration

Create `.env` file in project root:

```bash
# Copy example config
cp .env.example .env

# Edit as needed
nano .env  # or your preferred editor
```

**Minimum `.env` configuration:**

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=ministral-3:8b
MCP_SERVER_URL=http://localhost:3001
LOG_LEVEL=info
```

### Step 5: First Run

**Terminal 1 - MCP Server:**

```bash
cd mcp_server
npm start
```

**Terminal 2 - Streamlit App:**

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Run the app
streamlit run app.py
```

**Open browser:** http://localhost:8501

---

## Configuration

### Environment Variables

Create `.env` in project root:

```env
# ===== Ollama Configuration =====
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=ministral-3:8b
OLLAMA_TIMEOUT_MS=120000            # 2 minutes for complex research queries
OLLAMA_TEMPERATURE=0.4              # LLM creativity (0.0-1.0, lower = more focused)

# ===== MCP Server Configuration =====
MCP_SERVER_URL=http://localhost:3001
MCP_SERVER_TIMEOUT_MS=30000

# ===== Search/Fetch Timeouts =====
SEARCH_TIMEOUT_MS=30000             # 30 seconds for search requests
FETCH_TIMEOUT_MS=30000              # 30 seconds for page fetches

# ===== Logging =====
LOG_LEVEL=info                      # debug, info, warn, error
LOG_FORMAT=pretty                   # pretty, json

# ===== Development =====
APP_ENV=development                 # development, production, test
```

### MCP Server Configuration

Create `.env` in `mcp_server/` directory:

```env
# ===== Server =====
PORT=3001
HOST=localhost
LOG_LEVEL=info

# ===== Search =====
SEARCH_PROVIDER=duckduckgo          # duckduckgo (free) or serper (requires API key)
SERPER_API_KEY=                     # Required if SEARCH_PROVIDER=serper
MAX_SEARCH_RESULTS=5
SEARCH_TIMEOUT_MS=30000             # 30 seconds for search requests

# ===== Fetch =====
MAX_PAGE_SIZE=50000                 # Maximum characters to extract from a page
FETCH_TIMEOUT_MS=30000              # 30 seconds for page fetches

# ===== Database =====
DB_PATH=./data/notes.db

# ===== Rate Limits (per minute) =====
RATE_LIMIT_SEARCH=10
RATE_LIMIT_FETCH=30
RATE_LIMIT_NOTES=50
```

### Using Serper (Better Search Results)

1. Get API key from [serper.dev](https://serper.dev/)
2. Add to `.env`:

```env
SEARCH_PROVIDER=serper
SERPER_API_KEY=your_api_key_here
```

---

## Verification

### Run Environment Validation

```bash
python scripts/validate_env.py
```

Expected output:

```
✓ Python 3.12.0
✓ Required packages installed
✓ Ollama available at http://localhost:11434
✓ Model ministral-3:8b available
✓ MCP server available at http://localhost:3001
✓ All 5 MCP tools available

Environment validation passed!
```

### Run Tests

```bash
# Python tests
pytest tests/ -v

# MCP server tests
cd mcp_server && npm test
```

### Manual Verification

```bash
# 1. Check Ollama
curl http://localhost:11434/api/tags
# Should list available models

# 2. Check MCP Server
curl http://localhost:3001/health
# Should return {"status":"ok",...}

# 3. Test MCP Tool
curl -X POST http://localhost:3001/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":"1"}'
# Should list 5 tools
```

---

## Troubleshooting

### Common Issues

#### "Ollama not available"

**Symptoms:** Health check fails, app shows Ollama error

**Solutions:**

1. Start Ollama service:
   ```bash
   ollama serve
   ```

2. Check if running:
   ```bash
   curl http://localhost:11434
   ```

3. Check port conflict:
   ```bash
   lsof -i :11434
   ```

#### "MCP server not available"

**Symptoms:** Tools fail, MCP health check returns false

**Solutions:**

1. Check if server is running:
   ```bash
   curl http://localhost:3001/health
   ```

2. Start the server:
   ```bash
   cd mcp_server && npm start
   ```

3. Check for build errors:
   ```bash
   cd mcp_server && npm run build
   ```

4. Check logs for errors in terminal running MCP server

#### "Model not found"

**Symptoms:** Ollama returns model error

**Solutions:**

1. List available models:
   ```bash
   ollama list
   ```

2. Pull the model:
   ```bash
   ollama pull ministral-3:8b
   ```

3. Check `.env` has correct model name

#### "Port already in use"

**Symptoms:** Server fails to start with EADDRINUSE

**Solutions:**

1. Find process using port:
   ```bash
   lsof -i :3001   # MCP server
   lsof -i :8501   # Streamlit
   ```

2. Kill the process:
   ```bash
   kill -9 <PID>
   ```

3. Or change port in `.env`

#### "Search returns no results"

**Symptoms:** DuckDuckGo search always fails

**Solutions:**

1. This is normal for some queries with DuckDuckGo
2. Try different search terms
3. Consider using Serper for better results:
   ```env
   SEARCH_PROVIDER=serper
   SERPER_API_KEY=your_key
   ```

#### "Import errors in Python"

**Symptoms:** ModuleNotFoundError

**Solutions:**

1. Activate virtual environment:
   ```bash
   source .venv/bin/activate
   ```

2. Reinstall dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Check PYTHONPATH:
   ```bash
   export PYTHONPATH=$PWD:$PYTHONPATH
   ```

### Log Locations

| Component | Location |
|-----------|----------|
| Python app | Terminal output (stdout) |
| MCP server | Terminal output (stdout) |
| Ollama | `~/.ollama/logs/` |

### Debug Mode

Enable debug logging:

```env
LOG_LEVEL=debug
```

---

## Advanced Setup

### Running with Docker

```dockerfile
# Dockerfile (if using Docker)
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

### Running as Services

**systemd service (Linux):**

```ini
# /etc/systemd/system/research-copilot-mcp.service
[Unit]
Description=Research Copilot MCP Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/research-copilot/mcp_server
ExecStart=/usr/bin/npm start
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Production Deployment

For production use:

1. Set `APP_ENV=production`
2. Use `LOG_FORMAT=json` for structured logging
3. Configure proper rate limits
4. Set up HTTPS reverse proxy
5. Use process manager (PM2, systemd)

### Multiple Models

Configure multiple Ollama models:

```bash
# Pull models
ollama pull ministral-3:8b
ollama pull ministral-3:8b
ollama pull codellama

# Switch in app sidebar or .env
OLLAMA_DEFAULT_MODEL=ministral-3:8b
```

---

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/yourusername/research-copilot/issues)
- **Documentation:** See `docs/` directory
- **PRD:** `docs/research-copilot-prd-v1.5.md`

---

*Last updated: January 12, 2026*
