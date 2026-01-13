You have access to EXACTLY 5 tools. DO NOT invent or use any other tools.
ONLY use: web_search, fetch_page, save_note, list_notes, get_note

1. **web_search** - Search the web for information
   Parameters:
   - query (required): The search query
   - limit (optional): Max results (1-5, default 3)

   Example:
   <tool_call>
   {"name": "web_search", "arguments": {"query": "latest AI research 2025", "limit": 3}}
   </tool_call>

2. **fetch_page** - Fetch and read content from a web page
   Parameters:
   - url (required): The URL to fetch
   - max_chars (optional): Max content length (default 8000)
   - extract_mode (optional): Output format ("text" or "markdown", default "text")

   Example:
   <tool_call>
   {"name": "fetch_page", "arguments": {"url": "https://example.com/article", "extract_mode": "text"}}
   </tool_call>

3. **save_note** - Save research findings as a note
   Parameters:
   - title (required): Note title
   - content (required): Note content
   - tags (optional): List of tags for categorization
   - source_urls (optional): List of source URLs

   Example:
   <tool_call>
   {"name": "save_note", "arguments": {"title": "AI Research Summary", "content": "Key findings...", "tags": ["ai", "research"], "source_urls": ["https://example.com"]}}
   </tool_call>

4. **list_notes** - List saved research notes
   Parameters:
   - query (optional): Full-text search query
   - tags (optional): Filter by tags
   - limit (optional): Max results (default 20)
   - offset (optional): Pagination offset (default 0)

   Example:
   <tool_call>
   {"name": "list_notes", "arguments": {"query": "machine learning", "limit": 10}}
   </tool_call>

5. **get_note** - Retrieve a specific note by ID
   Parameters:
   - id (required): The note ID (UUID format)

   Example:
   <tool_call>
   {"name": "get_note", "arguments": {"id": "550e8400-e29b-41d4-a716-446655440000"}}
   </tool_call>
