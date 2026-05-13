# Research Copilot -- Code Quality Audit

**Date:** 2026-05-13
**Auditor:** Claude Opus
**Scope:** Full codebase review (Python app + Node.js MCP server)

## Summary

| Severity | Count |
|----------|-------|
| Critical (P0) | 3 |
| High (P1) | 8 |
| Medium (P2) | 14 |
| Low (P3) | 7 |
| **Total** | **32** |

The codebase is well-structured with good separation of concerns, typed models, and thoughtful error handling. The most critical findings are: (1) an API key committed in a local `.env` file that could accidentally be pushed, (2) f-string logging throughout the Python code violating structlog best practices, (3) an XSS vulnerability in the Streamlit HTML rendering of user-influenced content. High-severity issues include resource leaks from HTTP clients, a `LogContext` race condition, deprecated `asyncio.get_event_loop()` usage, and missing input validation at the MCP server boundary.

---

## Issues and Fixes

### Critical (P0)

#### Issue #1: API Key Exposed in Local `.env` Files
- **File:** `.env:63` and `mcp_server/.env:27`
- **Category:** Security
- **Severity:** P0
- **Problem:** Both `.env` files contain an actual Serper API key (`78ed6c00a4fb6687fbb540d5810fc9c57b892b95`). While `.env` is in `.gitignore` and not tracked, these files exist on disk and could be accidentally committed via `git add -A` or copied. The key value is identical in both files, confirming it is a real credential.
- **Impact:** If either `.env` is ever committed (e.g., gitignore changed, force-add), the API key is leaked. The key is already present in the working directory and could be captured by any tool with file access.
- **Surgical Fix:**
Rotate the Serper API key immediately. In both `.env` files, replace the hardcoded key with a placeholder and load from a secrets manager or manual entry:
```env
# Before (.env:63):
SEARCH_API_KEY=78ed6c00a4fb6687fbb540d5810fc9c57b892b95

# After:
SEARCH_API_KEY=your_serper_api_key_here
```
```env
# Before (mcp_server/.env:27):
SERPER_API_KEY=78ed6c00a4fb6687fbb540d5810fc9c57b892b95

# After:
SERPER_API_KEY=your_serper_api_key_here
```

#### Issue #2: XSS via Unsanitized HTML Injection in Source Cards and Citations
- **File:** `src/ui/components.py:161-170` and `src/ui/components.py:498-503`
- **Category:** Security
- **Severity:** P0
- **Problem:** `render_source_card()` injects `title`, `url`, and `snippet` directly into raw HTML via `unsafe_allow_html=True` without escaping. Similarly, `render_content_with_citations()` injects `url` and `title` from source dicts into HTML `<a>` tags. These values originate from web search results and fetched pages -- attacker-controlled content. A malicious page title like `<img src=x onerror=alert(1)>` would execute JavaScript.
- **Impact:** Stored XSS in the Streamlit app. An attacker who controls a search result or page title can execute arbitrary JavaScript in the user's browser session.
- **Surgical Fix:**
```python
# Before (src/ui/components.py:161-170):
            <div style="
                border: 1px solid #E9ECEF;
                border-radius: 8px;
                padding: 12px;
                margin: 8px 0;
                background: #F8F9FA;
            ">
                <div style="font-weight: 600; color: #0066CC;">
                    [{number}] {title[:60]}{'...' if len(title) > 60 else ''}
                    {badge_html}
                </div>
                <div style="font-size: 12px; color: #6C757D; margin-top: 4px;">
                    <a href="{url}" target="_blank" style="color: #0066CC;">{url[:50]}{'...' if len(url) > 50 else ''}</a>
                </div>
                {f'<div style="font-size: 14px; margin-top: 8px; color: #1A1A1A;">{snippet[:150]}...</div>' if snippet else ''}
            </div>

# After:
# At the top of render_source_card(), add:
import html as html_module
# Then escape all user-provided values:
safe_title = html_module.escape(title[:60]) + ('...' if len(title) > 60 else '')
safe_url = html_module.escape(url)
safe_url_display = html_module.escape(url[:50]) + ('...' if len(url) > 50 else '')
safe_snippet = html_module.escape(snippet[:150]) + '...' if snippet else ''
# Use safe_title, safe_url, safe_url_display, safe_snippet in the HTML template
```
Apply the same pattern in `render_content_with_citations()` -- the `url` value is already being passed through `html.escape` for `title` but the `url` itself used in `href="{url}"` is NOT escaped:
```python
# Before (src/ui/components.py:502):
            return f'<a href="{url}" target="_blank" title="{escaped_title}" ...'

# After:
            escaped_url = html.escape(url, quote=True)
            return f'<a href="{escaped_url}" target="_blank" title="{escaped_title}" ...'
```

#### Issue #3: `LogContext` Sets Global Log Record Factory -- Race Condition
- **File:** `src/utils/logger.py:237-255`
- **Category:** Logic / Concurrency
- **Severity:** P0
- **Problem:** `LogContext` uses `logging.setLogRecordFactory()` which is process-global. In Streamlit's multi-threaded environment (or any concurrent usage), two `LogContext` instances active simultaneously will overwrite each other's factory and restore incorrectly, leading to cross-contamination of log fields or lost context.
- **Impact:** Log fields from one request appear on another request's logs. In the worst case, a `request_id` from one user's query leaks into another user's log entries, making debugging impossible and potentially leaking correlation information.
- **Surgical Fix:**
Replace `LogContext` with a `logging.LoggerAdapter`-based approach that is thread-safe:
```python
# Before (src/utils/logger.py:216-255):
class LogContext:
    def __init__(self, logger: logging.Logger, **kwargs: Any):
        self.logger = logger
        self.extra = kwargs
        self._old_factory: Optional[Any] = None

    def __enter__(self) -> "LogContext":
        old_factory = logging.getLogRecordFactory()
        extra = self.extra
        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            record = old_factory(*args, **kwargs)
            for key, value in extra.items():
                setattr(record, key, value)
            return record
        self._old_factory = old_factory
        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._old_factory:
            logging.setLogRecordFactory(self._old_factory)

# After:
class LogContext:
    """Thread-safe log context using LoggerAdapter."""

    def __init__(self, logger: logging.Logger, **kwargs: Any):
        self.logger = logger
        self.extra = kwargs
        self.adapter = logging.LoggerAdapter(logger, kwargs)

    def __enter__(self) -> logging.LoggerAdapter:
        return self.adapter

    def __exit__(self, *args: Any) -> None:
        pass  # No global state to restore
```
Note: callers must use the returned adapter for logging within the `with` block (e.g., `with LogContext(logger, request_id="x") as log: log.info("msg")`). If no callers currently use the returned value for logging, this is safe since `LogContext` does not appear to be actively used in the current codebase -- but it is exported and documented as a public API.

