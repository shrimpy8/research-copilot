# CLAUDE.md
## Research Copilot — Project Principles

> **One-liner:** A local AI research assistant that searches, reads, summarizes, and remembers—all through transparent tool calls and zero cloud dependencies.
>
> **Scope:** project-specific principles, invariants, and gotchas only. General engineering, security, language, and testing standards are handled globally and are not restated here.

---

## 🎯 Project Purpose

**We're building this to demonstrate:**
1. AI agent orchestration patterns (tool-calling loops)
2. MCP protocol implementation (standardized tool access)
3. Local-first architecture (privacy-preserving AI)
4. Clean information retrieval and synthesis

**This is a stepping stone to:** Engineering Assistant (more complex UI, same MCP patterns)

---

## 🧭 Core Principles

### 1. Sources Over Assertions

Every research answer must cite its sources.

- ✅ Include clickable source URLs with every research response
- ✅ Show which pages were actually read
- ✅ Distinguish between "I searched for" and "I found"
- ✅ Include inline numbered citations that map to the Sources list
- ❌ Never present web content without attribution
- ❌ Never hallucinate sources or URLs

**Test yourself:** "Can the user verify every claim by clicking a link?"

---

### 2. Transparency Is Trust

Users must see what the AI is doing.

- ✅ Show tool trace for every interaction
- ✅ Display "Searching web...", "Reading page..." status
- ✅ Make all tool arguments visible (on click/expand)
- ✅ Show a “Research Trail” timeline (tools + sources)
- ❌ Never silently fetch or search
- ❌ Never hide failed tool calls

**Test yourself:** "Does the user know exactly what happened behind the scenes?"

---

### 3. Local-First, Always

Everything runs on the user's machine.

- ✅ Ollama for all LLM inference
- ✅ SQLite for notes storage
- ✅ Only web calls are search/fetch (transparent); two providers supported in v1
- ❌ No cloud LLM services
- ❌ No analytics or telemetry
- ❌ No "phone home" features

**Test yourself:** "Does this work if the user turns off WiFi after loading the app?"

---

### 4. Research That Persists

Knowledge should accumulate, not disappear.

- ✅ Easy "Save as Note" for any research response
- ✅ Tags and full-text search for notes
- ✅ Notes list supports pagination for large libraries (offset-based)
- ✅ Notes survive app restarts
- ✅ Source URLs preserved with notes
- ✅ Notes persist indefinitely (retention policy out of scope)
- ❌ Session-only memory for important findings

**Test yourself:** "Can the user find this information next week?"

---

### 5. Errors Guide Recovery

When things fail, help the user fix it.

- ✅ Every error has: title, message, suggestion
- ✅ Recovery steps for service issues
- ✅ Graceful degradation (show partial results)
- ❌ Generic "Something went wrong"
- ❌ Technical jargon in user-facing errors

**Test yourself:** "If I saw this error, would I know what to do?"

---

### 6. Simple UI, Complete Function

Streamlit should feel finished, not half-baked.

- ✅ Clean layout with clear hierarchy
- ✅ Consistent styling (colors, spacing, fonts)
- ✅ Loading states for all async operations
- ✅ Mobile-responsive (at least tablet)
- ✅ Low-scope demo polish features (see below)
- ✅ Model selection uses installed Ollama models with preferred defaults
- ❌ Placeholder text in production
- ❌ Broken layouts at any viewport

**Test yourself:** "Would I be comfortable demoing this to a hiring manager?"

---

## 🚦 Decision Framework

When making implementation choices:

```
1. Does it break source attribution?
   → If yes, don't do it.

2. Does it hide what the AI is doing?
   → If yes, find a transparent way.

3. Does it require cloud services?
   → If yes, make it optional or remove it.

4. Is there a simpler approach?
   → If yes, do that first.

5. Does it follow established patterns?
   → If no, document why you're diverging.
```

---

## 🛡️ Code Quality Guardrails (Lessons from Audits)

These rules close specific gaps found during the code quality audits (see `docs/ISSUE_FIXES.md`).

### XSS — Streamlit HTML rendering
Every call with `unsafe_allow_html=True` must escape **all** interpolated values with `_html.escape()` (already imported as `import html as _html` in `components.py`). When fixing one XSS instance, grep for `unsafe_allow_html` across the entire file — the same pattern appears in multiple rendering functions (`render_tags`, `render_error_message`, `render_source_comparison`, `render_source_card`).

### Information disclosure — error display
`st.error(f"...{variable}")` and `st.warning(f"...{variable}")` expose internals whether inside or outside an `except` block. **Never interpolate exception objects, `result.error` fields, or any non-static value into Streamlit display calls.** Log the detail with `logger.warning/exception()` and show a generic message to the user.

### Logging style
`setup_logger()` returns a standard Python `logging.Logger`. Use `%s` lazy-evaluation style (`logger.info("msg: %s", value)`) not f-strings (`logger.info(f"msg: {value}")`). Required for `LogRedactor` compatibility and deferred string formatting.

### Symbol deletion checklist
When removing a function from `components.py` (or any module), immediately grep for it in `src/ui/__init__.py` (import line + `__all__`) and any other file that imports from that module. A deleted definition with a live export causes `ImportError` at startup.

