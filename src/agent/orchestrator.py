"""
Agent orchestrator for the research assistant.

Manages the tool-calling loop between the LLM and MCP tools.
Handles multi-turn conversations with tool execution and result integration.
"""

import asyncio
import uuid
from typing import AsyncIterator, List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from src.clients.ollama_client import OllamaClient
from src.clients.mcp_client import MCPClient
from src.errors import ResearchError, OllamaError, MCPError
from src.utils.config import settings
from src.utils.logger import setup_logger
from src.models.research_mode import RESEARCH_MODES, get_mode_by_key

from .parser import parse_tool_calls, ToolCall, ParseResult
from .prompts import build_system_prompt, format_tool_result

logger = setup_logger(__name__)


@dataclass
class ToolExecution:
    """Record of a tool execution."""
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    success: bool = True
    duration_ms: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    request_id: Optional[str] = None  # MCP request ID for traceability


@dataclass
class Source:
    """A source URL extracted from tool results."""
    url: str
    title: str
    tool: str  # Which tool provided this source


@dataclass
class ResearchResponse:
    """Complete response from a research query."""
    content: str
    tool_trace: List[ToolExecution]
    sources: List[Source]
    request_id: str
    total_duration_ms: float
    model: str
    # PRD §5.10 - Additional fields for UI polish
    can_save_as_note: bool = True  # Whether response can be saved
    suggested_title: str = ""  # Suggested title for saving as note
    followup_questions: List[str] = field(default_factory=list)  # LLM-generated follow-ups


@dataclass
class Message:
    """A message in the conversation."""
    role: str  # "system", "user", "assistant"
    content: str


