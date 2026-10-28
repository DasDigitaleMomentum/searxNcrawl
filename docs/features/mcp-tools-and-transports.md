---
type: documentation
entity: feature
feature: "mcp-tools-and-transports"
version: 1.2
---

# Feature: mcp-tools-and-transports

> Part of [searxNcrawl](../overview.md)

## Summary

This feature exposes crawling and search capabilities as MCP tools (`crawl`, `crawl_site`, `search`) and supports both stdio and HTTP transports for local editor integrations and remote service use.

## How It Works

### User Flow

1. User starts MCP server via Python module, `searxncrawl` or `crawl-mcp` script.
2. User chooses transport: stdio (default) or HTTP (`--transport http`).
3. For remote HTTP access, the operator enables Host/Origin protection and configures the externally visible Host headers and browser Origins.
4. MCP client discovers tools and invokes them with arguments.
5. Server runs crawl/search actions and returns markdown/json payloads.

### Technical Flow

1. `mcp = FastMCP(...)` creates server and tool registry.
2. `@mcp.tool` decorators register `crawl`, `crawl_site`, and `search` functions.
3. Crawl tool handlers call package APIs and route output through `_format_output`; `search` calls `crawler.search_orchestrator` and returns its serialized envelope.
4. `main()` parses transport arguments and normalizes comma-separated Host/Origin allowlists with `_parse_csv_allowlist` (`crawler/mcp_server.py`).
5. In HTTP mode, allowlists reach FastMCP; request-time checks require `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true`. Configured CORS origins also reach Starlette CORS response middleware, independently of guard activation (`crawler/mcp_server.py`). The stdio branch receives none of these HTTP-only arguments.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-mcp-server](../modules/crawler-mcp-server.md) | `mcp`, `crawl`, `crawl_site`, `search`, `_parse_csv_allowlist`, `main` | Tool definitions, allowlist normalization, and transport-specific server runtime bootstrap. |
| [crawler-package-api](../modules/crawler-package-api.md) | `crawl_page_async`, `crawl_pages_async`, `crawl_site_async` | Crawl execution logic called from MCP tools. |
| [crawler-document-pipeline](../modules/crawler-document-pipeline.md) | `CrawledDocument` | Shared output model serialized in MCP responses. |

## Configuration

- Set `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true` in the process environment before startup to enable header checks. Locked FastMCP 4.1.3 defaults this setting to `false`; native `.env` loading happens after FastMCP initializes. Docker Compose injects `.env` into the container environment.
- Runtime args: `--transport` defaults to `stdio`; `--host=127.0.0.1` and `--port=8000` select the HTTP listener (`crawler/mcp_server.py`). Binding to `0.0.0.0` does not itself trust a public Host header.
- `--allowed-hosts` is an HTTP-only, comma-separated allowlist for request `Host` headers (`crawler/mcp_server.py`). Whitespace is trimmed and empty entries are discarded; prefer exact externally visible names, for example `--allowed-hosts "mcp.example.com"`.
- As an alternative to the CLI option, FastMCP reads `FASTMCP_HTTP_ALLOWED_HOSTS` in JSON-list format, for example `FASTMCP_HTTP_ALLOWED_HOSTS='["mcp.example.com"]'` (`.env.example`). No searxNcrawl-specific Host environment variable is added.
- `--cors-origins` is an HTTP-only, comma-separated Origin allowlist (`crawler/mcp_server.py`). It configures the enabled request guard and Starlette CORS response headers; with the guard disabled, CORS middleware alone does not reject arbitrary Origins at request time.
- Omitting the Host or Origin option passes no corresponding override and leaves FastMCP's setting unchanged; allowlist configuration does not activate protection.
- Environment for the search tool: `SEARXNG_URL` (no default) with optional basic-auth credentials (both or neither) and/or `YDC_API_KEY`; see [search-with-searxng](search-with-searxng.md).
- Docker runtime uses `docker-compose.yml` with HTTP transport and configurable `MCP_PORT` (default 9555) (`docker-compose.yml`).

## Edge Cases & Limitations

- Native STDIO/HTTP is the standard runtime. The [optional Arcade adapter](../../deploy/arcade/README.md) is a separate pinned-package project requiring a compatible host; this repository does not provision permanent Arcade hosting.
- Host/Origin guards do not authenticate callers. Shared HTTP deployments require an authenticated TLS proxy; [HTTP guide](../usage/mcp-server.md).
- Tool responses are JSON strings for search and markdown/json strings for crawl tools; clients must parse according to expected tool output contract.
- Invalid `output_format` values fallback to markdown in crawl tools (`crawler/mcp_server.py`).
- Search depends on the configured external providers (SearXNG and/or You.com); with none configured, `search` returns an error.
- With header protection enabled, FastMCP rejects untrusted public Hosts with HTTP 421 and untrusted Origins with HTTP 403 before MCP routing/CORS processing (`tests/test_cors.py` enables protection explicitly).
- `*` for Hosts or Origins is preserved only when explicitly supplied and admits arbitrary values (`tests/test_cors.py`). It weakens Host/Origin protection; exact allowlists are the safer deployment choice, and Docker has no wildcard default.

## Related Features

- [crawling-workflows](crawling-workflows.md)
- [site-crawling-bfs](site-crawling-bfs.md)
- [search-with-searxng](search-with-searxng.md)
- [cli-commands-and-output](cli-commands-and-output.md)