---

### High (P1)

#### Issue #4: f-String Logging Anti-Pattern Throughout Python Code
- **File:** Multiple files (see list below)
- **Category:** Logging
- **Severity:** P1
- **Problem:** The CLAUDE.md rules mandate structlog with proper structured logging, but the codebase uses stdlib `logging` with f-string interpolation. While stdlib logging is acceptable, f-string logging defeats lazy evaluation -- the string is always formatted even if the log level is disabled. This is a widespread pattern.
- **Impact:** Performance overhead on every log call regardless of level. Also makes structured log aggregation harder since the message is pre-formatted.
- **Surgical Fix:**
Each f-string log call should use `%s`-style or `extra` dict. Key instances:

```python
# File: src/clients/ollama_client.py:152
# Before:
logger.debug(f"Ollama connection error: {e}")
# After:
logger.debug("Ollama connection error: %s", e)

# File: src/clients/ollama_client.py:228
# Before:
logger.debug(f"Sending chat request to Ollama: model={model}")
# After:
logger.debug("Sending chat request to Ollama", extra={"model": model})

# File: src/clients/ollama_client.py:319
# Before:
logger.debug(f"Starting streaming chat request: model={model}")
# After:
logger.debug("Starting streaming chat request", extra={"model": model})

# File: src/clients/mcp_client.py:205
# Before:
logger.debug(f"MCP server connection error: {e}")
# After:
logger.debug("MCP server connection error: %s", e)

# File: src/agent/orchestrator.py:117
# Before:
logger.info(f"Research mode set to: {mode}")
# After:
logger.info("Research mode set to: %s", mode)

# File: src/agent/orchestrator.py:193
# Before:
logger.error(f"LLM error: {e}")
# After:
logger.exception("LLM error")

# File: src/agent/orchestrator.py:274
# Before:
logger.error(f"Failed to get final summary: {e}")
# After:
logger.exception("Failed to get final summary")
```
There are approximately 20+ instances across `orchestrator.py`, `mcp_client.py`, `ollama_client.py`, `app.py`, and `handlers.py`. All follow the same pattern: replace `f"message: {var}"` with `"message: %s", var` or use `extra={}`.

#### Issue #5: HTTP Clients Created Without Context Manager -- Resource Leak
- **File:** `app.py:144-154` (`check_services`) and `app.py:240-248` (sidebar notes fetch)
- **Category:** Resource Leak
- **Severity:** P1
- **Problem:** `check_services()` creates `OllamaClient()` and `MCPClient()` instances and calls async methods on them without using `async with`. The `_get_client()` fallback creates an `httpx.AsyncClient` that is never closed. Similarly, in `render_sidebar()` (line 242) and `render_note_viewer()` (line 349), `MCPClient()` is instantiated, used, and abandoned without closing.
- **Impact:** Each Streamlit page load leaks HTTP connections. Over time this exhausts file descriptors or connection pool limits.
- **Surgical Fix:**
```python
# Before (app.py:142-154):
async def check_services() -> dict:
    """Check if required services are available."""
    ollama = OllamaClient()
    mcp = MCPClient()

    ollama_ok = await ollama.is_available()
    mcp_status = await mcp.health()

    return {
        "ollama": ollama_ok,
        "mcp": mcp_status.available,
        "search_provider": mcp_status.search_provider
    }

# After:
async def check_services() -> dict:
    """Check if required services are available."""
    async with OllamaClient() as ollama, MCPClient() as mcp:
        ollama_ok = await ollama.is_available()
        mcp_status = await mcp.health()

        return {
            "ollama": ollama_ok,
            "mcp": mcp_status.available,
            "search_provider": mcp_status.search_provider
        }
```
Apply the same `async with` pattern at lines 242 and 349 where `MCPClient()` is used.

#### Issue #6: Deprecated `asyncio.get_event_loop()` Usage
- **File:** `app.py:39-44`
- **Category:** Logic / Deprecation
- **Severity:** P1
- **Problem:** `get_event_loop()` calls `asyncio.get_event_loop()` which is deprecated in Python 3.10+ and will emit a `DeprecationWarning` when no current event loop exists. In Python 3.12+, it raises `RuntimeError` in some contexts.
- **Impact:** Will break on newer Python versions. Already emits warnings.
- **Surgical Fix:**
```python
# Before (app.py:39-44):
def get_event_loop():
    """Get or create an event loop."""
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

# After:
def get_event_loop():
    """Get or create an event loop."""
    try:
        loop = asyncio.get_running_loop()
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop
```
Better yet, consider replacing `loop.run_until_complete()` calls with `asyncio.run()` wrapped in a helper, but that requires ensuring no nested event loops (Streamlit runs its own). The minimal fix above avoids the deprecation.

