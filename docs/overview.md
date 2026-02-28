---
type: documentation
entity: project-overview
version: 1.0
---

# searxNcrawl

## Purpose

searxNcrawl is a Python package that provides web crawling and SearXNG search through both a CLI and an MCP server, returning model-friendly Markdown or JSON for downstream agent/tool workflows (`README.md:3`, `README.md:11`, `README.md:19`, `README.md:29`).

## Architecture

The system is implemented as one package (`crawler/`) with clear layers:

- **Public API/orchestration**: `crawler/__init__.py`
- **Crawler configuration**: `crawler/config.py`
- **Data model + transformation**: `crawler/document.py`, `crawler/references.py`, `crawler/builder.py`
- **Site BFS crawling**: `crawler/site.py`
- **Interfaces**: `crawler/cli.py` and `crawler/mcp_server.py`

### System Diagram

```text
User / Agent
  |                          |
  v                          v
CLI (crawl/search)      MCP client (stdio/http)
  |                          |
  +------------+-------------+
               v
      Interface Layer
  (crawler/cli.py, crawler/mcp_server.py)
               |
               v
      Crawl/Search Orchestration
 (crawler.__init__, crawler.site)
          |               |
          v               v
       Crawl4AI       SearXNG API
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
| crawler-config | Crawl4AI and markdown generation configuration builders. | [Detail](modules/crawler-config.md) |
| crawler-document-pipeline | Internal document datatypes, reference extraction, and result conversion. | [Detail](modules/crawler-document-pipeline.md) |
| crawler-site-crawl | BFS site crawling with domain/subdomain controls. | [Detail](modules/crawler-site-crawl.md) |
| crawler-cli | Command-line UX for crawl and search workflows. | [Detail](modules/crawler-cli.md) |
| crawler-mcp-server | FastMCP tools and server runtime for stdio/http transports. | [Detail](modules/crawler-mcp-server.md) |

## Key Features

| Feature | Description | Documentation |
|---------|-------------|---------------|
| crawling-workflows | Crawl one or many URLs with markdown/json output and concurrency controls. | [Detail](features/crawling-workflows.md) |
| site-crawling-bfs | Crawl complete sites from a seed URL via BFS strategy. | [Detail](features/site-crawling-bfs.md) |
| search-with-searxng | Query SearXNG with filters and structured output. | [Detail](features/search-with-searxng.md) |
| mcp-tools-and-transports | Expose crawl/search tools over MCP stdio or HTTP. | [Detail](features/mcp-tools-and-transports.md) |
| cli-commands-and-output | CLI argument parsing, env loading, and output materialization. | [Detail](features/cli-commands-and-output.md) |

## Development

### Setup

1. Create a venv and install editable package (`README.md:35`, `README.md:39`).
2. Install Playwright Chromium (`README.md:42`).
3. Configure `SEARXNG_URL` and optional credentials via `.env`/env vars (`README.md:70`, `.env.example:2`).

### Build & Run

- Entry points:
  - `crawl` → `crawler.cli:main` (`pyproject.toml:23`)
  - `search` → `crawler.cli:search_main` (`pyproject.toml:24`)
  - `crawl-mcp` → `crawler.mcp_server:main` (`pyproject.toml:25`)
- MCP server run patterns documented in `README.md:51`-`README.md:66`.
- Container runtime in `Dockerfile` and `docker-compose.yml`.

### Testing

- Pytest configured via `pyproject.toml:39`-`pyproject.toml:41`.
- In this branch snapshot, `tests/` currently contains only `__pycache__/` entries.
- Operational test scripts exist in `scripts/test-realworld.sh` and `scripts/test-extended.sh`.

## References

- [README.md](../README.md)
- [CHANGELOG.md](../CHANGELOG.md)
- [pyproject.toml](../pyproject.toml)
