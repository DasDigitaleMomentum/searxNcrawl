---
type: documentation
entity: module
module: "crawler-mcp-server"
version: 1.3
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
| `crawler-package-api` | module | Calls async crawl and site-crawl APIs from tool handlers (`crawler/mcp_server.py`). |
| `crawler-document-pipeline` | module | Uses `CrawledDocument` type and serialization support (`crawler/mcp_server.py`). |
| `fastmcp.FastMCP` | library | MCP framework for declaring tools and running the server; version 3.4.3 or newer supplies the HTTP Host/Origin protection controls used here (`pyproject.toml`, `crawler/mcp_server.py`). |
| `crawler.search_orchestrator` | module | Multi-provider search (SearXNG, You.com), result serializer and configured-provider list for the startup log (`crawler/mcp_server.py`). |
| `starlette` | library | CORS middleware for HTTP transport (`CORSMiddleware`), transitive dependency of FastMCP. |
| `python-dotenv` | library | Transitively used via shared `crawler.env` config loader (`crawler/env.py`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/mcp_server.py` | file | MCP server, tool handlers, output formatters, and transport CLI. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `mcp` | const | public | `crawler/mcp_server.py` | FastMCP server instance and tool registry root. |
| `OutputFormat` | enum | internal | `crawler/mcp_server.py` | Enum constraining crawl output formats (`markdown`/`json`). |
| `_resolve_log_level` | function | internal | `crawler/mcp_server.py` | Validates `LOG_LEVEL`; falls back to INFO for missing/invalid values. |
| `_configure_stdio_encoding` | function | internal | `crawler/mcp_server.py` | Best-effort UTF-8 stream setup before starting STDIO. |
| `_parse_csv_allowlist` | function | internal | `crawler/mcp_server.py` | Trims comma-separated HTTP allowlist entries, removes empty entries, preserves explicit wildcards, and returns no override for absent/effectively empty input. |
| `_format_timestamp` | function | internal | `crawler/mcp_server.py` | Produces UTC timestamp string for output payloads. |
| `_strip_markdown_links` | function | internal | `crawler/mcp_server.py` | Optional post-processing for removing link targets in output. |
| `_doc_to_dict` | function | internal | `crawler/mcp_server.py` | Converts `CrawledDocument` to JSON-serializable structure. |
| `_format_single_doc_markdown` | function | internal | `crawler/mcp_server.py` | Renders a URL heading and nests page headings one level lower, capped at h6; closed fenced code is preserved. |
| `_format_multiple_docs_markdown` | function | internal | `crawler/mcp_server.py` | Joins multiple doc sections with separators. |
| `_format_output` | function | internal | `crawler/mcp_server.py` | Central formatter for markdown/json outputs plus summary/stats. |
| `crawl` | function | public | `crawler/mcp_server.py` | MCP tool for crawling one or more URLs. |
| `crawl_site` | function | public | `crawler/mcp_server.py` | MCP tool for DFS site crawl from seed URL. |
| `search` | function | public | `crawler/mcp_server.py` | Provider search with optional `include_content`; adds page Markdown or `crawl_error`, or returns `{"error", "query"}` for search failure. |
| `main` | function | public | `crawler/mcp_server.py` | Process entrypoint selecting stdio/http transport and conditionally wiring HTTP Host/Origin allowlists and CORS middleware. |

## Data Flow

1. MCP client invokes a tool via FastMCP transport.
2. Tool validates/normalizes arguments (e.g., output format).
3. Tool calls package crawl functions or `crawler.search_orchestrator.search`.
   - Search resolves SearXNG extra headers and secret files per call; headers never reach You.com.
   - `include_content=true` crawls result pages through `crawl_result_pages` before serialization.
4. Results are transformed to markdown or JSON string payload.
5. FastMCP returns payload to client over stdio/HTTP.

## Configuration

- Environment variables loaded at startup via shared `crawler.env.load_config()` which searches:
  1. `./.env` (current working directory)
  2. `~/.config/searxncrawl/.env` (user config directory)
  3. Auto-creates from `.env.example` if available
- Existing process variables win over file values; only the first existing `.env` is selected.
- Env vars consumed:
  - `LOG_LEVEL` sets server logging (default `INFO`); invalid values fall back to INFO.
  - Search providers, read at call time by `crawler.search_orchestrator`: `SEARXNG_URL` (no default), `SEARXNG_USERNAME`/`SEARXNG_PASSWORD` (both or neither), `SEARXNG_EXTRA_HEADERS`, `YDC_API_KEY`; plus `SEARCH_RESULT_FIELDS`. The startup log lists configured providers without secrets.
  - Extra-header names must be HTTP tokens and values ASCII strings without control characters. UTF-8 secret files require absolute or `~/` references. Invalid configuration disables only SearXNG with a value/path-free warning. [Header rules](../usage/installation.md#searxng-behind-cloudflare-access).
- Runtime CLI args for server process:
  - Header protection is opt-in: set `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true` before startup. Locked FastMCP 4.1.3 defaults to `false`; allowlists alone do not enable it. FastMCP initializes before native `.env` loading, so export the setting or inject it into the container environment.
  - `--transport` (`stdio`/`http`, default `stdio`); HTTP defaults to `127.0.0.1:8000` (`crawler/mcp_server.py`).
  - `--host` and `--port` select the HTTP bind address and port; they do not trust an externally visible Host header (`crawler/mcp_server.py`).
  - `--allowed-hosts` accepts comma-separated HTTP `Host` header values, trims whitespace, and removes empty entries (`crawler/mcp_server.py`). In HTTP mode, a non-empty list is passed to FastMCP as `allowed_hosts`; for example, `--allowed-hosts "mcp.example.com,mcp.internal.example"` trusts those exact names.
  - FastMCP's `FASTMCP_HTTP_ALLOWED_HOSTS` is the environment-based alternative and expects a JSON list, for example `FASTMCP_HTTP_ALLOWED_HOSTS='["mcp.example.com"]'` (`.env.example`). Unset or effectively empty CLI input leaves the upstream setting unchanged; neither form enables protection by itself.
  - `--cors-origins` accepts the same normalized comma-separated form (`crawler/mcp_server.py`). A non-empty list reaches the enabled FastMCP Origin guard and Starlette CORS response headers. CORS middleware is added independently of guard activation; without the option, neither override nor CORS middleware is added.
  - `"*"` is preserved for either CLI allowlist but is never supplied by default. It explicitly trusts every Host or Origin and weakens HTTP request protection, so exact values should be preferred.
- Host/Origin guards do not authenticate callers. Shared HTTP deployments require an authenticated TLS proxy; [deployment guide](../usage/mcp-server.md).
- Host, Origin, bind, port, and middleware arguments are HTTP-only. The stdio branch ignores them even if their CLI flags are supplied (`crawler/mcp_server.py`).

## Dedup Parameters and Metadata

- `crawl.timeout=15` is per URL; `crawl_site.timeout=120` covers the deep-crawl operation. Both require values of at least 1 s.

- `crawl` and `crawl_site` expose `dedup_mode` with values `exact|off` and default `exact`.
- `crawl` and `crawl_site` expose `storage_state` (optional path to Playwright storage state JSON) for authenticated crawling.
- `exact` is the backward-compatible default and keeps dedup active for intra-document exact duplicates.
- `off` disables dedup for that request only.
- JSON output forwards builder metadata unchanged, including dedup stats and guardrail indicators when present (for example `dedup_guardrail_triggered`).
- MCP crawl Markdown nests page headings one level below URL headings, capped at h6; JSON `markdown` values remain unchanged.

## Auth Surface

- MCP tool auth input supports `storage_state` only.
- Tool handlers forward auth into package APIs via `auth={"storage_state": ...}` and rely on shared resolver behavior for validation/errors.
- Session capture is a separate CLI/Python workflow; MCP exposes no capture tool. [Capture guide](../usage/session-capture.md).
- `searxncrawl` and `crawl-mcp` both enter `main`; a leading `setup` argument dispatches to coding-agent registration before starting a server.
- Optional Arcade deployment wraps a pinned published package in a separate project. [Adapter runtime/security](../../deploy/arcade/README.md).

## Inventory Notes

- **Coverage**: best-effort
- **Notes**: Includes all tool handlers and server bootstrapping symbols in `crawler/mcp_server.py`.
