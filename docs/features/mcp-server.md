---
type: documentation
entity: feature
feature: "mcp-server"
version: 1.0
---

# Feature: MCP Server

> Part of [searxNcrawl](../overview.md)

## Summary

The MCP (Model Context Protocol) server exposes searxNcrawl's crawling and search capabilities as tools that LLM agents can invoke. It supports STDIO transport (for MCP harnesses like Zed, opencode, Claude Code, Codex, VS Code, OpenClaw) and HTTP transport (for remote access and Docker deployments). Built on the FastMCP framework.

## How It Works

### User Flow

1. User configures their MCP harness to connect to the searxNcrawl server.
2. The LLM agent discovers available tools: `crawl`, `crawl_site`, `search`, `list_auth_profiles`.
3. The agent invokes tools with parameters; the server executes and returns results.

### Technical Flow

1. `mcp_server.py:main()` parses CLI args (`--transport`, `--host`, `--port`).
2. A `FastMCP` instance is created with tool descriptions and instructions.
3. Four tools are registered via `@mcp.tool` decorators:
   - `crawl`: Single/multi-page crawling
   - `crawl_site`: BFS site crawling
   - `search`: SearXNG web search
   - `list_auth_profiles`: List available auth profiles
4. `mcp.run(transport=...)` starts the server:
   - **STDIO**: Reads JSON-RPC from stdin, writes to stdout.
   - **HTTP**: Starts an HTTP server on `host:port/mcp`.
5. Each tool invocation:
   - Validates parameters (output format, auth config).
   - Delegates to the core crawl/search functions.
   - Formats output as string (Markdown or JSON).
   - Returns the string to the MCP harness.

### Tool Registration

```python
mcp = FastMCP(name="Web Crawler & Search", instructions="...")

@mcp.tool
async def crawl(urls, output_format, concurrency, remove_links,
                cookies, headers, storage_state, auth_profile,
                delay, wait_until): ...

@mcp.tool
async def crawl_site(url, max_depth, max_pages, include_subdomains,
                     output_format, remove_links, cookies, headers,
                     storage_state, auth_profile, delay, wait_until): ...

@mcp.tool
async def search(query, language, time_range, categories, engines,
                 safesearch, pageno, max_results): ...

@mcp.tool
async def list_auth_profiles(): ...
```

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-core](../modules/crawler-core.md) | `mcp` (`mcp_server.py:63`) | FastMCP server instance |
| [crawler-core](../modules/crawler-core.md) | `crawl` (MCP tool, `mcp_server.py:231`) | Crawl one or more URLs |
| [crawler-core](../modules/crawler-core.md) | `crawl_site` (MCP tool, `mcp_server.py:355`) | BFS site crawl |
| [crawler-core](../modules/crawler-core.md) | `search` (MCP tool, `mcp_server.py:498`) | SearXNG search (delegates to shared `search.py` module) |
| [crawler-core](../modules/crawler-core.md) | `list_auth_profiles` (MCP tool, `mcp_server.py:465`) | List auth profiles |
| [crawler-core](../modules/crawler-core.md) | `main` (`mcp_server.py:574`) | CLI entry point for `crawl-mcp` |
| [crawler-core](../modules/crawler-core.md) | `_format_output` (`mcp_server.py:159`) | Format results as markdown or JSON |
| [crawler-core](../modules/crawler-core.md) | `_build_auth_config` (`mcp_server.py:192`) | Build AuthConfig from MCP params |
| [crawler-core](../modules/crawler-core.md) | `OutputFormat` (`mcp_server.py:87`) | Enum: markdown, json |

## Configuration

### Transport

| Transport | Flag | Default | Description |
|-----------|------|---------|-------------|
| STDIO | `--transport stdio` | yes | Standard input/output JSON-RPC |
| HTTP | `--transport http` | no | HTTP server with `/mcp` endpoint |

### HTTP Settings

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Bind port |

### Environment Variables

All environment variables from [authenticated crawling](authenticated-crawling.md) and [SearXNG search](searxng-search.md) apply. The MCP server loads `.env` via `python-dotenv` at import time.

### Entry Points

| Entry Point | Command | Description |
|-------------|---------|-------------|
| `pyproject.toml` script | `crawl-mcp` | Runs `crawler.mcp_server:main` |
| Module | `python -m crawler.mcp_server` | Direct module execution |

### MCP Harness Configuration Example

```json
{
  "mcpServers": {
    "crawler": {
      "command": "python",
      "args": ["-m", "crawler.mcp_server"],
      "cwd": "/path/to/searxNcrawl",
      "env": {
        "SEARXNG_URL": "http://your-searxng:8888"
      }
    }
  }
}
```

### Docker Deployment

The Docker Compose configuration runs the MCP server in HTTP mode on port `${MCP_PORT:-9555}`:

```bash
docker compose up --build
# Server available at http://localhost:9555/mcp
```

## Edge Cases & Limitations

- **STDIO is default**: When no transport is specified, STDIO is used. This is the expected mode for MCP harnesses.
- **No streaming**: Tool results are returned as a single string. Large site crawls may produce substantial output.
- **Auth fallback chain**: MCP tool auth params > environment variables > no auth. Explicit params always win.
- **Error handling**: Crawl failures produce documents with `status="failed"` and `error_message` rather than raising errors to the MCP harness.
- **SearXNG errors**: Search errors (HTTP errors, network failures) are returned as JSON error objects rather than protocol-level errors.

## Related Features

- [Web Crawling](web-crawling.md) -- core crawl logic exposed as MCP tools
- [SearXNG Search](searxng-search.md) -- search logic exposed as MCP tool
- [Authenticated Crawling](authenticated-crawling.md) -- auth params on MCP tools
- [CLI Interface](cli.md) -- alternative interface to the same functionality
