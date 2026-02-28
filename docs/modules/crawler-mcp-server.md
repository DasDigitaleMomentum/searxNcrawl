---
type: documentation
entity: module
module: "crawler-mcp-server"
version: 1.0
---

# Module: crawler-mcp-server

> Part of [searxNcrawl](../overview.md)

## Overview

`crawler/mcp_server.py` hosts the FastMCP server and exposes three MCP tools (`crawl`, `crawl_site`, `search`) over stdio or HTTP transport.

### Responsibility

- Define MCP tool contracts and implementation wrappers around crawl/search logic.
- Format output for markdown/json responses expected by MCP clients.
- Bootstrap server runtime with transport/host/port CLI arguments.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| `crawler-package-api` | module | Calls async crawl and site-crawl APIs from tool handlers (`crawler/mcp_server.py:221`, `crawler/mcp_server.py:295`). |
| `crawler-document-pipeline` | module | Uses `CrawledDocument` type and serialization support (`crawler/mcp_server.py:40`). |
| `fastmcp.FastMCP` | library | MCP framework for declaring tools and running server (`crawler/mcp_server.py:38`, `crawler/mcp_server.py:59`). |
| `httpx` | library | SearXNG HTTP client for search tool (`crawler/mcp_server.py:36`, `crawler/mcp_server.py:332`). |
| `python-dotenv` | library | Loads environment before server/tool config resolution (`crawler/mcp_server.py:37`, `crawler/mcp_server.py:51`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/mcp_server.py` | file | MCP server, tool handlers, output formatters, and transport CLI. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `mcp` | const | public | `crawler/mcp_server.py:59` | FastMCP server instance and tool registry root. |
| `OutputFormat` | enum | internal | `crawler/mcp_server.py:78` | Enum constraining crawl output formats (`markdown`/`json`). |
| `_format_timestamp` | function | internal | `crawler/mcp_server.py:85` | Produces UTC timestamp string for output payloads. |
| `_strip_markdown_links` | function | internal | `crawler/mcp_server.py:90` | Optional post-processing for removing link targets in output. |
| `_doc_to_dict` | function | internal | `crawler/mcp_server.py:105` | Converts `CrawledDocument` to JSON-serializable structure. |
| `_format_single_doc_markdown` | function | internal | `crawler/mcp_server.py:121` | Renders one crawl result section in markdown. |
| `_format_multiple_docs_markdown` | function | internal | `crawler/mcp_server.py:137` | Joins multiple doc sections with separators. |
| `_format_output` | function | internal | `crawler/mcp_server.py:149` | Central formatter for markdown/json outputs plus summary/stats. |
| `crawl` | function | public | `crawler/mcp_server.py:188` | MCP tool for crawling one or more URLs. |
| `crawl_site` | function | public | `crawler/mcp_server.py:255` | MCP tool for BFS site crawl from seed URL. |
| `_get_searxng_client` | function | internal | `crawler/mcp_server.py:332` | Builds configured async HTTP client with optional auth. |
| `search` | function | public | `crawler/mcp_server.py:350` | MCP tool for SearXNG metasearch with filters and result limits. |
| `main` | function | public | `crawler/mcp_server.py:459` | Process entrypoint selecting stdio/http transport and running server. |

## Data Flow

1. MCP client invokes a tool via FastMCP transport.
2. Tool validates/normalizes arguments (e.g., output format).
3. Tool calls package crawl/search functions or SearXNG HTTP API.
4. Results are transformed to markdown or JSON string payload.
5. FastMCP returns payload to client over stdio/HTTP.

## Configuration

- Environment variables loaded at startup:
  - `SEARXNG_URL` (`crawler/mcp_server.py:54`)
  - `SEARXNG_USERNAME`, `SEARXNG_PASSWORD` (`crawler/mcp_server.py:55`-`crawler/mcp_server.py:56`)
- Runtime CLI args for server process:
  - `--transport` (`stdio`/`http`) (`crawler/mcp_server.py:485`)
  - `--host` and `--port` for HTTP mode (`crawler/mcp_server.py:491`, `crawler/mcp_server.py:496`)

## Dedup Parameters and Metadata

- `crawl` and `crawl_site` expose `dedup_mode` with values `exact|off` and default `exact`.
- `exact` is the backward-compatible default and keeps dedup active for intra-document exact duplicates.
- `off` disables dedup for that request only.
- JSON output forwards builder metadata unchanged, including dedup stats and guardrail indicators when present (for example `dedup_guardrail_triggered`).

## Inventory Notes

- **Coverage**: full
- **Notes**: Includes all tool handlers and server bootstrapping symbols in `crawler/mcp_server.py`.
