---
type: documentation
entity: feature
feature: "search-with-searxng"
version: 1.0
---

# Feature: search-with-searxng

> Part of [searxNcrawl](../overview.md)

## Summary

This feature provides configurable metasearch via SearXNG, available through both CLI and MCP, with support for language/time/category/engine filters and result limiting.

## How It Works

### User Flow

1. User provides a query and optional filters.
2. User invokes `search` CLI command or MCP `search` tool.
3. System sends request to configured SearXNG `/search` endpoint with JSON format.
4. Results are truncated to max result limit and returned as markdown (CLI default) or JSON.

### Technical Flow

1. Interface resolves SearXNG settings from environment variables.
2. Request params are assembled (`q`, `language`, `safesearch`, optional filters).
3. `httpx.AsyncClient` performs GET `/search`.
4. Response JSON is parsed, results are bounded to 1..50.
5. Output is rendered/returned; HTTP/auth/request errors are converted to friendly failures.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-cli](../modules/crawler-cli.md) | `_run_search_async`, `_parse_search_args`, `_format_search_markdown`, `search_main` | CLI search UX and output formatting. |
| [crawler-mcp-server](../modules/crawler-mcp-server.md) | `search`, `_get_searxng_client` | MCP search tool and configured client creation. |

## Configuration

- Environment variables:
  - `SEARXNG_URL` (`crawler/cli.py:494`, `crawler/mcp_server.py:54`)
  - `SEARXNG_USERNAME`, `SEARXNG_PASSWORD` (`crawler/cli.py:495`-`crawler/cli.py:496`, `crawler/mcp_server.py:55`-`crawler/mcp_server.py:56`)
- CLI filters: `--language`, `--time-range`, `--categories`, `--engines`, `--safesearch`, `--max-results` (`crawler/cli.py:430`, `crawler/cli.py:436`, `crawler/cli.py:443`, `crawler/cli.py:450`, `crawler/cli.py:457`, `crawler/cli.py:464`).
- MCP search parameters parallel these options (`crawler/mcp_server.py:351`-`crawler/mcp_server.py:358`).

## Edge Cases & Limitations

- Missing/unreachable SearXNG returns request errors; no local search fallback exists.
- Authentication failures are explicitly mapped for 401 responses (`crawler/cli.py:561`, `crawler/mcp_server.py:432`).
- Result counts are constrained to `[1, 50]` regardless of requested value (`crawler/cli.py:537`, `crawler/mcp_server.py:422`).

## Related Features

- [mcp-tools-and-transports](mcp-tools-and-transports.md)
- [cli-commands-and-output](cli-commands-and-output.md)