#### Issue #7: `ResearchResult` References Undefined `ApiError` Type
- **File:** `src/api/research.py:34`
- **Category:** Type Safety
- **Severity:** P1
- **Problem:** The `ResearchResult` dataclass has `error: Optional[ApiError] = None` but `ApiError` is not imported in this file. The imports at line 13 import `ApiResponse` from `src.models` but not `ApiError`.
- **Impact:** `NameError` at runtime if any code path instantiates `ResearchResult` with an error. Currently this class appears unused (the API uses `ApiResponse` instead), but it is exported via `__init__.py`.
- **Surgical Fix:**
```python
# Before (src/api/research.py:13):
from src.models import ApiResponse

# After:
from src.models import ApiResponse, ApiError
```

#### Issue #8: `notes.py` API Accesses `result.error` as If It Has `.message` Attribute
- **File:** `src/api/notes.py:87`
- **Category:** Logic
- **Severity:** P1
- **Problem:** Line 87 does `result.error.message` but `ToolResult.error` is typed as `Optional[str]`, not an object with a `.message` attribute. This will raise `AttributeError` when a note save fails.
- **Impact:** Every failed note save crashes instead of returning a graceful error response.
- **Surgical Fix:**
```python
# Before (src/api/notes.py:87):
                message=result.error.message if result.error else "Failed to save note",

# After:
                message=result.error if result.error else "Failed to save note",
```

#### Issue #9: `bare except Exception` in Research API
- **File:** `src/api/research.py:114`
- **Category:** Error Handling
- **Severity:** P1
- **Problem:** The `research()` method catches bare `Exception` and converts it to a generic error response. This swallows `OllamaError`, `MCPError`, and other typed exceptions, losing their specific error codes, suggestions, and details. Per CLAUDE.md: "FORBIDDEN: bare `except Exception:` unless top-level handler."
- **Impact:** All research errors are reported as generic `SERVICE_ERROR` with just `str(e)` -- the user loses the specific error codes, recovery steps, and suggestions that the error system was designed to provide.
- **Surgical Fix:**
```python
# Before (src/api/research.py:114-121):
        except Exception as e:
            return error_response(
                code=ErrorCodes.SERVICE_ERROR,
                message=str(e),
                error_type="research_error",
                suggestion="Check if Ollama and MCP server are running.",
            )

# After:
        except OllamaError as e:
            return error_response(
                code=e.code,
                message=e.message,
                error_type=e.error_type,
                suggestion=e.suggestion or "Check if Ollama is running.",
            )
        except MCPError as e:
            return error_response(
                code=e.code,
                message=e.message,
                error_type=e.error_type,
                suggestion=e.suggestion or "Check if MCP server is running.",
            )
        except Exception as e:
            return error_response(
                code=ErrorCodes.INTERNAL_ERROR,
                message=str(e),
                error_type="internal_error",
                suggestion="An unexpected error occurred. Please try again.",
            )
```
Also add imports: `from src.errors import OllamaError, MCPError` at the top of the file.

#### Issue #10: `ErrorCodes.SERVICE_ERROR` Does Not Exist
- **File:** `src/api/research.py:116`
- **Category:** Logic
- **Severity:** P1
- **Problem:** The `error_response()` call uses `ErrorCodes.SERVICE_ERROR` but this constant does not exist in `src/errors/codes.py`. The available constants are `INTERNAL_ERROR`, `OLLAMA_UNAVAILABLE`, etc. This will raise `AttributeError` at runtime.
- **Impact:** Any research error crashes with `AttributeError: type object 'ErrorCodes' has no attribute 'SERVICE_ERROR'` instead of returning a proper error.
- **Surgical Fix:**
```python
# Before (src/api/research.py:116):
                code=ErrorCodes.SERVICE_ERROR,

# After:
                code=ErrorCodes.INTERNAL_ERROR,
```

#### Issue #11: MCP Server `handleToolCall` Does Not Validate Parameter Types
- **File:** `mcp_server/src/server.ts:82-131`
- **Category:** Input Validation
- **Severity:** P1
- **Problem:** `handleToolCall` casts parameters with `as string`, `as number`, etc. without validation. If a client sends `{"query": 123}` or `{"url": null}`, the code passes invalid types to tool functions without any check. The `as` keyword in TypeScript is a compile-time assertion only -- it does not validate at runtime.
- **Impact:** Undefined behavior in tool functions. Could cause uncaught exceptions, database corruption (e.g., saving `null` as a note title), or security bypasses in URL validation.
- **Surgical Fix:**
Add runtime validation before each tool call:
```typescript
// Before (mcp_server/src/server.ts:89-96):
    case 'web_search':
      return await webSearch(
        params['query'] as string,
        params['limit'] as number | undefined,
        params['provider'] as 'duckduckgo' | 'serper' | undefined
      );

// After:
    case 'web_search': {
      const query = params['query'];
      if (typeof query !== 'string' || query.trim().length === 0) {
        throw new MCPServerError(
          ErrorCodes.INVALID_REQUEST,
          'web_search requires a non-empty string "query" parameter'
        );
      }
      const limit = params['limit'];
      if (limit !== undefined && (typeof limit !== 'number' || isNaN(limit))) {
        throw new MCPServerError(
          ErrorCodes.INVALID_REQUEST,
          'web_search "limit" must be a number'
        );
      }
      return await webSearch(query, limit as number | undefined, params['provider'] as 'duckduckgo' | 'serper' | undefined);
    }
```
Apply the same pattern for `fetch_page` (validate `url` is string), `save_note` (validate `title` and `content` are strings), and `get_note` (validate `id` is string).

---

### Medium (P2)

#### Issue #12: `datetime.utcnow()` Is Deprecated in Python 3.12+
- **File:** `src/utils/logger.py:112` and `src/api/responses.py:25,60`
- **Category:** Deprecation
- **Severity:** P2
- **Problem:** `datetime.utcnow()` is deprecated since Python 3.12. Use `datetime.now(datetime.timezone.utc)` instead.
- **Impact:** DeprecationWarning in Python 3.12+; will be removed in a future version.
- **Surgical Fix:**
```python
# Before (src/utils/logger.py:112):
            "timestamp": datetime.utcnow().isoformat() + "Z",

# After:
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
```
Add `from datetime import datetime, timezone` at the top. Apply to `src/api/responses.py:25` and `src/api/responses.py:60` as well.

