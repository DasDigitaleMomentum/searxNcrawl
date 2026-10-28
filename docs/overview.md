---
type: documentation
entity: project-overview
version: 1.1
---

# searxNcrawl

## Purpose

- Python package, CLI and MCP server for web crawling and parallel SearXNG/You.com search.
- Results return as Markdown or JSON; optional search-page crawling includes page content in the same call.
- Protected SearXNG search supports Basic Auth and validated extra headers with secret-file references.

## Architecture

The system is implemented as one package (`crawler/`) with clear layers:

- **Public API/orchestration**: `crawler/__init__.py`
- **Crawler configuration**: `crawler/config.py`
- **Data model + transformation**: `crawler/document.py`, `crawler/references.py`, `crawler/builder.py`
- **Site DFS crawling**: `crawler/site.py`
- **Search orchestration**: `crawler/search_orchestrator.py` (provider selection, SearXNG + You.com calls, merge, serializer)
- **Interfaces**: `crawler/cli.py` and `crawler/mcp_server.py`

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

- Python >=3.10 (`pyproject.toml:6`)
- crawl4ai (`pyproject.toml:8`)
- tldextract (`pyproject.toml:9`)
- playwright (`pyproject.toml:10`)
- fastmcp (`pyproject.toml:11`)
- httpx (`pyproject.toml:12`)
- python-dotenv (`pyproject.toml:13`)

## Modules

| Module | Description | Documentation |
|--------|-------------|---------------|
| crawler-package-api | Public Python crawl APIs and lazy MCP export. | [Detail](modules/crawler-package-api.md) |
| crawler-env | Shared `.env` config loading with CWD → user-config fallback. | [Detail](modules/crawler-env.md) |
| crawler-config | Crawl4AI and markdown generation configuration builders. | [Detail](modules/crawler-config.md) |
| crawler-document-pipeline | Internal document datatypes, reference extraction, and result conversion. | [Detail](modules/crawler-document-pipeline.md) |
| crawler-site-crawl | BFS site crawling with domain/subdomain controls. | [Detail](modules/crawler-site-crawl.md) |
| crawler-cli | Command-line UX for crawl and search workflows. | [Detail](modules/crawler-cli.md) |
| crawler-mcp-server | FastMCP tools and server runtime for stdio/http transports. | [Detail](modules/crawler-mcp-server.md) |

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

1. Create a venv and install editable package (`README.md:35`, `README.md:39`).
2. Install Playwright Chromium (`README.md:42`).
3. Configure `SEARXNG_URL` (optional Basic Auth and `SEARXNG_EXTRA_HEADERS`) and/or `YDC_API_KEY` through `.env` or process environment. See [installation](usage/installation.md).

### Build & Run

- Entry points:
  - `crawl` → `crawler.cli:main` (`pyproject.toml:23`)
  - `crawl-capture` → `crawler.cli:capture_main` (`pyproject.toml:24`)
  - `search` → `crawler.cli:search_main` (`pyproject.toml:25`)
  - `crawl-mcp` → `crawler.mcp_server:main` (`pyproject.toml:26`)
- MCP server run patterns documented in `README.md:51`-`README.md:66`.
- Container runtime in `Dockerfile` and `docker-compose.yml`.

### Testing

- Pytest configured via `pyproject.toml:39`-`pyproject.toml:41`.
- CLI coverage includes `tests/test_cli.py`, with links-only output mode scenarios and argument parsing checks.
- Operational test scripts exist in `scripts/test-realworld.sh` and `scripts/test-extended.sh`.

## References

- [README.md](../README.md)
- [CHANGELOG.md](../CHANGELOG.md)
- [pyproject.toml](../pyproject.toml)
