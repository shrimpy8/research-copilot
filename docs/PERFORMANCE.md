# Performance Analysis

> Performance characteristics and optimization notes for Research Copilot.

---

## Performance Profile

Tested on: MacBook (Apple Silicon), Ollama with llama3.2:3b

### Latency Breakdown

| Operation | Typical Latency | Notes |
|-----------|-----------------|-------|
| Ollama health check | 50-100ms | HTTP request to Ollama |
| MCP health check | 10-20ms | HTTP request to localhost |
| web_search | 150-300ms | DuckDuckGo API call |
| fetch_page | 50-200ms | Depends on target site |
| list_notes | 1-5ms | SQLite query |
| get_note | 1-3ms | SQLite lookup |
| save_note | 5-20ms | SQLite insert |
| LLM inference | 1.5-4s | Model dependent |

### End-to-End Query

**Quick Summary Mode:**
- Total: 3-6 seconds
- Tool calls: 1-2
- LLM inference: ~80% of time

**Deep Dive Mode:**
- Total: 8-15 seconds
- Tool calls: 3-5
- LLM inference: ~70% of time

---

## Bottleneck Analysis

### 1. LLM Inference (Primary Bottleneck)

The largest contributor to latency is local LLM inference via Ollama.

**Factors:**
- Model size (3b vs 8b vs 70b)
- Context length
- Hardware (GPU vs CPU)
- Quantization level

**Mitigations:**
- Use smaller models for faster responses (llama3.2:3b)
- Use GPU acceleration if available
- Keep prompts concise

### 2. Web Search

DuckDuckGo search can occasionally be slow or return no results.

**Factors:**
- DuckDuckGo API rate limits
- Query complexity
- Network latency

**Mitigations:**
- Use Serper API for better performance ($50/mo for 50K searches)
- Implement result caching (not currently implemented)

### 3. Page Fetching

Fetching external pages depends on target site performance.

**Factors:**
- Target site response time
- Content size
- SSL handshake time

**Mitigations:**
- Set appropriate timeouts (15s default)
- Limit max content size (50KB default)
- Consider implementing caching for frequently accessed URLs

---

## Optimization Strategies

### Implemented

1. **Connection Pooling**: httpx AsyncClient reuses connections
2. **Async Operations**: All I/O operations are async
3. **Streaming Responses**: LLM responses stream progressively
4. **Content Truncation**: Page content limited to prevent memory issues

### Potential Future Optimizations

1. **Search Result Caching**
   - Cache search results for 15 minutes
   - Estimated improvement: Skip 150-300ms for repeated queries

2. **Page Content Caching**
   - Cache fetched pages for 1 hour
   - Estimated improvement: Skip 50-200ms for repeated URLs

3. **Parallel Page Fetches**
   - Fetch multiple pages concurrently in Deep Dive mode
   - Estimated improvement: 30-50% reduction in fetch phase

4. **Model Preloading**
   - Keep model in memory between requests
   - Currently handled by Ollama (model stays loaded)

---

## Benchmarks

### Quick Summary Query

```
Query: "What is Python programming?"
Research mode: quick

Results (5 runs):
  Run 1: 2,694ms (1 tool call)
  Run 2: 3,102ms (2 tool calls)
  Run 3: 2,891ms (1 tool call)
  Run 4: 3,456ms (2 tool calls)
  Run 5: 2,782ms (1 tool call)

Average: 2,985ms
Min: 2,694ms
Max: 3,456ms
```

### Deep Dive Query

```
Query: "Compare MCP to function calling"
Research mode: deep

Results (3 runs):
  Run 1: 8,234ms (4 tool calls)
  Run 2: 11,456ms (5 tool calls)
  Run 3: 9,012ms (4 tool calls)

Average: 9,567ms
Min: 8,234ms
Max: 11,456ms
```

### Tool-Only Operations

```
web_search (3 results): 122-196ms
fetch_page (docs.python.org): 70-150ms
list_notes (5 results): 1-3ms
save_note: 5-10ms
get_note: 1-2ms
```

---

## Hardware Recommendations

### Minimum (CPU-only)
- 8GB RAM
- 4+ CPU cores
- Expect 4-8 second query times

### Recommended (GPU)
- 16GB RAM
- NVIDIA GPU with 8GB+ VRAM
- Expect 2-4 second query times

### Optimal
- 32GB RAM
- NVIDIA GPU with 12GB+ VRAM
- Larger models (8b, 70b) for better quality
- Expect 1-3 second query times with high-quality responses

---

## Monitoring

### Key Metrics to Track

1. **Query Latency**: Total time from request to response
2. **Tool Latency**: Time per tool execution
3. **LLM Latency**: Time spent on inference
4. **Error Rate**: Failed tool calls / total calls
5. **Cache Hit Rate**: (if caching implemented)

### Logging

Enable debug logging to see detailed timing:

```env
LOG_LEVEL=debug
```

Tool execution times are logged:

```
[INFO] MCP tool completed: web_search (196ms)
[INFO] Research complete (2694ms)
```

---

## Performance Checklist

Before demo/production:

- [ ] Ollama model is preloaded (`ollama run model_name` once)
- [ ] MCP server is running and warmed up
- [ ] No other heavy processes competing for GPU
- [ ] Network connection is stable (for search/fetch)
- [ ] Using appropriate model size for hardware

---

*Last updated: January 11, 2026*