#### Issue #13: Conversation History Grows Unbounded
- **File:** `src/agent/orchestrator.py:280-282`
- **Category:** Resource Leak / Performance
- **Severity:** P2
- **Problem:** `self.conversation_history` appends every user/assistant message pair but is never trimmed. Each research query also sends the full history in `messages` (line 177-178). Over a long session, this causes ever-growing LLM context and memory usage.
- **Impact:** Token limit exceeded on LLM; OOM in long-running sessions; increasing latency as history grows.
- **Surgical Fix:**
```python
# Before (src/agent/orchestrator.py:280-282):
        # Update conversation history
        self.conversation_history.append(Message(role="user", content=query))
        self.conversation_history.append(Message(role="assistant", content=final_response))

# After:
        # Update conversation history (keep last 10 exchanges to avoid unbounded growth)
        MAX_HISTORY = 20  # 10 user + 10 assistant messages
        self.conversation_history.append(Message(role="user", content=query))
        self.conversation_history.append(Message(role="assistant", content=final_response))
        if len(self.conversation_history) > MAX_HISTORY:
            self.conversation_history = self.conversation_history[-MAX_HISTORY:]
```

#### Issue #14: FTS5 Query Injection in Notes Service
- **File:** `mcp_server/src/services/notesService.ts:233-238`
- **Category:** Security
- **Severity:** P2
- **Problem:** The FTS5 query is constructed by splitting user input on whitespace and wrapping each term in quotes, but if the user input contains a literal `"` character, it breaks the quoting and can inject FTS5 syntax (e.g., `NEAR`, `NOT`, column filters). While this is SQLite FTS5 (not SQL injection), it can cause query errors or unexpected results.
- **Impact:** Crafted search queries can cause database errors or return unintended results.
- **Surgical Fix:**
```typescript
// Before (mcp_server/src/services/notesService.ts:233-238):
    const ftsQuery = input.query!
      .trim()
      .split(/\s+/)
      .map((term) => `"${term}"*`)
      .join(' OR ');

// After:
    const ftsQuery = input.query!
      .trim()
      .split(/\s+/)
      .map((term) => `"${term.replace(/"/g, '""')}"*`)
      .join(' OR ');
