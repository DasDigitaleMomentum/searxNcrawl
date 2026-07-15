---
type: documentation
entity: module
module: "crawler-mcp-server"
version: 1.1
---

# Module: crawler-mcp-server

> Part of [searxNcrawl](../overview.md)

## Overview

`crawler/mcp_server.py` hosts the FastMCP server and exposes three MCP tools (`crawl`, `crawl_site`, `search`) over stdio or HTTP transport.

### Responsibility

- Define MCP tool contracts and implementation wrappers around crawl/search logic.
- Format output for markdown/json responses expected by MCP clients.
- Bootstrap server runtime with transport, bind address, and HTTP Host/Origin trust configuration.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| `crawler-env` | module | Shared `.env` loading with config-dir fallback (`crawler/env.py`). |
| `crawler-package-api` | module | Calls async crawl and site-crawl APIs from tool handlers (`crawler/mcp_server.py:288`, `crawler/mcp_server.py:303`, `crawler/mcp_server.py:383`). |
| `crawler-document-pipeline` | module | Uses `CrawledDocument` type and serialization support (`crawler/mcp_server.py:44`). |
| `fastmcp.FastMCP` | library | MCP framework for declaring tools and running the server; version 3.4.3 or newer supplies the HTTP Host/Origin protection controls used here (`pyproject.toml:11`, `crawler/mcp_server.py:42`, `crawler/mcp_server.py:82`). |
| `httpx` | library | SearXNG HTTP client for search tool (`crawler/mcp_server.py:41`, `crawler/mcp_server.py:463`). |
| `starlette` | library | CORS middleware for HTTP transport (`CORSMiddleware`), transitive dependency of FastMCP. |
| `python-dotenv` | library | Transitively used via shared `crawler.env` config loader (`crawler/env.py`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/mcp_server.py` | file | MCP server, tool handlers, output formatters, and transport CLI. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `mcp` | const | public | `crawler/mcp_server.py:82` | FastMCP server instance and tool registry root. |
| `OutputFormat` | enum | internal | `crawler/mcp_server.py:101` | Enum constraining crawl output formats (`markdown`/`json`). |
| `_parse_csv_allowlist` | function | internal | `crawler/mcp_server.py:120` | Trims comma-separated HTTP allowlist entries, removes empty entries, preserves explicit wildcards, and returns no override for absent/effectively empty input. |
| `_format_timestamp` | function | internal | `crawler/mcp_server.py:129` | Produces UTC timestamp string for output payloads. |
| `_strip_markdown_links` | function | internal | `crawler/mcp_server.py:134` | Optional post-processing for removing link targets in output. |
| `_doc_to_dict` | function | internal | `crawler/mcp_server.py:150` | Converts `CrawledDocument` to JSON-serializable structure. |
| `_format_single_doc_markdown` | function | internal | `crawler/mcp_server.py:166` | Renders one crawl result section in markdown. |
| `_format_multiple_docs_markdown` | function | internal | `crawler/mcp_server.py:182` | Joins multiple doc sections with separators. |
| `_format_output` | function | internal | `crawler/mcp_server.py:194` | Central formatter for markdown/json outputs plus summary/stats. |
| `crawl` | function | public | `crawler/mcp_server.py:233` | MCP tool for crawling one or more URLs. |
| `crawl_site` | function | public | `crawler/mcp_server.py:318` | MCP tool for BFS site crawl from seed URL. |
| `_get_searxng_client` | function | internal | `crawler/mcp_server.py:463` | Builds configured async HTTP client with optional auth. |
| `search` | function | public | `crawler/mcp_server.py:481` | MCP tool for SearXNG metasearch with filters and result limits. |
| `main` | function | public | `crawler/mcp_server.py:633` | Process entrypoint selecting stdio/http transport and conditionally wiring HTTP Host/Origin allowlists and CORS middleware. |

## Data Flow

1. MCP client invokes a tool via FastMCP transport.
2. Tool validates/normalizes arguments (e.g., output format).
3. Tool calls package crawl/search functions or SearXNG HTTP API.
4. Results are transformed to markdown or JSON string payload.
5. FastMCP returns payload to client over stdio/HTTP.

## Configuration

- Environment variables loaded at startup via shared `crawler.env.load_config()` which searches:
  1. `./.env` (current working directory)
  2. `~/.config/searxncrawl/.env` (user config directory)
  3. Auto-creates from `.env.example` if available
- Env vars consumed:
  - `SEARXNG_URL` (`crawler/mcp_server.py:54`)
  - `SEARXNG_USERNAME`, `SEARXNG_PASSWORD` (`crawler/mcp_server.py:55`-`crawler/mcp_server.py:56`)
- Runtime CLI args for server process:
  - `--transport` (`stdio`/`http`) (`crawler/mcp_server.py:664`)
  - `--host` and `--port` select the HTTP bind address and port; they do not trust an externally visible Host header (`crawler/mcp_server.py:670`, `crawler/mcp_server.py:675`).
  - `--allowed-hosts` accepts comma-separated HTTP `Host` header values, trims whitespace, and removes empty entries (`crawler/mcp_server.py:681`, `crawler/mcp_server.py:722`). In HTTP mode, a non-empty list is passed to FastMCP as `allowed_hosts`; for example, `--allowed-hosts "mcp.example.com,mcp.internal.example"` trusts those exact names.
  - FastMCP's `FASTMCP_HTTP_ALLOWED_HOSTS` is the environment-based alternative and expects a JSON list, for example `FASTMCP_HTTP_ALLOWED_HOSTS='["mcp.example.com"]'` (`.env.example:4`-`.env.example:5`). The CLI option is omitted from `mcp.run()` when unset or effectively empty, allowing FastMCP's secure defaults or this upstream setting to apply (`crawler/mcp_server.py:722`-`crawler/mcp_server.py:725`).
  - `--cors-origins` accepts the same normalized comma-separated form (`crawler/mcp_server.py:690`, `crawler/mcp_server.py:727`). A non-empty list is sent both to FastMCP as `allowed_origins` for request-time Origin trust and to Starlette `CORSMiddleware` as `allow_origins` for CORS response headers (`crawler/mcp_server.py:727`-`crawler/mcp_server.py:742`). These are separate controls; without the option, neither override nor CORS middleware is added.
  - `"*"` is preserved for either CLI allowlist but is never supplied by default. It explicitly trusts every Host or Origin and weakens HTTP request protection, so exact values should be preferred.
- Host, Origin, bind, port, and middleware arguments are HTTP-only. The stdio branch ignores them even if their CLI flags are supplied (`crawler/mcp_server.py:713`-`crawler/mcp_server.py:749`).

## Dedup Parameters and Metadata

- `crawl` and `crawl_site` expose `dedup_mode` with values `exact|off` and default `exact`.
- `crawl` and `crawl_site` expose `storage_state` (optional path to Playwright storage state JSON) for authenticated crawling.
- `exact` is the backward-compatible default and keeps dedup active for intra-document exact duplicates.
- `off` disables dedup for that request only.
- JSON output forwards builder metadata unchanged, including dedup stats and guardrail indicators when present (for example `dedup_guardrail_triggered`).

## Auth Surface (Phase 2 MVP)

- MCP tool auth input is MVP-only: `storage_state`.
- Tool handlers forward auth into package APIs via `auth={"storage_state": ...}` and rely on shared resolver behavior for validation/errors.
- Session capture and profile ergonomics are deferred to later phases.
- No-drift invariant: MCP auth surface changes do not alter crawl config defaults.

## Inventory Notes

- **Coverage**: full
- **Notes**: Includes all tool handlers and server bootstrapping symbols in `crawler/mcp_server.py`.
