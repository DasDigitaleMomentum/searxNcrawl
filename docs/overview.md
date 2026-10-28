---
type: documentation
entity: project-overview
version: 1.2
---

# searxNcrawl

## Purpose

- Python package, CLI and MCP server for web crawling and parallel SearXNG/You.com search.
- Results return as Markdown or JSON; optional search-page crawling includes page content in the same call.
- Protected SearXNG search supports Basic Auth and validated extra headers with secret-file references.

## Architecture

- Native CLI and MCP runtime share the `crawler/` package:

- **Public API/orchestration**: `crawler/__init__.py`
- **Crawler configuration**: `crawler/config.py`
- **Data model + transformation**: `crawler/document.py`, `crawler/references.py`, `crawler/builder.py`
- **Site DFS crawling**: `crawler/site.py`
- **Search orchestration**: `crawler/search_orchestrator.py` (provider selection, SearXNG + You.com calls, merge, serializer)
- **Interfaces**: `crawler/cli.py` and `crawler/mcp_server.py`
- **Runtime support**: `crawler/env.py`, `crawler/browser_setup.py`, `crawler/page_hooks.py`
- **Auth and capture**: `crawler/auth.py`, `crawler/session_capture.py`
- **Agent registration**: `crawler/setup.py` (`searxncrawl setup`)
- **Optional Arcade adapter**: `deploy/arcade/`, a separate project pinned to the published package; requires a compatible host and authenticated worker connection. [Runtime and security details](../deploy/arcade/README.md).

### System Diagram

```text
User / Agent
  |                          |
  v                          v
CLI (crawl/capture/search)  MCP client (stdio/http)
  |                          |
  +------------+-------------+
               v
      Interface Layer
  (crawler/cli.py, crawler/mcp_server.py)
               |
               v
      Crawl/Search Orchestration
 (crawler.__init__, crawler.site,
  crawler.search_orchestrator)
          |               |
          v               v
       Crawl4AI       SearXNG API + You.com API
          |
          v
  builder + references + document
          |
          v
     CrawledDocument / JSON / Markdown
```

### Tech Stack

- Python >=3.10 (`pyproject.toml`)
- crawl4ai (`pyproject.toml`)
- tldextract (`pyproject.toml`)
- playwright (`pyproject.toml`)
- fastmcp (`pyproject.toml`)
- httpx (`pyproject.toml`)
- python-dotenv (`pyproject.toml`)

## Modules

| Module | Description | Documentation |
|--------|-------------|---------------|
| crawler-package-api | Public crawl/capture APIs, auth/browser support and lazy MCP export. | [Detail](modules/crawler-package-api.md) |
| crawler-env | Shared `.env` config loading with CWD → user-config fallback. | [Detail](modules/crawler-env.md) |
| crawler-config | Crawl4AI configuration, Markdown generation and awaited page-reload hooks. | [Detail](modules/crawler-config.md) |
| crawler-document-pipeline | Document types, references, result conversion and Markdown dedup/heading helpers. | [Detail](modules/crawler-document-pipeline.md) |
| crawler-site-crawl | DFS site crawling with domain/subdomain controls. | [Detail](modules/crawler-site-crawl.md) |
| crawler-cli | Crawl, capture, search and coding-agent setup commands. | [Detail](modules/crawler-cli.md) |
| crawler-mcp-server | FastMCP tools and server runtime for stdio/http transports. | [Detail](modules/crawler-mcp-server.md) |
| crawler-search-orchestration | Provider configuration, search requests, result merging and page-content enrichment. | [Detail](features/search-with-searxng.md) |

## Key Features

| Feature | Description | Documentation |
|---------|-------------|---------------|
| crawling-workflows | Crawl one or many URLs with markdown/json output and concurrency controls. | [Detail](features/crawling-workflows.md) |
| site-crawling-bfs | Crawl sites from a seed URL via DFS; documentation path retained for link stability. | [Detail](features/site-crawling-bfs.md) |
| search-with-searxng | Parallel, attributed SearXNG/You.com results; optional page content and protected-SearXNG headers. | [Detail](features/search-with-searxng.md) |
| mcp-tools-and-transports | Expose crawl/search tools over MCP stdio or HTTP. | [Detail](features/mcp-tools-and-transports.md) |
| cli-commands-and-output | CLI argument parsing, env loading, and output materialization across markdown, JSON, link-stripped, and links-only modes. | [Detail](features/cli-commands-and-output.md) |

## Development

### Setup

1. Install development dependencies with `uv sync --extra dev`.
2. Install Chromium with `uv run playwright install chromium` (Linux: add `--with-deps` for system libraries).
3. Configure `SEARXNG_URL` (optional Basic Auth and `SEARXNG_EXTRA_HEADERS`) and/or `YDC_API_KEY` through `.env` or process environment. See [installation](usage/installation.md).

### Build & Run

- Entry points:
  - `crawl` → `crawler.cli:main` (`pyproject.toml`)
  - `crawl-capture` → `crawler.cli:capture_main` (`pyproject.toml`)
  - `search` → `crawler.cli:search_main` (`pyproject.toml`)
  - `crawl-mcp`, `searxncrawl` → `crawler.mcp_server:main` (`pyproject.toml`)
- `searxncrawl setup` registers the native STDIO server with detected coding agents.
- [MCP server run patterns](usage/mcp-server.md); [CLI reference](usage/cli.md).
- Container runtime in `Dockerfile` and `docker-compose.yml`.

### Testing

- `uv run --extra dev pytest` runs the pytest suite configured in `pyproject.toml`.
- `uvx ruff@0.16.10 check .` matches CI lint.
- CLI coverage includes `tests/test_cli.py`, with links-only output mode scenarios and argument parsing checks.
- Operational test scripts exist in `scripts/test-realworld.sh` and `scripts/test-extended.sh`.

## References

- [README.md](../README.md)
- [CHANGELOG.md](../CHANGELOG.md)
- [pyproject.toml](../pyproject.toml)
