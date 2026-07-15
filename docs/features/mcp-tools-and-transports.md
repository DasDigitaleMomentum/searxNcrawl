---
type: documentation
entity: feature
feature: "mcp-tools-and-transports"
version: 1.1
---

# Feature: mcp-tools-and-transports

> Part of [searxNcrawl](../overview.md)

## Summary

This feature exposes crawling and search capabilities as MCP tools (`crawl`, `crawl_site`, `search`) and supports both stdio and HTTP transports for local editor integrations and remote service use.

## How It Works

### User Flow

1. User starts MCP server via Python module or `crawl-mcp` script.
2. User chooses transport: stdio (default) or HTTP (`--transport http`).
3. For remote HTTP access, the operator explicitly trusts externally visible Host headers and, for browser clients, trusted Origins.
4. MCP client discovers tools and invokes them with arguments.
5. Server runs crawl/search actions and returns markdown/json payloads.

### Technical Flow

1. `mcp = FastMCP(...)` creates server and tool registry.
2. `@mcp.tool` decorators register `crawl`, `crawl_site`, and `search` functions.
3. Tool handlers call package APIs/SearXNG and route output through `_format_output`.
4. `main()` parses transport arguments and normalizes comma-separated Host/Origin allowlists with `_parse_csv_allowlist` (`crawler/mcp_server.py:120`, `crawler/mcp_server.py:633`).
5. In HTTP mode, explicitly configured Hosts reach FastMCP's request guard; configured CORS origins reach both FastMCP's Origin guard and Starlette CORS response middleware (`crawler/mcp_server.py:713`-`crawler/mcp_server.py:745`). The isolated stdio branch receives none of these HTTP-only arguments (`crawler/mcp_server.py:746`-`crawler/mcp_server.py:749`).

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-mcp-server](../modules/crawler-mcp-server.md) | `mcp`, `crawl`, `crawl_site`, `search`, `_parse_csv_allowlist`, `main` | Tool definitions, allowlist normalization, and transport-specific server runtime bootstrap. |
| [crawler-package-api](../modules/crawler-package-api.md) | `crawl_page_async`, `crawl_pages_async`, `crawl_site_async` | Crawl execution logic called from MCP tools. |
| [crawler-document-pipeline](../modules/crawler-document-pipeline.md) | `CrawledDocument` | Shared output model serialized in MCP responses. |

## Configuration

- Runtime args: `--transport`, `--host`, and `--port` select the transport and HTTP listener (`crawler/mcp_server.py:664`-`crawler/mcp_server.py:680`). Binding to `0.0.0.0` does not itself trust a public Host header.
- `--allowed-hosts` is an HTTP-only, comma-separated allowlist for request `Host` headers (`crawler/mcp_server.py:681`-`crawler/mcp_server.py:689`). Whitespace is trimmed and empty entries are discarded; prefer exact externally visible names, for example `--allowed-hosts "mcp.example.com"`.
- As an alternative to the CLI option, FastMCP reads `FASTMCP_HTTP_ALLOWED_HOSTS` in JSON-list format, for example `FASTMCP_HTTP_ALLOWED_HOSTS='["mcp.example.com"]'` (`.env.example:4`-`.env.example:5`). No searxNcrawl-specific Host environment variable is added.
- `--cors-origins` is an HTTP-only, comma-separated Origin allowlist (`crawler/mcp_server.py:690`-`crawler/mcp_server.py:699`). The normalized list configures both FastMCP's request-time `allowed_origins` guard and Starlette `CORSMiddleware` response headers (`crawler/mcp_server.py:727`-`crawler/mcp_server.py:742`); configuring only response headers would not bypass the earlier guard.
- Omitting the Host or Origin option passes no corresponding override, preserving FastMCP's secure defaults and allowing its environment configuration to resolve (`crawler/mcp_server.py:722`-`crawler/mcp_server.py:734`).
- Environment: `SEARXNG_URL`, optional basic-auth credentials for search tool (`crawler/mcp_server.py:54`-`crawler/mcp_server.py:56`).
- Docker runtime uses `docker-compose.yml` with HTTP transport and configurable `MCP_PORT` (`docker-compose.yml:23`-`docker-compose.yml:32`).

## Edge Cases & Limitations

- Tool responses are JSON strings for search and markdown/json strings for crawl tools; clients must parse according to expected tool output contract.
- Invalid `output_format` values fallback to markdown in crawl tools (`crawler/mcp_server.py:224`-`crawler/mcp_server.py:228`, `crawler/mcp_server.py:298`-`crawler/mcp_server.py:301`).
- Search behavior depends on external SearXNG availability.
- FastMCP rejects untrusted public Hosts with HTTP 421 and untrusted Origins with HTTP 403 before MCP routing/CORS processing (`tests/test_cors.py:130`-`tests/test_cors.py:146`). Configure the externally observed Host/Origin values rather than assuming the bind address is sufficient.
- `*` for Hosts or Origins is preserved only when explicitly supplied and admits arbitrary values (`tests/test_cors.py:35`-`tests/test_cors.py:68`, `tests/test_cors.py:148`-`tests/test_cors.py:168`). It weakens Host/Origin protection; exact allowlists are the safer deployment choice, and Docker has no wildcard default.

## Related Features

- [crawling-workflows](crawling-workflows.md)
- [site-crawling-bfs](site-crawling-bfs.md)
- [search-with-searxng](search-with-searxng.md)
- [cli-commands-and-output](cli-commands-and-output.md)
