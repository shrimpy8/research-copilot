"""
Ollama HTTP client for Research Copilot.

Provides async communication with the Ollama API for LLM inference.
Includes health checking, retry logic, and streaming support.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

import httpx

from src.errors import ErrorCodes, OllamaError
from src.utils.config import settings
from src.utils.logger import setup_logger

logger = setup_logger("research_copilot.ollama")


@dataclass
class OllamaHealthStatus:
    """Status of the Ollama service."""

    available: bool
    version: Optional[str] = None
    models: list[str] | None = None
    error: Optional[str] = None


@dataclass
class ChatMessage:
    """A message in a chat conversation."""

    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class ChatResponse:
    """Response from Ollama chat endpoint."""

    model: str
    message: ChatMessage
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class OllamaClient:
    """
    Async HTTP client for Ollama API.

    Provides methods for:
    - Health checking and model listing
    - Chat completions with streaming support
    - Retry logic for transient failures

    Usage:
        client = OllamaClient()
        async with client:
            health = await client.health()
            if health.available:
                response = await client.chat([{"role": "user", "content": "Hello"}])
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        """
        Initialize the Ollama client.

        Args:
            base_url: Ollama API base URL (default from settings)
            model: Default model to use (default from settings)
            timeout_seconds: Request timeout in seconds (default from settings)
            max_retries: Maximum retry attempts (default from settings)
        """
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_default_model
        self.timeout_seconds = timeout_seconds or settings.ollama_timeout_seconds
        self.max_retries = max_retries or settings.ollama_max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "OllamaClient":
        """Enter async context and create HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout_seconds),
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
            )
        return self._client

    async def health(self) -> OllamaHealthStatus:
        """
        Check Ollama service health and list available models.

        Returns:
            OllamaHealthStatus with availability, version, and models

        Note:
            Does not raise exceptions - returns status with available=False on error
        """
        try:
            client = self._get_client()

            # Check if Ollama is responding
            response = await client.get("/api/version")
            if response.status_code != 200:
                return OllamaHealthStatus(
                    available=False,
                    error=f"Unexpected status code: {response.status_code}",
                )

            version_data = response.json()

            # List available models
            models_response = await client.get("/api/tags")
            models = []
            if models_response.status_code == 200:
                models_data = models_response.json()
                models = [m["name"] for m in models_data.get("models", [])]

            return OllamaHealthStatus(
                available=True,
                version=version_data.get("version"),
                models=models,
            )

        except httpx.ConnectError as e:
            logger.debug(f"Ollama connection error: {e}")
            return OllamaHealthStatus(
                available=False,
                error="Cannot connect to Ollama. Is it running?",
            )
        except httpx.TimeoutException:
            logger.debug("Ollama health check timed out")
            return OllamaHealthStatus(
                available=False,
                error="Connection timed out",
            )
        except Exception as e:
            logger.exception("Unexpected error checking Ollama health")
            return OllamaHealthStatus(
                available=False,
                error=str(e),
            )

    async def is_available(self) -> bool:
        """
        Quick check if Ollama is available.

        Returns:
            True if Ollama is responding, False otherwise
        """
        health = await self.health()
        return health.available

    async def has_model(self, model: Optional[str] = None) -> bool:
        """
        Check if a specific model is available.

        Args:
            model: Model name to check (default: configured model)

        Returns:
            True if the model is available, False otherwise
        """
        model = model or self.model
        health = await self.health()
        if not health.available or not health.models:
            return False
        return model in health.models

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> ChatResponse:
        """
        Send a chat completion request to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (default: configured model)
            stream: Whether to stream the response (for streaming, use chat_stream)
            **kwargs: Additional parameters to pass to Ollama

        Returns:
            ChatResponse with the model's reply

        Raises:
            OllamaError: If the request fails
        """
        model = model or self.model
        client = self._get_client()

        request_body = {
            "model": model,
            "messages": messages,
            "stream": False,  # Non-streaming for this method
            **kwargs,
        }

        logger.debug(f"Sending chat request to Ollama: model={model}")

        for attempt in range(self.max_retries):
            try:
                response = await client.post("/api/chat", json=request_body)

                if response.status_code == 404:
                    raise OllamaError(
                        code=ErrorCodes.OLLAMA_MODEL_NOT_FOUND,
                        message=f"Model '{model}' is not installed",
                        model=model,
                        suggestion=f"Run: ollama pull {model}",
                    )

                if response.status_code != 200:
                    raise OllamaError(
                        code=ErrorCodes.OLLAMA_UNAVAILABLE,
                        message=f"Ollama returned status {response.status_code}",
                        model=model,
                    )

                data = response.json()
                return ChatResponse(
                    model=data.get("model", model),
                    message=ChatMessage(
                        role=data.get("message", {}).get("role", "assistant"),
                        content=data.get("message", {}).get("content", ""),
                    ),
                    done=data.get("done", True),
                    total_duration=data.get("total_duration"),
                    load_duration=data.get("load_duration"),
                    prompt_eval_count=data.get("prompt_eval_count"),
                    eval_count=data.get("eval_count"),
                    eval_duration=data.get("eval_duration"),
                )

            except OllamaError:
                raise
            except httpx.ConnectError:
                if attempt == self.max_retries - 1:
                    raise OllamaError(
                        code=ErrorCodes.OLLAMA_UNAVAILABLE,
                        message="Cannot connect to Ollama",
                        suggestion="Make sure Ollama is running: ollama serve",
                    )
                await asyncio.sleep(1)
            except httpx.TimeoutException:
                if attempt == self.max_retries - 1:
                    raise OllamaError(
                        code=ErrorCodes.OLLAMA_TIMEOUT,
                        message="Ollama request timed out",
                        suggestion="Try a shorter query or increase timeout",
                    )
                await asyncio.sleep(1)

        # Should not reach here, but just in case
        raise OllamaError(
            code=ErrorCodes.OLLAMA_UNAVAILABLE,
            message="Failed to connect to Ollama after retries",
        )

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion response from Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (default: configured model)
            **kwargs: Additional parameters to pass to Ollama

        Yields:
            Content chunks as they arrive

        Raises:
            OllamaError: If the request fails
        """
        model = model or self.model
        client = self._get_client()

        request_body = {
            "model": model,
            "messages": messages,
            "stream": True,
            **kwargs,
        }

        logger.debug(f"Starting streaming chat request: model={model}")

        try:
            async with client.stream(
                "POST",
                "/api/chat",
                json=request_body,
            ) as response:
                if response.status_code == 404:
                    raise OllamaError(
                        code=ErrorCodes.OLLAMA_MODEL_NOT_FOUND,
                        message=f"Model '{model}' is not installed",
                        model=model,
                        suggestion=f"Run: ollama pull {model}",
                    )

                if response.status_code != 200:
                    raise OllamaError(
                        code=ErrorCodes.OLLAMA_UNAVAILABLE,
                        message=f"Ollama returned status {response.status_code}",
                        model=model,
                    )

                # Stream the response line by line
                import json as json_module

                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json_module.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if data.get("done", False):
                                break
                        except json_module.JSONDecodeError:
                            continue

        except httpx.ConnectError:
            raise OllamaError(
                code=ErrorCodes.OLLAMA_UNAVAILABLE,
                message="Cannot connect to Ollama",
                suggestion="Make sure Ollama is running: ollama serve",
            )
        except httpx.TimeoutException:
            raise OllamaError(
                code=ErrorCodes.OLLAMA_TIMEOUT,
                message="Ollama request timed out",
                suggestion="Try a shorter query or increase timeout",
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
