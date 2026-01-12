#!/bin/bash
# Run all tests for Research Copilot
#
# Usage: ./scripts/test.sh [options]
#
# Options:
#   --unit       Run only unit tests
#   --integration Run only integration tests
#   --coverage   Generate coverage report
#   --verbose    Verbose output

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Parse arguments
UNIT_ONLY=false
INTEGRATION_ONLY=false
COVERAGE=false
VERBOSE=""

for arg in "$@"; do
    case $arg in
        --unit)
            UNIT_ONLY=true
            ;;
        --integration)
            INTEGRATION_ONLY=true
            ;;
        --coverage)
            COVERAGE=true
            ;;
        --verbose|-v)
            VERBOSE="-v"
            ;;
    esac
done

echo "🧪 Running Research Copilot Tests"
echo "=================================="
echo ""

# Build pytest command
PYTEST_CMD="pytest $VERBOSE"

if $COVERAGE; then
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=term-missing --cov-report=html"
fi

# Run appropriate tests
if $UNIT_ONLY; then
    echo "Running unit tests..."
    $PYTEST_CMD tests/unit/
elif $INTEGRATION_ONLY; then
    echo "Running integration tests..."
    $PYTEST_CMD tests/integration/
else
    echo "Running all tests..."
    $PYTEST_CMD tests/
fi

# Report
if $COVERAGE; then
    echo ""
    echo "Coverage report generated in htmlcov/"
fi

echo ""
echo "✅ Tests complete!"
