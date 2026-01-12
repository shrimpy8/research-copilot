#!/bin/bash
# Start all services for Research Copilot
#
# Usage: ./scripts/start.sh
#
# This script starts:
# 1. Ollama (if not already running)
# 2. MCP Server (in background)
# 3. Streamlit app

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting Research Copilot..."
echo ""

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo "📦 Starting Ollama..."
    echo "   Run 'ollama serve' in a separate terminal"
    echo "   Press Enter when Ollama is running..."
    read -r
fi

# Verify Ollama is now running
if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo "✓ Ollama is running"
else
    echo "✗ Ollama is not running. Please start it first."
    exit 1
fi

# Check for MCP server directory
if [ ! -d "$PROJECT_ROOT/mcp_server" ]; then
    echo "⚠️  MCP server directory not found. Skipping MCP server start."
    echo "   (MCP server will be created in Milestone 2)"
else
    # Start MCP server in background
    echo "📦 Starting MCP server..."
    cd "$PROJECT_ROOT/mcp_server"
    if [ -f "package.json" ]; then
        npm start &
        MCP_PID=$!
        echo "   MCP server starting (PID: $MCP_PID)..."
        sleep 2
    else
        echo "   MCP server not yet set up (will be done in Milestone 2)"
    fi
    cd "$PROJECT_ROOT"
fi

# Start Streamlit
echo "📦 Starting Streamlit app..."
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

streamlit run app.py

# Cleanup on exit
trap "echo 'Stopping services...'; kill $MCP_PID 2>/dev/null" EXIT
