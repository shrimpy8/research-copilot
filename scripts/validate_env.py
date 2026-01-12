#!/usr/bin/env python3
"""
Environment validation script for Research Copilot.

Validates that all dependencies, services, and configuration are correctly set up.
Run this script to verify your environment is ready for development or production.

Usage:
    python scripts/validate_env.py
    python scripts/validate_env.py --verbose
    python scripts/validate_env.py --skip-services
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ValidationResult:
    """Result of a validation check."""

    def __init__(
        self,
        name: str,
        passed: bool,
        message: str,
        suggestion: Optional[str] = None,
    ):
        self.name = name
        self.passed = passed
        self.message = message
        self.suggestion = suggestion


def check_python_version() -> ValidationResult:
    """Check Python version is 3.10+."""
    version = sys.version_info
    passed = version.major == 3 and version.minor >= 10

    return ValidationResult(
        name="Python Version",
        passed=passed,
        message=f"Python {version.major}.{version.minor}.{version.micro}",
        suggestion="Install Python 3.10 or higher" if not passed else None,
    )


def check_dependencies() -> ValidationResult:
    """Check that all required Python packages are installed."""
    missing = []
    required_packages = [
        ("streamlit", "streamlit"),
        ("httpx", "httpx"),
        ("pydantic", "pydantic"),
        ("pydantic_settings", "pydantic-settings"),
        ("dotenv", "python-dotenv"),
    ]

    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)

    if missing:
        return ValidationResult(
            name="Python Dependencies",
            passed=False,
            message=f"Missing: {', '.join(missing)}",
            suggestion=f"Run: pip install {' '.join(missing)}",
        )

    return ValidationResult(
        name="Python Dependencies",
        passed=True,
        message="All required packages installed",
    )


def check_env_file() -> ValidationResult:
    """Check that .env file exists."""
    env_path = project_root / ".env"
    example_path = project_root / ".env.example"

    if env_path.exists():
        return ValidationResult(
            name=".env File",
            passed=True,
            message=".env file found",
        )

    suggestion = "Copy .env.example to .env and configure"
    if example_path.exists():
        suggestion = "Run: cp .env.example .env"

    return ValidationResult(
        name=".env File",
        passed=False,
        message=".env file not found",
        suggestion=suggestion,
    )


def check_configuration() -> ValidationResult:
    """Check that configuration loads correctly."""
    try:
        from src.utils.config import settings

        # Verify some key settings are present
        assert settings.ollama_base_url
        assert settings.mcp_server_url
        assert settings.app_env in ("development", "production", "test")

        return ValidationResult(
            name="Configuration",
            passed=True,
            message=f"Loaded ({settings.app_env} mode)",
        )

    except Exception as e:
        return ValidationResult(
            name="Configuration",
            passed=False,
            message=f"Error: {str(e)}",
            suggestion="Check .env file for invalid values",
        )


def check_data_directory() -> ValidationResult:
    """Check that data directory exists and is writable."""
    data_dir = project_root / "data"

    try:
        data_dir.mkdir(parents=True, exist_ok=True)

        # Try to write a test file
        test_file = data_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()

        return ValidationResult(
            name="Data Directory",
            passed=True,
            message=f"{data_dir} is writable",
        )

    except Exception as e:
        return ValidationResult(
            name="Data Directory",
            passed=False,
            message=f"Error: {str(e)}",
            suggestion="Check directory permissions",
        )


async def check_ollama() -> ValidationResult:
    """Check that Ollama is running and accessible."""
    try:
        from src.clients.ollama_client import OllamaClient
        from src.utils.config import settings

        async with OllamaClient() as client:
            health = await client.health()

            if not health.available:
                return ValidationResult(
                    name="Ollama Service",
                    passed=False,
                    message=health.error or "Not available",
                    suggestion="Run: ollama serve",
                )

            # Check for default model
            model = settings.ollama_default_model
            has_model = model in (health.models or [])

            if not has_model:
                return ValidationResult(
                    name="Ollama Service",
                    passed=True,  # Partial pass - Ollama works but model missing
                    message=f"Running (v{health.version}), but model '{model}' not found",
                    suggestion=f"Run: ollama pull {model}",
                )

            return ValidationResult(
                name="Ollama Service",
                passed=True,
                message=f"Running (v{health.version}), model '{model}' available",
            )

    except Exception as e:
        return ValidationResult(
            name="Ollama Service",
            passed=False,
            message=f"Error: {str(e)}",
            suggestion="Make sure Ollama is installed and running",
        )


async def check_mcp_server() -> ValidationResult:
    """Check that MCP server is running and accessible."""
    try:
        from src.clients.mcp_client import MCPClient

        async with MCPClient() as client:
            health = await client.health()

            if not health.available:
                return ValidationResult(
                    name="MCP Server",
                    passed=False,
                    message=health.error or "Not available",
                    suggestion="Run: cd mcp_server && npm start",
                )

            tools = health.tools or []
            tool_count = len(tools)

            return ValidationResult(
                name="MCP Server",
                passed=True,
                message=f"Running with {tool_count} tools available",
            )

    except Exception as e:
        return ValidationResult(
            name="MCP Server",
            passed=False,
            message=f"Error: {str(e)}",
            suggestion="Start the MCP server: cd mcp_server && npm start",
        )


def print_result(result: ValidationResult, verbose: bool = False) -> None:
    """Print a validation result with formatting."""
    icon = "✓" if result.passed else "✗"
    color_start = "\033[32m" if result.passed else "\033[31m"
    color_end = "\033[0m"

    print(f"  {color_start}{icon}{color_end} {result.name}: {result.message}")

    if not result.passed and result.suggestion:
        print(f"    → {result.suggestion}")


async def main() -> int:
    """Run all validation checks."""
    parser = argparse.ArgumentParser(description="Validate Research Copilot environment")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "--skip-services",
        action="store_true",
        help="Skip checking external services (Ollama, MCP)",
    )
    args = parser.parse_args()

    print("\n🔍 Research Copilot Environment Validation\n")
    print("=" * 50)

    results: list[ValidationResult] = []

    # Basic checks
    print("\n📋 Basic Requirements:")
    results.append(check_python_version())
    print_result(results[-1], args.verbose)

    results.append(check_dependencies())
    print_result(results[-1], args.verbose)

    results.append(check_env_file())
    print_result(results[-1], args.verbose)

    results.append(check_configuration())
    print_result(results[-1], args.verbose)

    results.append(check_data_directory())
    print_result(results[-1], args.verbose)

    # Service checks
    if not args.skip_services:
        print("\n🔧 External Services:")

        result = await check_ollama()
        results.append(result)
        print_result(result, args.verbose)

        result = await check_mcp_server()
        results.append(result)
        print_result(result, args.verbose)

    # Summary
    print("\n" + "=" * 50)
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    all_passed = passed == total

    if all_passed:
        print("\n✅ All checks passed! Environment is ready.\n")
        return 0
    else:
        print(f"\n⚠️  {passed}/{total} checks passed. Please fix the issues above.\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