class Orchestrator:
    """
    Orchestrates the research assistant's tool-calling loop.

    Manages the conversation between the user, LLM, and MCP tools.
    """

    MAX_TOOL_ITERATIONS = 5  # Reduced from 10 to fail faster on bad models
    TOOL_TIMEOUT_MS = 30000  # 30 seconds per tool call

    # Valid MCP tools - reject unknown tools immediately to prevent LLM hallucinations
    VALID_TOOLS = {"web_search", "fetch_page", "save_note", "list_notes", "get_note"}

    # Research modes now imported from src.models.research_mode (DRY)

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        mcp_client: Optional[MCPClient] = None,
        model: Optional[str] = None,
        research_mode: str = "quick",
        fetch_extract_mode: str = "text",
        temperature: Optional[float] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            ollama_client: Ollama client instance (creates one if not provided)
            mcp_client: MCP client instance (creates one if not provided)
            model: LLM model to use (defaults to config setting)
            research_mode: "quick" or "deep" - controls search/fetch limits
            temperature: LLM temperature (0.0-1.0, defaults to config setting)
        """
        self.ollama = ollama_client or OllamaClient()
        self.mcp = mcp_client or MCPClient()
        self.model = model or settings.ollama_default_model
        self.research_mode = research_mode if research_mode in RESEARCH_MODES else "quick"
        self.fetch_extract_mode = fetch_extract_mode if fetch_extract_mode in ["text", "markdown"] else "text"
        self.temperature = temperature if temperature is not None else settings.ollama_temperature
        self.conversation_history: List[Message] = []
        self._request_id: str = ""

    def set_research_mode(self, mode: str) -> None:
        """Set the research mode (quick or deep)."""
        if mode in RESEARCH_MODES:
            self.research_mode = mode
            logger.info(f"Research mode set to: {mode}")

    def set_fetch_extract_mode(self, mode: str) -> None:
        """Set the fetch extract mode (text or markdown)."""
        if mode in ["text", "markdown"]:
            self.fetch_extract_mode = mode
            logger.info(f"Fetch extract mode set to: {mode}")

    def set_model(self, model: str) -> None:
        """Set the LLM model for the orchestrator."""
        if model:
            self.model = model

    def set_temperature(self, temperature: float) -> None:
        """Set the LLM temperature (0.0-1.0, lower = more focused)."""
        if 0.0 <= temperature <= 1.0:
            self.temperature = temperature
            logger.info(f"Temperature set to: {temperature}")

    async def research(
        self,
        query: str,
        on_tool_start: Optional[Callable[[str, Dict], None]] = None,
        on_tool_complete: Optional[Callable[[str, Dict, bool], None]] = None,
        on_text_chunk: Optional[Callable[[str], None]] = None
    ) -> ResearchResponse:
        """
        Execute a research query with tool-calling support.

        Args:
            query: The user's research query
            on_tool_start: Callback when a tool starts executing
            on_tool_complete: Callback when a tool completes
            on_text_chunk: Callback for streaming text chunks

        Returns:
            ResearchResponse with the complete answer and metadata
        """
        start_time = datetime.now()
        self._request_id = str(uuid.uuid4())[:8]

        logger.info(
            "Starting research",
            extra={
                "request_id": self._request_id,
                "query": query[:100],
                "model": self.model
            }
        )

        tool_trace: List[ToolExecution] = []
        sources: List[Source] = []

        # Build initial messages with research mode context
        messages = [
            {"role": "system", "content": build_system_prompt(research_mode=self.research_mode)},
            {"role": "user", "content": query}
        ]

        # Add conversation history if any
        for msg in self.conversation_history:
            messages.insert(-1, {"role": msg.role, "content": msg.content})

        final_response = ""
        iterations = 0

        while iterations < self.MAX_TOOL_ITERATIONS:
            iterations += 1

            # Get LLM response
            try:
                llm_response = await self._get_llm_response(
                    messages,
                    on_text_chunk if iterations == 1 else None
                )
            except OllamaError as e:
                logger.error(f"LLM error: {e}")
                raise

            # Debug: Log first 500 chars of LLM response to diagnose tool call issues
            logger.debug(
                f"LLM response preview (iteration {iterations}): {llm_response[:500]}...",
                extra={"request_id": self._request_id}
            )

            # Parse for tool calls
            parse_result = parse_tool_calls(llm_response)

            # Debug: Log parse result
            logger.info(
                f"Parsed {len(parse_result.tool_calls)} tool calls from response",
                extra={"request_id": self._request_id, "has_incomplete": parse_result.has_incomplete}
            )

            # If no tool calls, we're done
            if not parse_result.tool_calls:
                final_response = llm_response
                break

            # Execute tool calls
            tool_results = []
            for tool_call in parse_result.tool_calls:
                execution = await self._execute_tool(
                    tool_call,
                    on_tool_start,
                    on_tool_complete
                )
                tool_trace.append(execution)

                # Extract sources from results
                if execution.success and execution.result:
                    extracted_sources = self._extract_sources(
                        tool_call.name,
                        execution.result
                    )
                    sources.extend(extracted_sources)

                # Format result for LLM
                result_text = format_tool_result(
                    tool_call.name,
                    execution.result if execution.success else {"message": execution.error, "code": "error"},
                    execution.success
                )
                tool_results.append(result_text)

            # Add assistant message with tool call
            messages.append({
                "role": "assistant",
                "content": llm_response
            })

            # Add tool results as a new message
            messages.append({
                "role": "user",
                "content": "Tool results:\n\n" + "\n\n".join(tool_results)
            })

        # If loop exhausted without final response, request a summary
        if not final_response:
            logger.info(
                "Requesting final summary after tool iterations",
                extra={"request_id": self._request_id, "iterations": iterations}
            )
            # Add a prompt asking for the final answer
            messages.append({
                "role": "user",
                "content": "Based on all the information gathered above, please provide your final answer to the original question. Do not make any more tool calls - just summarize what you learned."
            })
            try:
                final_response = await self._get_llm_response(messages)
                # Strip any accidental tool calls from the response
                if "<tool_call>" in final_response:
                    # Extract just the text before any tool calls
                    final_response = final_response.split("<tool_call>")[0].strip()
                if not final_response:
                    final_response = "I gathered information from multiple sources but couldn't generate a complete summary. Please check the sources below for details."
            except Exception as e:
                logger.error(f"Failed to get final summary: {e}")
                final_response = "Research completed but summary generation failed. Please check the sources below."

        # Calculate total duration
        total_duration = (datetime.now() - start_time).total_seconds() * 1000

        # Update conversation history
        self.conversation_history.append(Message(role="user", content=query))
        self.conversation_history.append(Message(role="assistant", content=final_response))

        logger.info(
            "Research complete",
            extra={
                "request_id": self._request_id,
                "duration_ms": total_duration,
                "tool_calls": len(tool_trace),
                "sources": len(sources)
            }
        )

        # Generate suggested title from query (PRD §5.10)
        suggested_title = self._generate_suggested_title(query)

        # Determine if response can be saved (non-error, has content)
        can_save = bool(final_response and not final_response.startswith("❌"))

        # Generate LLM-based follow-up questions (PRD §5.10 Demo Polish Pack)
        deduplicated_sources = self._deduplicate_sources(sources)
        followup_questions = await self._generate_followup_questions(
            query, final_response, deduplicated_sources
        )

        return ResearchResponse(
            content=final_response,
            tool_trace=tool_trace,
            sources=deduplicated_sources,
            request_id=self._request_id,
            total_duration_ms=total_duration,
            model=self.model,
            can_save_as_note=can_save,
            suggested_title=suggested_title,
            followup_questions=followup_questions
        )

    async def research_stream(
        self,
        query: str,
        on_tool_start: Optional[Callable[[str, Dict], None]] = None,
        on_tool_complete: Optional[Callable[[str, Dict, bool], None]] = None
    ) -> AsyncIterator[str]:
        """
        Execute a research query with streaming response.

        Args:
            query: The user's research query
            on_tool_start: Callback when a tool starts executing
            on_tool_complete: Callback when a tool completes

        Yields:
            Text chunks as they are generated
        """
        start_time = datetime.now()
        self._request_id = str(uuid.uuid4())[:8]

        tool_trace: List[ToolExecution] = []
        sources: List[Source] = []

        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": query}
        ]

        for msg in self.conversation_history:
            messages.insert(-1, {"role": msg.role, "content": msg.content})

        iterations = 0
        accumulated_response = ""

        while iterations < self.MAX_TOOL_ITERATIONS:
            iterations += 1

            # Stream LLM response with temperature
            current_response = ""
            async for chunk in self.ollama.chat_stream(
                messages=messages,
                model=self.model,
                options={"temperature": self.temperature}
            ):
                current_response += chunk

                # Check if we're in a tool call
                if "<tool_call>" in current_response:
                    # Don't yield tool call content
                    if "</tool_call>" in current_response:
                        # Tool call complete, process it
                        break
                else:
                    # Yield text chunks
                    yield chunk

            # Parse for tool calls
            parse_result = parse_tool_calls(current_response)

            if not parse_result.tool_calls:
                accumulated_response = current_response
                break

            # Execute tool calls
            tool_results = []
            for tool_call in parse_result.tool_calls:
                # Notify UI that tool is starting
                if on_tool_start:
                    on_tool_start(tool_call.name, tool_call.arguments)

                execution = await self._execute_tool(
                    tool_call,
                    on_tool_start,
                    on_tool_complete
                )
                tool_trace.append(execution)

                if execution.success and execution.result:
                    extracted_sources = self._extract_sources(
                        tool_call.name,
                        execution.result
                    )
                    sources.extend(extracted_sources)

                result_text = format_tool_result(
                    tool_call.name,
                    execution.result if execution.success else {"message": execution.error},
                    execution.success
                )
                tool_results.append(result_text)

            messages.append({"role": "assistant", "content": current_response})
            messages.append({
                "role": "user",
                "content": "Tool results:\n\n" + "\n\n".join(tool_results)
            })

        # Update conversation history
        self.conversation_history.append(Message(role="user", content=query))
        self.conversation_history.append(Message(role="assistant", content=accumulated_response))

    async def _get_llm_response(
        self,
        messages: List[Dict[str, str]],
        on_chunk: Optional[Callable[[str], None]] = None
    ) -> str:
        """Get a complete response from the LLM."""
        # Build options with temperature
        options = {"temperature": self.temperature}

        if on_chunk:
            # Use streaming
            full_response = ""
            async for chunk in self.ollama.chat_stream(
                messages=messages,
                model=self.model,
                options=options
            ):
                full_response += chunk
                on_chunk(chunk)
            return full_response
        else:
            # Non-streaming
            response = await self.ollama.chat(
                messages=messages,
                model=self.model,
                stream=False,
                options=options
            )
            return response.message.content

    async def _execute_tool(
        self,
        tool_call: ToolCall,
        on_start: Optional[Callable[[str, Dict], None]] = None,
        on_complete: Optional[Callable[[str, Dict, bool], None]] = None
    ) -> ToolExecution:
        """Execute a single tool call."""
        start_time = datetime.now()

        # Validate tool name to prevent LLM hallucinations from wasting time
        if tool_call.name not in self.VALID_TOOLS:
            logger.warning(
                f"Skipping unknown tool: {tool_call.name}",
                extra={"request_id": self._request_id, "tool_name": tool_call.name}
            )
            if on_complete:
                on_complete(tool_call.name, {}, False)
            return ToolExecution(
                tool_name=tool_call.name,
                arguments=tool_call.arguments,
                error=f"Unknown tool: {tool_call.name}. Valid tools: {', '.join(self.VALID_TOOLS)}",
                success=False,
                duration_ms=0,
                request_id=self._request_id
            )

        if tool_call.name == "fetch_page" and "extract_mode" not in tool_call.arguments:
            tool_call.arguments["extract_mode"] = self.fetch_extract_mode

        if on_start:
            on_start(tool_call.name, tool_call.arguments)

        logger.info(
            f"Executing tool: {tool_call.name}",
            extra={
                "request_id": self._request_id,
                "tool_name": tool_call.name,
                "arguments": tool_call.arguments
            }
        )

        try:
            result = await self.mcp.call_tool(
                tool_call.name,
                tool_call.arguments,
                request_id=self._request_id
            )

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            if result.success:
                execution = ToolExecution(
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                    result=result.data,
                    success=True,
                    duration_ms=duration_ms,
                    request_id=self._request_id
                )
            else:
                execution = ToolExecution(
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                    error=result.error if result.error else "Unknown error",
                    success=False,
                    duration_ms=duration_ms,
                    request_id=self._request_id
                )

            if on_complete:
                on_complete(
                    tool_call.name,
                    result.data if result.success else {},
                    result.success
                )

            return execution

        except MCPError as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            logger.error(
                f"Tool execution failed: {tool_call.name}",
                extra={
                    "request_id": self._request_id,
                    "error": str(e)
                }
            )

            if on_complete:
                on_complete(tool_call.name, {}, False)

            return ToolExecution(
                tool_name=tool_call.name,
                arguments=tool_call.arguments,
                error=str(e),
                success=False,
                duration_ms=duration_ms,
                request_id=self._request_id
            )

    def _extract_sources(
        self,
        tool_name: str,
        result: Dict[str, Any]
    ) -> List[Source]:
        """Extract source URLs from a tool result."""
        sources = []

        if tool_name == "web_search":
            for item in result.get("results", []):
                sources.append(Source(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    tool="web_search"
                ))

        elif tool_name == "fetch_page":
            sources.append(Source(
                url=result.get("url", ""),
                title=result.get("title", ""),
                tool="fetch_page"
            ))

        elif tool_name == "get_note":
            note = result.get("note", {})
            for url in note.get("source_urls", []):
                sources.append(Source(
                    url=url,
                    title="From saved note",
                    tool="get_note"
                ))

        return sources

    def _deduplicate_sources(self, sources: List[Source]) -> List[Source]:
        """Remove duplicate sources, keeping the first occurrence."""
        seen_urls = set()
        unique_sources = []

        for source in sources:
            if source.url and source.url not in seen_urls:
                seen_urls.add(source.url)
                unique_sources.append(source)

        return unique_sources

    def _generate_suggested_title(self, query: str) -> str:
        """
        Generate a suggested title from the query.

        Per PRD §5.10 - One-click Note with prefilled title.

        Args:
            query: The user's original query

        Returns:
            A suggested title for the note (max 80 chars)
        """
        # Clean up query
        title = query.strip()

        # Remove question marks and common prefixes
        for prefix in ["what is", "what are", "how to", "how do", "why", "can you"]:
            if title.lower().startswith(prefix):
                title = title[len(prefix):].strip()
                break

        # Capitalize first letter
        if title:
            title = title[0].upper() + title[1:]

        # Truncate and add suffix
        if len(title) > 70:
            title = title[:67] + "..."

        # Add "Research: " prefix if not too long
        if len(title) < 60:
            title = f"Research: {title}"

        return title[:80]  # Max 80 chars per PRD

    async def _generate_followup_questions(
        self,
        query: str,
        response_content: str,
        sources: List[Source]
    ) -> List[str]:
        """
        Generate contextual follow-up questions using the LLM.

        Per PRD §5.10 Demo Polish Pack - LLM-generated follow-up suggestions.
        Replaces the rule-based approach for better context awareness.

        Args:
            query: The user's original query
            response_content: The research response content
            sources: List of sources used in the response

        Returns:
            List of 3 follow-up question suggestions
        """
        # Build a focused prompt for generating follow-ups
        source_titles = [s.title for s in sources[:3]] if sources else []
        source_context = f"Sources used: {', '.join(source_titles)}" if source_titles else ""

        followup_prompt = f"""Based on this research interaction, suggest exactly 3 follow-up questions the user might want to ask next.