### Known pre-existing test failure
`tests/unit/test_config.py::TestSettings::test_default_ollama_settings` asserts `ollama_timeout_ms == 60000` but the config default is `120000`. This is a stale test — do not change the config default to match it. Fix the test assertion if you touch `test_config.py`.

---

## 📐 Technical Guardrails

### Response Types
```python
# Success response
ApiResponse(
    success=True,
    data={...},
    error=None,
    meta=ResponseMeta(request_id=..., timestamp=..., duration_ms=...)
)

# Error response
ApiResponse(
    success=False,
    data=None,
    error=ApiError(code=..., message=..., type=..., suggestion=...),
    meta=ResponseMeta(...)
)
```

### Error Codes
- Use `snake_case`: `search_failed`, `fetch_timeout`
- Be specific: `ollama_unavailable` not `service_error`
- Match the tool: `note_not_found`, `search_no_results`

### Logging & Tracing
- Generate a `request_id` per user message and propagate through tools/logs.
- Redact API keys and query params in logs; truncate fetched content to 200 chars.

### File/Function Naming
| Type | Convention | Example |
|------|------------|---------|
| Files | snake_case | `ollama_client.py` |
| Classes | PascalCase | `OllamaClient` |
| Functions | snake_case | `fetch_page` |
| Constants | SCREAMING_SNAKE | `MAX_PAGE_SIZE` |

### Security
- Enforce SSRF protections and block DNS rebinding.
- Block redirects to private IP ranges.

### Content Extraction
- Support `extract_mode` for fetches; `markdown` should at least include a title + readable body.

### Demo Polish Pack (Low-Scope)
- Research Trail panel
- One-click Note (prefill title + tags)
- Confidence meter (based on source count + fetch success)
- Source quality badges (docs/blog/news)
- Compare sources (collapsed bullets per source)
- Follow-up question chips (3 suggestions)
- Inline numbered citations

---

## 🎨 Design Tokens (Quick Reference)

> **Implementation:** All design values are centralized in `src/ui/design_tokens.py`.
> Import and use these classes/functions rather than hardcoding values.

```python
from src.ui.design_tokens import Colors, Spacing, Typography, BorderRadius
from src.ui.design_tokens import tag_style, card_style, badge_style

# Example usage
Colors.ACCENT           # #0066CC
Colors.TAG_BACKGROUND   # #E7F1FF
Spacing.NORMAL_MD       # 16px
tag_style()             # Returns CSS for tag pills
```

**Color Palette:**
| Token | Value | Usage |
|-------|-------|-------|
| `BACKGROUND_PRIMARY` | #FFFFFF | Main background |
| `BACKGROUND_SECONDARY` | #F8F9FA | Cards, sections |
| `TEXT_PRIMARY` | #1A1A1A | Body text |
| `TEXT_SECONDARY` | #6C757D | Captions, metadata |
| `ACCENT` | #0066CC | Links, buttons |
| `ERROR` | #DC3545 | Error states |
| `SUCCESS` | #198754 | Success states |
| `TAG_BACKGROUND` | #E7F1FF | Tags, pills |

**DRY Helpers:**
- `render_tags(tags, max_tags)` - Consistent tag rendering
- `format_source_link(number, title, url)` - Citation link formatting

---

## ✅ Definition of Done

A feature is complete when:

- [ ] It works as specified
- [ ] Sources are cited for research answers
- [ ] Tool trace shows what happened
- [ ] Error states display friendly messages
- [ ] Loading states are implemented
- [ ] It's tested (unit + integration)
- [ ] It follows naming conventions
- [ ] Console has no errors or warnings
- [ ] A PM could demo it without explanation

---

## 🚫 Explicit Non-Goals (v1)

To maintain focus, we are **not** building:

- PDF/document parsing
- Image analysis
- Note editing (save-only)
- Note export
- More than two search providers (v1 supports DuckDuckGo + Serper)
- Conversation persistence
- User authentication
- Collaborative features

These are valid for v1.1+ but would delay MVP.

---

## 🔧 MCP Tools Reference

| Tool | Purpose | Key Params |
|------|---------|------------|
| `web_search` | Search the web | query, limit (1-5), provider (duckduckgo|serper) |
| `fetch_page` | Read a URL | url, max_chars |
| `save_note` | Store research | title, content, tags |
| `list_notes` | Find notes | query, tags, limit |
| `get_note` | Retrieve note | id |

---

## 💬 How to Talk About This Project

### Elevator Pitch
"It's a local AI assistant for research—it searches the web, reads pages, 
and saves what you learn. The key difference: you see every tool call, 
every source, and everything stays on your machine."

### For AI/ML PM Interviews
- Emphasize: Agent architecture, tool orchestration, user trust
- Key phrase: "Transparency is essential for AI systems users can trust"

### For Dev Tools PM Interviews
- Emphasize: Local-first, privacy, developer workflow
- Key phrase: "Knowledge workers need tools that respect their data"

---

## 📁 Key Files to Know

