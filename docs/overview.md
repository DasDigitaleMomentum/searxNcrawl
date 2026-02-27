---
type: documentation
entity: project-overview
version: 1.0
---

# searxNcrawl

## Purpose

searxNcrawl is a minimal MCP (Model Context Protocol) server and CLI toolkit that wraps SearXNG metasearch and Playwright-based web crawling to deliver model-ready Markdown. It replaces generic web-fetch tools with a purpose-built crawler optimised for documentation sites, delivering cleaner output with fewer tokens. The project also supports authenticated crawling (cookies, headers, storage state, persistent browser profiles) and interactive auth-session capture.

Maintained by **DDM -- Das Digitale Momentum GmbH & Co KG** and published at <https://github.com/DasDigitaleMomentum/searxNcrawl>. Successor to the deprecated `searxng-mcp`.

## Architecture

### System Diagram

```
                        +-------------------+
                        |   MCP Harness     |
                        |  (Zed, opencode,  |
                        |  Claude Code ...) |
                        +--------+----------+
                                 | STDIO / HTTP
                        +--------v----------+
                        |   mcp_server.py   |  FastMCP server
                        |  (crawl, search,  |
                        | crawl_site, auth) |
                        +----+----+----+----+
                             |    |    |
              +--------------+    |    +---------------+
              |                   |                    |
     +--------v------+  +--------v--------+  +--------v------+
     | __init__.py    |  |  SearXNG (httpx)|  |  auth.py      |
     | crawl_page     |  |  /search JSON   |  |  AuthConfig   |
     | crawl_pages    |  +-----------------+  |  BrowserConfig|
     +--------+-------+                       +-------+-------+
              |                                       |
     +--------v-------+                      +--------v-------+
     |   site.py       |                      |  capture.py    |
     | BFS crawl_site  |                      | Interactive    |
     +--------+--------+                      | auth capture   |
              |                               +----------------+
     +--------v--------+
     | builder.py       |  CrawlResult -> CrawledDocument
     | config.py        |  RunConfig factory
     | document.py      |  CrawledDocument / Reference
     | references.py    |  Link / reference parser
     +------------------+
              |
     +--------v--------+
     |   crawl4ai       |  Headless Chromium via Playwright
     +------------------+

     +------------------+
     |   cli.py          |  CLI: crawl, search, capture-auth
     +------------------+
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python >= 3.10 | Runtime |
| Browser engine | Playwright >= 1.40 + Chromium | JS rendering & crawling |
| Crawl framework | crawl4ai >= 0.7.4 | Headless crawl orchestration |
| MCP framework | FastMCP >= 2.0.0 | Model Context Protocol server |
| HTTP client | httpx >= 0.27.0 | Async requests to SearXNG |
| Domain parsing | tldextract >= 5.1.2 | Domain filtering for site crawls |
| Env management | python-dotenv >= 1.0.1 | .env file loading |
| Testing | pytest >= 8.0, pytest-asyncio >= 0.23 | Unit & async test suite |
| Containerisation | Docker, Docker Compose | Production deployment |

## Modules

| Module | Description | Documentation |
|--------|-------------|---------------|
| crawler (core) | Main Python package -- public API, crawl orchestration, data types, config, auth, capture, CLI, MCP server | [Detail](modules/crawler-core.md) |
| scripts | Shell helper scripts for Docker builds and integration testing | [Detail](modules/scripts.md) |
| tests | Comprehensive test suite (unit + E2E) | [Detail](modules/tests.md) |

## Key Features

| Feature | Description | Documentation |
|---------|-------------|---------------|
| Web Crawling | Single-page, multi-page, and BFS site crawling with Markdown extraction | [Detail](features/web-crawling.md) |
| SearXNG Search | Privacy-respecting metasearch via SearXNG with filters and pagination | [Detail](features/searxng-search.md) |
| Authenticated Crawling | Crawl pages behind login walls using cookies, headers, storage state, or browser profiles | [Detail](features/authenticated-crawling.md) |
| Auth Capture | Interactive headed-browser flow to capture login sessions for reuse | [Detail](features/auth-capture.md) |
| MCP Server | Model Context Protocol server (STDIO + HTTP) exposing crawl/search as LLM tools | [Detail](features/mcp-server.md) |
| CLI Interface | `crawl`, `search`, and `capture-auth` command-line tools | [Detail](features/cli.md) |

## Development

### Setup

```bash
# Clone & enter repo
cd searxNcrawl

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode (with dev deps)
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium
```

### Build & Run

```bash
# Run MCP server (STDIO, default)
python -m crawler.mcp_server

# Run MCP server (HTTP)
python -m crawler.mcp_server --transport http --port 8000

# Docker
docker compose up --build

# Docker build script
scripts/build.sh
```

### Testing

```bash
# Unit tests
pytest

# Real-world integration tests (requires Docker + .env)
scripts/test-realworld.sh

# Extended integration tests
scripts/test-extended.sh
```

### Configuration

Environment variables are loaded from `.env` files with this search order:

1. `./.env` (current directory)
2. `~/.config/searxncrawl/.env` (user config)
3. Auto-created from `.env.example` if neither exists

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG instance URL |
| `SEARXNG_USERNAME` | (none) | Optional SearXNG basic-auth username |
| `SEARXNG_PASSWORD` | (none) | Optional SearXNG basic-auth password |
| `CRAWL_AUTH_STORAGE_STATE` | (none) | Default Playwright storage state JSON path |
| `CRAWL_AUTH_COOKIES_FILE` | (none) | Default cookies JSON file path |
| `CRAWL_AUTH_PROFILE` | (none) | Default persistent browser profile directory |
| `MCP_PORT` | `9555` | HTTP port for Docker deployment |

## References

- [crawl4ai](https://github.com/unclecode/crawl4ai) -- underlying crawler engine
- [SearXNG](https://github.com/searxng/searxng) -- privacy-respecting metasearch engine
- [FastMCP](https://github.com/jlowin/fastmcp) -- MCP server framework
- [Playwright](https://playwright.dev/python/) -- browser automation
- [Model Context Protocol](https://modelcontextprotocol.io/) -- LLM tool protocol spec