Original question: {query}

Research summary (first 500 chars): {response_content[:500]}...

{source_context}

Requirements:
- Generate exactly 3 questions
- Each question should explore a different aspect or go deeper
- Questions should be specific and actionable
- Keep each question under 60 characters
- Format: Output ONLY the 3 questions, one per line, no numbering or bullets

Example output format:
How does this compare to alternatives?
What are the main limitations?
Can you show a practical example?"""

        try:
            # Use a quick LLM call for follow-up generation
            response = await self.ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": followup_prompt}],
                options={"temperature": 0.7, "num_predict": 200}  # Slightly creative, short response
            )

            if response and response.message and response.message.content:
                # Parse the response into individual questions
                lines = response.message.content.strip().split('\n')
                questions = []
                for line in lines:
                    # Clean up each line
                    q = line.strip().strip('0123456789.-) ').strip()
                    if q and len(q) > 10 and q.endswith('?'):
                        questions.append(q[:80])  # Max 80 chars
                    if len(questions) >= 3:
                        break

                if questions:
                    logger.debug(f"Generated {len(questions)} follow-up questions")
                    return questions[:3]

        except Exception as e:
            logger.warning(f"Failed to generate follow-up questions: {e}")

        # Fallback to basic questions if LLM fails
        return self._fallback_followup_questions(query)

    def _fallback_followup_questions(self, query: str) -> List[str]:
        """
        Generate basic follow-up questions as fallback.

        Used when LLM-based generation fails.
        """
        query_lower = query.lower()
        topic = query.replace("?", "").strip()

        # Extract topic from common patterns
        for prefix in ["what is", "what are", "how to", "how do", "why is", "why are"]:
            if query_lower.startswith(prefix):
                topic = query[len(prefix):].strip().strip("?")
                break

        if len(topic) > 30:
            topic = topic[:30]

        return [
            f"What are the pros and cons of {topic}?",
            f"Can you show a practical example?",
            f"How does this compare to alternatives?"
        ]

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all services."""
        ollama_health = await self.ollama.is_available()
        mcp_health = await self.mcp.health()

        return {
            "ollama": {
                "available": ollama_health,
                "model": self.model
            },
            "mcp": {
                "available": mcp_health.available,
                "tools": mcp_health.tools if mcp_health.available else []
            }
        }