| Purpose | Location |
|---------|----------|
| **Implementation progress** | `PROGRESS.md` |
| **Project README** | `README.md` |
| PRD specification | `docs/research-copilot-prd-v1.5.md` |
| Streamlit entry | `app.py` |
| Agent orchestrator | `src/agent/orchestrator.py` |
| System prompts | `src/agent/prompts.py` |
| Ollama client | `src/clients/ollama_client.py` |
| MCP client | `src/clients/mcp_client.py` |
| Error definitions | `src/errors/` |
| **UI components** | `src/ui/components.py` |
| **Design tokens** | `src/ui/design_tokens.py` |
| **Session state** | `src/ui/state.py` |
| **Research modes** | `src/models/research_mode.py` |
| Response models | `src/models/responses.py` |
| Note models | `src/models/notes.py` |
| MCP server tools | `mcp_server/src/tools/` |
| Config loader | `src/utils/config.py` |
| URL validator | `src/utils/validators.py` |
| Demo flow | `docs/demo-flow.md` |

---

## 🔄 Session Workflow

**Starting a new session:**
1. Read `PROGRESS.md` — check "Overall Status" and "Session Log" for context
2. Review any blockers from previous session
3. Pick up from the next incomplete task

**During a session:**
- Mark tasks complete in `PROGRESS.md` as you finish them
- Add notes for anything non-obvious
- Log blockers immediately

**Ending a session:**
- Update "Session Log" in `PROGRESS.md` with work done + next steps
- Ensure "Overall Status" table reflects current state

---

## 🔄 Daily Check-in Questions

1. What did I ship yesterday?
2. What's blocking me?
3. Are sources cited in research answers?
4. Is the tool trace visible?
5. Is there something I should simplify?

---

## 📚 Reference Links

- [MCP Specification](https://modelcontextprotocol.io)
- [Ollama API Docs](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Streamlit Docs](https://docs.streamlit.io)
- [SQLite FTS5](https://www.sqlite.org/fts5.html)

---

## 🔗 Relationship to Engineering Assistant

This project teaches:
- MCP tool implementation patterns
- Agent orchestration loops
- Error handling philosophy
- Tool trace UI patterns

These patterns transfer directly to the Engineering Assistant:
- Same MCP client structure → different tools
- Same orchestration loop → different system prompt
- Same error framework → same codes
- Tool trace → identical pattern in React

**Complete this first, then the next project goes faster.**

---

## Security Patterns Learned (2026-06-03)

These rules close specific gaps found during the high-priority security review (see `docs/HIGH_PRIORITY_REVIEW_2026-06-03.md`).

### `unsafe_allow_html` requires prior escaping
Before any `st.markdown(..., unsafe_allow_html=True)` call, run `html.escape()` on **all** non-static content first — this includes assistant responses, citation content, source titles, and URLs. Generate citation anchor HTML separately from escaped content; never mix raw model text with HTML generation. Correct pattern: escape model text → build citation anchors from trusted source metadata → concatenate → render.

### Tool results are untrusted data, not trusted text
Fetched page content, search snippets, and note content must be escaped (`_neutralize_tool_content()`) and wrapped in `<untrusted_tool_data source="...">` before being added to the model conversation. The system prompt must explicitly instruct the model to treat those blocks as evidence only, never as instructions. Using the same tag vocabulary as real tool calls — without escaping — lets a malicious page inject fake tool calls into the model context.

### MCP server must require auth for non-loopback binds
If `HOST` is not `localhost`, `127.0.0.1`, or `::1`, startup must fail unless `MCP_AUTH_TOKEN` is configured and a `Authorization: Bearer <token>` check is added to the `/mcp` route. Never silently serve an unauthenticated endpoint on a public or LAN-accessible interface. Localhost-only development remains tokenless.

### HTTP response body caps require streaming, not `arrayBuffer()`
`response.arrayBuffer()` allocates the entire response body before any size check can run. For byte-capped fetches, read with a `ReadableStreamDefaultReader` loop, accumulate chunk sizes, and call `reader.cancel()` the moment the cap is exceeded. Keep a `Content-Length` pre-check as an early-exit optimisation, but never rely on it alone — chunked or streaming responses may omit it. A `null` body fallback to `arrayBuffer()` is acceptable only when the runtime exposes no stream.

### MCP service limits must mirror Python-side limits
When there are two write paths to the same store (Python API + MCP server), both must enforce identical content length caps, URL count limits, and field size limits. A stricter Python validator does not protect the MCP write path. Define shared limit constants once (e.g., `MAX_CONTENT_LENGTH`, `MAX_SOURCE_URLS`, `MAX_SOURCE_URL_LENGTH`, `MAX_TAG_LENGTH`) and apply them in `validateNoteInput()` on the MCP side.

### Follow-up LLM calls must be budget-gated
Any "nice to have" LLM call (e.g., follow-up question generation) that runs after the main response must be guarded by a budget check and an opt-out flag (`enable_followup_questions`, default `True`). Skip the call when the main response already consumed `MAX_TOOL_ITERATIONS` LLM calls or when the caller disables it. Track the call in the same metrics object as the main response so total cost and latency per user action are visible.
