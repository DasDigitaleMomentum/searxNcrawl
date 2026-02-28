---
type: documentation
entity: feature
feature: "mcp-tools-and-transports"
version: 1.0
---

# Feature: mcp-tools-and-transports

> Part of [searxNcrawl](../overview.md)

## Summary

This feature exposes crawling and search capabilities as MCP tools (`crawl`, `crawl_site`, `search`) and supports both stdio and HTTP transports for local editor integrations and remote service use.

## How It Works

### User Flow

1. User starts MCP server via Python module or `crawl-mcp` script.
2. User chooses transport: stdio (default) or HTTP (`--transport http`).
3. MCP client discovers tools and invokes them with arguments.
4. Server runs crawl/search actions and returns markdown/json payloads.

### Technical Flow

1. `mcp = FastMCP(...)` creates server and tool registry.
2. `@mcp.tool` decorators register `crawl`, `crawl_site`, and `search` functions.
3. Tool handlers call package APIs/SearXNG and route output through `_format_output`.
4. `main()` parses transport args and invokes `mcp.run(...)` with stdio or HTTP configuration.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-mcp-server](../modules/crawler-mcp-server.md) | `mcp`, `crawl`, `crawl_site`, `search`, `main` | Tool definitions and server runtime bootstrap. |
| [crawler-package-api](../modules/crawler-package-api.md) | `crawl_page_async`, `crawl_pages_async`, `crawl_site_async` | Crawl execution logic called from MCP tools. |
| [crawler-document-pipeline](../modules/crawler-document-pipeline.md) | `CrawledDocument` | Shared output model serialized in MCP responses. |

## Configuration

- Runtime args: `--transport`, `--host`, `--port` (`crawler/mcp_server.py:485`, `crawler/mcp_server.py:491`, `crawler/mcp_server.py:496`).
- Environment: `SEARXNG_URL`, optional basic-auth credentials for search tool (`crawler/mcp_server.py:54`-`crawler/mcp_server.py:56`).
- Docker runtime uses `docker-compose.yml` with HTTP transport and configurable `MCP_PORT` (`docker-compose.yml:23`-`docker-compose.yml:32`).

## Edge Cases & Limitations

- Tool responses are JSON strings for search and markdown/json strings for crawl tools; clients must parse according to expected tool output contract.
- Invalid `output_format` values fallback to markdown in crawl tools (`crawler/mcp_server.py:224`-`crawler/mcp_server.py:228`, `crawler/mcp_server.py:298`-`crawler/mcp_server.py:301`).
- Search behavior depends on external SearXNG availability.

## Related Features

- [crawling-workflows](crawling-workflows.md)
- [site-crawling-bfs](site-crawling-bfs.md)
- [search-with-searxng](search-with-searxng.md)
- [cli-commands-and-output](cli-commands-and-output.md)