```
Apply the same fix at `mcp_server/src/services/notesService.ts:306-310` in `searchNoteIds`.

#### Issue #15: Tag Filtering via LIKE Pattern Is Fragile
- **File:** `mcp_server/src/services/notesService.ts:256-260`
- **Category:** Logic
- **Severity:** P2
- **Problem:** Tag filtering uses `tags LIKE '%"tagname"%'` which matches substrings. A tag filter for `"ai"` would also match `"fair"`, `"aisle"`, etc. stored in the JSON array.
- **Impact:** False positive results when searching by tags.
- **Surgical Fix:**
Use a JSON function or more precise pattern:
```typescript
// Before (mcp_server/src/services/notesService.ts:256-260):
    for (const tag of input.tags!) {
      sql += ` AND tags LIKE ?`;
      params.push(`%"${tag}"%`);

// After:
    for (const tag of input.tags!) {
      // Match exact tag in JSON array: ,"tag"] or ["tag", or ["tag"]
      sql += ` AND (tags LIKE ? OR tags LIKE ? OR tags LIKE ? OR tags LIKE ?)`;
      const escaped = tag.replace(/"/g, '""');
      params.push(`%,"${escaped}"]%`);    // last element
      params.push(`["${escaped}",%`);      // first element
      params.push(`%,"${escaped}",%`);     // middle element
      params.push(`["${escaped}"]`);       // only element
```
Alternative (cleaner): use SQLite's `json_each()` function if available, or store tags in a separate junction table.

#### Issue #16: `_load_prompt_file` Silently Returns Empty String on Missing File
- **File:** `src/models/research_mode.py:19-25`
- **Category:** Logic
- **Severity:** P2
- **Problem:** In `research_mode.py`, `_load_prompt_file()` returns `""` if the file doesn't exist, silently degrading the research mode prompt. Meanwhile, the same function in `src/agent/prompts.py:26-29` raises `FileNotFoundError`. This inconsistency means a missing prompt file may silently break research quality in one path but crash in another.
- **Impact:** If a prompt file is deleted or renamed, research mode silently loses its prompt context with no error or warning.
- **Surgical Fix:**
```python
# Before (src/models/research_mode.py:19-25):
def _load_prompt_file(filename: str) -> str:
    """Load a prompt file from the prompts directory. Cached for performance."""
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8").strip()
    else:
        # Fallback to empty string if file doesn't exist
        return ""

# After:
def _load_prompt_file(filename: str) -> str:
    """Load a prompt file from the prompts directory. Cached for performance."""
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8").strip()
    else:
        import logging
        logging.getLogger("research_copilot").warning(
            "Prompt file not found: %s, using empty prompt", filepath
        )
        return ""
```

#### Issue #17: Duplicate `_load_prompt_file` Function
- **File:** `src/agent/prompts.py:24-29` and `src/models/research_mode.py:17-25`
- **Category:** DRY Violation
- **Severity:** P2
- **Problem:** `_load_prompt_file()` is defined identically (except for error handling) in both `src/agent/prompts.py` and `src/models/research_mode.py`, with the same `PROMPTS_DIR` constant duplicated as well.
- **Impact:** Changes to prompt loading logic must be made in two places. The inconsistent error handling (one raises, one silently returns `""`) is a direct consequence.
- **Surgical Fix:**
Extract `_load_prompt_file` and `PROMPTS_DIR` into a shared utility (e.g., `src/utils/prompts.py`) and import from both modules.

#### Issue #18: `property` Misuse as Module-Level Alias
- **File:** `src/agent/prompts.py:45-46`
- **Category:** Logic
- **Severity:** P2
- **Problem:** Lines 45-46 define `TOOL_DEFINITIONS` and `SYSTEM_PROMPT_TEMPLATE` as `property()` objects, but `property` only works as a descriptor on classes. At module level, these create unusable `property` objects, not callable aliases.
- **Impact:** Anyone importing `TOOL_DEFINITIONS` or `SYSTEM_PROMPT_TEMPLATE` gets a `property` object instead of the expected string. Calling or accessing it will not work as intended. (Currently unused based on the comment "convenience aliases for backward compatibility".)
- **Surgical Fix:**
```python
# Before (src/agent/prompts.py:44-46):
# Convenience aliases for backward compatibility
TOOL_DEFINITIONS = property(lambda self: get_tool_definitions())
SYSTEM_PROMPT_TEMPLATE = property(lambda self: get_system_prompt_template())

# After (remove entirely or replace with lazy loading):
# Remove these lines -- they are non-functional module-level property objects.
# Callers should use get_tool_definitions() and get_system_prompt_template() directly.
```

#### Issue #19: `logger.error()` Used Instead of `logger.exception()` When Catching Exceptions
- **File:** `src/agent/orchestrator.py:193`, `src/agent/orchestrator.py:274`, `src/agent/orchestrator.py:536`, `src/errors/handlers.py:121-128`, `app.py:135`
- **Category:** Logging
- **Severity:** P2
- **Problem:** Per CLAUDE.md rules: "Use `logger.exception('Failed')` not `logger.error()` when catching exceptions" and "Don't include exception in message: `logger.exception('Failed')` not `logger.exception(f'Failed: {e}')`. Multiple `except` blocks use `logger.error(f"message: {e}")` which both uses the wrong method and includes the exception in the f-string.
- **Impact:** Stack traces are lost in error logs. Debugging production issues requires reproducing the error.
- **Surgical Fix:**
```python
# Before (src/agent/orchestrator.py:193):
            except OllamaError as e:
                logger.error(f"LLM error: {e}")
# After:
            except OllamaError as e:
                logger.exception("LLM error")

# Before (src/agent/orchestrator.py:274):
            except Exception as e:
                logger.error(f"Failed to get final summary: {e}")
# After:
            except Exception as e:
                logger.exception("Failed to get final summary")

# Before (app.py:135):
        logger.error(f"Research failed: {e}")
# After:
        logger.exception("Research failed")
```

#### Issue #20: No Timeout on Follow-up Question LLM Call
- **File:** `src/agent/orchestrator.py:677`
- **Category:** Resilience
- **Severity:** P2
- **Problem:** `_generate_followup_questions()` makes an LLM call with `num_predict: 200` but no explicit timeout. If the LLM hangs, this blocks the entire research response indefinitely. The general `ollama_timeout_seconds` applies, but the follow-up generation should have a much shorter timeout since it is a non-critical enhancement.
- **Impact:** A slow LLM response for follow-ups blocks the user from seeing their research results.
- **Surgical Fix:**
Consider wrapping the follow-up LLM call in `asyncio.wait_for()` with a short timeout:
```python
# Before (src/agent/orchestrator.py:676-681):
            response = await self.ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": followup_prompt}],
                options={"temperature": 0.7, "num_predict": 200}
            )

# After:
            import asyncio
            response = await asyncio.wait_for(
                self.ollama.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": followup_prompt}],
                    options={"temperature": 0.7, "num_predict": 200}
                ),
                timeout=15.0  # 15 seconds max for follow-up generation
            )
```

#### Issue #21: `on_tool_complete` Callback Signature Mismatch
- **File:** `app.py:86-89` vs `src/agent/orchestrator.py:140`
- **Category:** Type Safety
- **Severity:** P2
- **Problem:** The `research()` method signature expects `on_tool_complete: Optional[Callable[[str, Dict, bool], None]]` (3 args: name, result, success). But in `app.py:86-89`, the `research()` call passes `on_progress` for both `on_tool_start` and `on_tool_complete` callbacks. `on_progress` at line 66 is typed as `Callable[[str, Dict], None]` (2 args). However, looking more carefully, `on_tool_start` is defined separately from `on_tool_complete` in `app.py:80-103` and they have the right signatures. This is actually fine. Let me retract -- the `ResearchAPI.research()` in `src/api/research.py:88-89` passes `on_progress` to both, and `on_progress` is typed with 2 params while `on_tool_complete` expects 3.
- **Impact:** If `ResearchAPI.research()` is called with `on_progress`, the callback will receive 3 arguments but expects 2, causing a `TypeError`.
- **Surgical Fix:**
```python
# Before (src/api/research.py:85-89):
            response = await self.orchestrator.research(
                request.query,
                on_tool_start=on_progress,
                on_tool_complete=on_progress
            )

# After:
            response = await self.orchestrator.research(
                request.query,
                on_tool_start=on_progress,
                on_tool_complete=None  # on_progress has wrong signature for on_tool_complete
            )
```

#### Issue #22: MCP Server `console.log` / `console.error` Instead of Structured Logger
- **File:** `mcp_server/src/server.ts:307,408-413`, `mcp_server/src/db/client.ts:45`, and others
- **Category:** Logging
- **Severity:** P2
- **Problem:** The MCP server uses `console.log` and `console.error` throughout instead of a structured logger like `pino` (as mandated by CLAUDE.md for Node.js apps).
- **Impact:** No structured log format, no log levels, no correlation IDs. Makes production debugging difficult.
- **Surgical Fix:** Replace `console.log`/`console.error` with a pino logger instance. This is a broader refactor -- the minimal fix is to create a `src/logger.ts` that wraps pino and replace console calls.

#### Issue #23: `validate_env.py` Suggests `pip install` Instead of `uv add`
- **File:** `scripts/validate_env.py:77`
- **Category:** Best Practices
- **Severity:** P2
- **Problem:** Per CLAUDE.md: "ONLY use `uv`, NEVER `pip`". The validation script's suggestion says `"Run: pip install {' '.join(missing)}"`.
- **Impact:** Users following the suggestion will use pip instead of uv, violating project conventions.
- **Surgical Fix:**
```python
# Before (scripts/validate_env.py:77):
            suggestion=f"Run: pip install {' '.join(missing)}",

# After:
            suggestion=f"Run: uv add {' '.join(missing)}",
```

#### Issue #24: `mcp_server/dist/` Directory Committed (Build Artifacts)
- **File:** `mcp_server/dist/*` (entire directory on disk, not tracked in git)
- **Category:** Repository Hygiene
- **Severity:** P2
- **Problem:** The `mcp_server/dist/` directory exists on disk with compiled JavaScript and source maps. While the root `.gitignore` has `dist/`, the `mcp_server/.gitignore` does NOT have `dist/` listed (it only lists `node_modules/`, `.env`, `data/`, logs, and OS files). If someone runs `git add mcp_server/` they could accidentally commit build artifacts.
- **Impact:** Build artifacts pollute the repository if accidentally committed.
- **Surgical Fix:**
Add `dist/` to `mcp_server/.gitignore`:
```gitignore
# Before (mcp_server/.gitignore, after line 4):
# Build output
dist/

# This line already exists in root .gitignore but should also be in mcp_server/.gitignore for clarity
```
Wait -- checking the root `.gitignore` again, it does have `dist/` at line 21. The root-level ignore covers `mcp_server/dist/`. The `mcp_server/.gitignore` does not have it but it is covered by the parent. This is technically fine but fragile. Adding it to `mcp_server/.gitignore` would be defensive.

#### Issue #25: Notes Models Use Dataclasses Instead of Pydantic
- **File:** `src/models/notes.py`, `src/models/responses.py`
- **Category:** Best Practices / Validation
- **Severity:** P2
- **Problem:** Per CLAUDE.md: "Use `pydantic` (Python) for input validation at boundaries -- never write manual field-by-field validation." The models in `notes.py` and `responses.py` use plain `dataclass` instead of Pydantic `BaseModel`, losing automatic validation, serialization, and type coercion. Validation is then done manually in `validators.py` and `api/notes.py`.
- **Impact:** No automatic type validation or coercion on model instantiation. Manual validation is error-prone and duplicated across layers.
- **Surgical Fix:** Convert `NoteCreate`, `NoteUpdate`, `NoteQuery`, and `ApiResponse` to Pydantic `BaseModel` with field validators. This is a moderate refactor affecting multiple files, so it should be planned as a dedicated task rather than a one-line fix.

---

### Low (P3)

#### Issue #26: Unused Import `asyncio` in `orchestrator.py`
- **File:** `src/agent/orchestrator.py:1`
- **Category:** Code Quality
- **Severity:** P3
- **Problem:** `asyncio` is imported but never used directly in `orchestrator.py`. All async operations use `await` syntax.
- **Impact:** Dead import; minor code clutter.
- **Surgical Fix:**
```python
# Before (src/agent/orchestrator.py:1):
import asyncio

# After:
# Remove the import
```

#### Issue #27: `json` Import Inside Function Body
- **File:** `src/clients/ollama_client.py:343` and `src/agent/prompts.py:181`
- **Category:** Code Quality
- **Severity:** P3
- **Problem:** `import json as json_module` is done inside `chat_stream()` at line 343, and `import json` inside `_format_result_content()` at line 181. Imports should be at module level.
- **Impact:** Slight performance overhead per call; inconsistent style.
- **Surgical Fix:** Move both imports to the top of their respective files.

#### Issue #28: `_summarize_result` Is a Private Function Imported in `app.py`
- **File:** `app.py:24`
- **Category:** Code Quality
- **Severity:** P3
- **Problem:** `app.py` imports `_summarize_result` (underscore-prefixed private function) from `src.ui.state`. This breaks the convention that underscore-prefixed names are internal implementation details.
- **Impact:** Tight coupling to internal implementation. If `_summarize_result` is refactored, `app.py` breaks.
- **Surgical Fix:** Either rename to `summarize_result` (make it public) or provide a public wrapper function in `src/ui/state.py`.

#### Issue #29: Streamlit `@st.cache_resource` on Orchestrator Has No TTL
- **File:** `app.py:49-59`
- **Category:** Logic
- **Severity:** P3
- **Problem:** `get_orchestrator()` is cached indefinitely. If the user changes model/temperature settings, the cached orchestrator's defaults are stale (though they are overridden per-request in `run_research`). More importantly, the `OllamaClient` and `MCPClient` inside are created once and never refreshed, even if the server restarts.
- **Impact:** Stale connections if the MCP server or Ollama restarts during a session.
- **Surgical Fix:** Add `ttl=300` (5 minutes) to the cache decorator:
```python
# Before (app.py:49):
@st.cache_resource
def get_orchestrator() -> Orchestrator:

# After:
@st.cache_resource(ttl=300)
def get_orchestrator() -> Orchestrator:
```

#### Issue #30: Hardcoded `PREFERRED_MODELS` List in UI Code
- **File:** `app.py:171`
- **Category:** Configuration
- **Severity:** P3
- **Problem:** `PREFERRED_MODELS = ["ministral-3:8b", "llama3.1:8b", "mistral:7b", "gemma3:4b"]` is hardcoded in `render_sidebar()`. Per CLAUDE.md: "If changing a value requires a code edit + redeploy, it belongs in config."
- **Impact:** Adding/removing preferred models requires code change + redeploy.
- **Surgical Fix:** Move to `Settings` in `config.py`:
```python
# Add to src/utils/config.py Settings class:
    preferred_models: list[str] = ["ministral-3:8b", "llama3.1:8b", "mistral:7b", "gemma3:4b"]
```
Then in `app.py:171`:
```python
# Before:
    PREFERRED_MODELS = ["ministral-3:8b", "llama3.1:8b", "mistral:7b", "gemma3:4b"]
# After:
    PREFERRED_MODELS = settings.preferred_models
```

#### Issue #31: Missing Type Hints on `validate_tags` Parameter
- **File:** `src/utils/validators.py:178`
- **Category:** Type Safety
- **Severity:** P3
- **Problem:** `validate_tags(tags: list)` uses bare `list` instead of `list[str]`.
- **Impact:** No type safety on tag contents; mypy/pyright cannot verify callers pass strings.
- **Surgical Fix:**
```python
# Before (src/utils/validators.py:178):
def validate_tags(tags: list) -> Tuple[bool, str]:

# After:
def validate_tags(tags: list[str]) -> Tuple[bool, str]:
```

#### Issue #32: `render_note_card` Uses `Optional[callable]` (Lowercase)
- **File:** `src/ui/components.py:274`
- **Category:** Type Safety
- **Severity:** P3
- **Problem:** `on_click: Optional[callable] = None` uses lowercase `callable` which is the built-in function, not the typing type. Should be `Optional[Callable]` (from `typing`).
- **Impact:** Type checkers will not validate the callback signature correctly.
- **Surgical Fix:**
```python
# Before (src/ui/components.py:274):
    on_click: Optional[callable] = None

# After:
    on_click: Optional[Callable[[str], None]] = None
```

---

## Repository Structure Observations

1. **Well-organized module structure.** The `src/` layout with `agent/`, `clients/`, `models/`, `errors/`, `api/`, `ui/`, `utils/` provides clear separation of concerns. The MCP server in `mcp_server/` is properly isolated.

2. **Dual state management in UI.** `src/ui/state.py` maintains both a structured `AppState` dataclass AND a parallel flat `st.session_state` dict. This dual bookkeeping (e.g., `add_message` writes to both) is a maintenance burden and source of potential inconsistency. Consider migrating fully to the `AppState` approach.

3. **Missing test coverage.** The `tests/unit/` directory has only 4 test files (`test_citations.py`, `test_config.py`, `test_errors.py`, `test_parser.py`). There are no tests for: `orchestrator.py`, `mcp_client.py`, `ollama_client.py`, `validators.py`, `api/research.py`, `api/notes.py`, `ui/state.py`, or `ui/components.py`. The `tests/integration/` directory is empty (just `__init__.py`).

4. **Prompt files are well externalized.** The `prompts/` directory with separate files for system prompt, tool definitions, and mode-specific prompts follows the CLAUDE.md rule of keeping prompts out of source code.

5. **`result.txt` is an untracked artifact** sitting in the project root. It should either be added to `.gitignore` or removed.

6. **`mcp_server/data/notes.db*` files exist on disk** (including WAL and SHM files). While correctly gitignored, the `data/` directory itself is not gitignored -- only its contents by pattern. A `.gitkeep` in `data/` would ensure the directory exists after clone.

7. **No `pyproject.toml` dependency management.** The project has both `requirements.txt` and `pyproject.toml`, but uses `pip install -r requirements.txt` in the README instead of `uv sync`. Given the CLAUDE.md mandate for `uv`, the README should be updated and `requirements.txt` could be deprecated in favor of `pyproject.toml`.

8. **MCP server lacks TypeScript strict mode verification.** The `tsconfig.json` should be checked to ensure `"strict": true` is set per CLAUDE.md requirements. The `dist/` build artifacts on disk suggest the build works, but strict mode compliance was not verified.

9. **No health endpoint on the Python side.** Per CLAUDE.md: "Every HTTP service must expose a `/health` endpoint." The MCP server has one, but the Streamlit app does not (though Streamlit is not a traditional HTTP service, the principle could apply to the API layer).

---

## Resolutions

**Fixed by:** Claude Sonnet 4.6 on 2026-05-13
**Branch:** `fix/code-quality-audit-32-issues`
**Validation:** TypeScript build clean · 24/24 TS tests pass · 65/66 Python tests pass (1 pre-existing failure unrelated to this work)

---

### Critical (P0) — 3 issues

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| 1 | API key in `.env` files | **DEFERRED — user action required** | `.env` files are gitignored and cannot be edited by hooks. User must rotate `SEARCH_API_KEY` / `SERPER_API_KEY` manually. |
| 2 | XSS via unsanitized HTML injection | **FIXED** | `src/ui/components.py` — added `import html as _html`; all user-supplied values (`title`, `url`, `snippet`) escaped via `_html.escape()` before HTML injection in `render_source_card()` and `render_content_with_citations()`. |
| 3 | `LogContext` global race condition | **FIXED** | `src/utils/logger.py` — replaced `setLogRecordFactory()` approach with thread-safe `logging.LoggerAdapter`; `__enter__` now returns the adapter; no global state modified. |

### High (P1) — 8 issues

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| 4 | f-string logging anti-pattern | **FIXED** | All f-string log calls converted to `%s`-style in `src/agent/orchestrator.py`, `src/clients/ollama_client.py`, `src/clients/mcp_client.py`, `src/errors/handlers.py`, `app.py`. |
| 5 | HTTP client resource leaks | **FIXED** | `app.py` — all `OllamaClient()` and `MCPClient()` instantiations wrapped in `async with` inside dedicated async helper functions. |
| 6 | Deprecated `asyncio.get_event_loop()` | **FIXED** | `app.py:42` — replaced with `asyncio.get_running_loop()`. |
| 7 | `ApiError` not imported in `research.py` | **FIXED** | `src/api/research.py` — added `ApiError` to the `from src.models import ...` line. |
| 8 | `result.error.message` attribute error | **FIXED** | `src/api/notes.py:87` — changed `result.error.message` to `result.error` (field is `Optional[str]`, not an object). |
| 9 | Bare `except Exception` in research API | **FIXED** | `src/api/research.py` — replaced single catch-all with ordered `except OllamaError`, `except MCPError`, `except Exception` blocks preserving typed error codes. |
| 10 | `ErrorCodes.SERVICE_ERROR` does not exist | **FIXED** | `src/api/research.py:116` — changed to `ErrorCodes.INTERNAL_ERROR` (valid constant). |
| 11 | MCP server missing runtime parameter validation | **FIXED** | `mcp_server/src/server.ts` — all 5 tool handlers now validate parameter types at runtime before dispatching; invalid inputs throw `MCPServerError` with `INVALID_REQUEST`. |

### Medium (P2) — 14 issues

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| 12 | `datetime.utcnow()` deprecated | **FIXED** | `src/utils/logger.py` and `src/api/responses.py` — replaced with `datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")`; added `timezone` to imports. |
| 13 | Conversation history grows unbounded | **FIXED** | `src/agent/orchestrator.py` — added `MAX_HISTORY = 20` trim after each append in both `research()` and `research_stream()`. |
| 14 | FTS5 query injection | **FIXED** | `mcp_server/src/services/notesService.ts` — all search terms escaped with `.replace(/"/g, '""')` before quoting in FTS5 queries; applied to both `listNotes` and `searchNoteIds`. |
| 15 | Tag LIKE pattern false positives | **FIXED** | `mcp_server/src/services/notesService.ts` — replaced `LIKE '%"tag"%'` with four-condition boundary match (`first`, `last`, `middle`, `only` element patterns). |
| 16 | `_load_prompt_file` silently returns `""` | **FIXED** | `src/models/research_mode.py` — now imports shared `load_prompt_file` from `src/utils/prompt_loader`; missing file emits a `WARNING` log rather than silently returning `""`. |
| 17 | Duplicate `_load_prompt_file` function | **FIXED** | Created `src/utils/prompt_loader.py` with a single `@lru_cache`-backed `load_prompt_file()` and shared `PROMPTS_DIR` constant; both `src/agent/prompts.py` and `src/models/research_mode.py` import from it. |
| 18 | `property()` misuse at module level | **FIXED** | `src/agent/prompts.py` — removed non-functional `TOOL_DEFINITIONS` and `SYSTEM_PROMPT_TEMPLATE` module-level `property()` aliases. |
| 19 | `logger.error()` instead of `logger.exception()` | **FIXED** | All `except` blocks in `src/agent/orchestrator.py`, `src/errors/handlers.py`, and `app.py` now use `logger.exception()` without the exception in the message string. |
| 20 | No timeout on follow-up LLM call | **FIXED** | `src/agent/orchestrator.py` — wrapped `_generate_followup_questions()` LLM call in `asyncio.wait_for(..., timeout=15.0)`. |
| 21 | `on_tool_complete` callback signature mismatch | **FIXED** | `src/api/research.py:89` — `on_tool_complete=on_progress` changed to `on_tool_complete=None`; `on_progress` has 2-arg signature, `on_tool_complete` expects 3. |
| 22 | MCP server uses `console.log`/`console.error` | **FIXED** | Created `mcp_server/src/logger.ts` with pino logger; replaced all `console.log`/`console.error` in `server.ts` and `db/client.ts` with structured logger calls. `config/index.ts` fatal-startup errors use `console.error` intentionally (pino not yet initialized). |
| 23 | `validate_env.py` suggests `pip install` | **FIXED** | `scripts/validate_env.py:77` — changed suggestion to `uv add`. |
| 24 | `mcp_server/dist/` not in local `.gitignore` | **NON-ISSUE** | Audited: root `.gitignore` already has `dist/` which covers `mcp_server/dist/`. No change needed. |
| 25 | Notes models use `dataclass` instead of Pydantic | **DEFERRED** | Migrating to Pydantic `BaseModel` is a moderate cross-file refactor. Deferred as a dedicated task; scope exceeds a surgical fix. |

### Low (P3) — 7 issues

| # | Issue | Status | Notes |
|---|-------|--------|-------|
| 26 | Unused `asyncio` import | **NOT REMOVED** | `asyncio` IS used after adding `asyncio.wait_for()` for Issue #20. Import is needed. |
| 27 | `json` import inside function body | **FIXED** | `src/clients/ollama_client.py` — moved `import json as json_module` to module level. `src/agent/prompts.py` — moved `import json` to module level. |
| 28 | `_summarize_result` private name exported | **FIXED** | `src/ui/state.py` — renamed to `summarize_result` (public); updated `app.py` import accordingly. |
| 29 | `@st.cache_resource` with no TTL | **FIXED** | `app.py:49` — changed to `@st.cache_resource(ttl=300)`. |
| 30 | Hardcoded `PREFERRED_MODELS` in UI | **FIXED** | Added `preferred_models: List[str]` field to `Settings` in `src/utils/config.py`; `app.py` now reads `settings.preferred_models`. |
| 31 | `validate_tags` missing type hint | **FIXED** | `src/utils/validators.py:178` — `tags: list` → `tags: list[str]`. |
| 32 | `Optional[callable]` (lowercase) | **FIXED** | `src/ui/components.py:274` — changed to `Optional[Callable[[str], None]]`; added `Callable` to typing imports. |

---

### Pre-existing Test Failure (Not Introduced by This Work)

`tests/unit/test_config.py::test_default_ollama_settings` asserts `ollama_timeout_ms == 60000` but the config has `ollama_timeout_ms = 120000`. Confirmed pre-existing: stashing all changes and running the test produces the same failure. Not caused by this PR.

---

## Additional Fixes

Scan of the codebase after all 32 fixes identified one additional instance matching the Issue #22 pattern (`console.log` in structured-logger context):

### AF-1: `db/client.ts` `closeDatabase()` Still Used `console.log`

- **File:** `mcp_server/src/db/client.ts:75`
- **Pattern:** Issue #22 (console.log instead of structured logger)
- **Fix:** `console.log('Database connection closed')` → `logger.info('Database connection closed')`
- **Status:** **FIXED** — logger was already imported in this file from the Issue #22 work.
