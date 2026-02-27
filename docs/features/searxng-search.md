---
type: documentation
entity: feature
feature: "searxng-search"
version: 1.0
---

# Feature: SearXNG Search

> Part of [searxNcrawl](../overview.md)

## Summary

SearXNG search provides privacy-respecting web search by querying a SearXNG metasearch engine instance. Results are returned as structured JSON or formatted Markdown, with support for language filtering, time ranges, category/engine selection, safe search levels, and pagination.

## How It Works

### User Flow

1. User provides a search query via CLI (`search "query"`), MCP tool (`search(query="...")`), or Python API (`search_async("query")` / `search("query")`).
2. Optionally specifies language, time range, categories, engines, safe search level, page number, max results.
3. Receives search results as Markdown (default for CLI) or JSON.

### Technical Flow

1. The search function constructs query parameters:
   - `q` (query), `format: json`, `language`, `safesearch`, `pageno`
   - Optional: `time_range`, `categories` (comma-joined), `engines` (comma-joined)
2. An `httpx.AsyncClient` is created targeting `SEARXNG_URL` with optional basic auth.
3. A GET request is sent to `/search` with the constructed params.
4. The JSON response is parsed; results are truncated to `max_results` (1-50).
5. Output is formatted as JSON string (MCP) or Markdown (CLI default).

### Markdown Output Format (CLI)

```markdown
# Search: python tutorials
_Found 10 results_

## 1. Python Tutorial - W3Schools
https://www.w3schools.com/python/

Well organized tutorials...

---
```

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-core](../modules/crawler-core.md) | `search_async` (`search.py:149`), `search` (`search.py:246`) | Shared search implementation (async + sync) |
| [crawler-core](../modules/crawler-core.md) | `SearchResult` (`search.py:48`), `SearchResultItem` (`search.py:34`) | Structured result types |
| [crawler-core](../modules/crawler-core.md) | `SearchError` (`search.py:91`) | Search exception type |
| [crawler-core](../modules/crawler-core.md) | `_get_searxng_client` (`search.py:109`) | Create httpx client with auth |
| [crawler-core](../modules/crawler-core.md) | `search` (MCP tool at `mcp_server.py:498`) | MCP tool (delegates to `search.py`) |
| [crawler-core](../modules/crawler-core.md) | `search_async`, `search`, `SearchResult` (`__init__.py:52`) | Python API re-exports |
| [crawler-core](../modules/crawler-core.md) | `_run_search_async` (`cli.py:730`) | CLI search execution |
| [crawler-core](../modules/crawler-core.md) | `_format_search_markdown` (`cli.py:88`) | Format results as Markdown |
| [crawler-core](../modules/crawler-core.md) | `search_main` (`cli.py:775`) | CLI entry point |

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG instance URL |
| `SEARXNG_USERNAME` | (none) | Basic auth username |
| `SEARXNG_PASSWORD` | (none) | Basic auth password |

| Parameter | CLI Flag | MCP Param | Default | Purpose |
|-----------|----------|-----------|---------|---------|
| Query | positional | `query` | required | Search query string |
| Language | `--language` | `language` | `en` | Language code (e.g. en, de, fr) |
| Time range | `--time-range` | `time_range` | (none) | day, week, month, year |
| Categories | `--categories` | `categories` | (all) | general, images, news, etc. |
| Engines | `--engines` | `engines` | (all) | Specific search engines |
| Safe search | `--safesearch` | `safesearch` | `1` | 0=off, 1=moderate, 2=strict |
| Max results | `--max-results` | `max_results` | `10` | 1-50 |
| Page number | `--pageno` | `pageno` | `1` | Page number (minimum 1) |
| Output format | `--json` | (always JSON) | markdown (CLI) | JSON or Markdown |
| Output file | `-o` | N/A | stdout | File to write results to |

## Edge Cases & Limitations

- **SearXNG instance required**: The search feature requires a running SearXNG instance with JSON format enabled. Without it, all searches will fail.
- **Auth errors**: HTTP 401 from SearXNG produces a specific error message prompting credential check.
- **Network errors**: Connection failures are caught and returned as error JSON rather than raising.
- **Rate limiting**: Public SearXNG instances may rate-limit; self-hosting is recommended.
- **CLI pagination**: Use `--pageno` to navigate result pages (default: page 1).

## Related Features

- [MCP Server](mcp-server.md) -- exposes search as an MCP tool
- [CLI Interface](cli.md) -- `search` command
