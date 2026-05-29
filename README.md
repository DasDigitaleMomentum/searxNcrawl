# searxNcrawl

MCP server and CLI toolkit for web search and crawling, built on [Crawl4AI](https://github.com/unclecode/crawl4ai) and [SearXNG](https://github.com/searxng/searxng).

Published at [github.com/DasDigitaleMomentum/searxNcrawl](https://github.com/DasDigitaleMomentum/searxNcrawl) — maintained by **DDM – Das Digitale Momentum GmbH & Co KG**. Successor to `searxng-mcp`.

## Quick Start

Pick your setup:

### Docker Compose (everything included)

SearXNG, Playwright, and the MCP server — one command.

```bash
cp .env.example .env          # edit SEARXNG_URL if needed
docker compose up --build
```

➜ MCP server at `http://localhost:9555/mcp`

### pip (standalone)

CLI tools, Python API, and MCP server. SearXNG required for search.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
```

### uv (standalone)

Same capabilities as pip.

```bash
uv sync
uv run playwright install chromium
```

### What you get

| Feature                 | Docker Compose | pip / uv  |
| ----------------------- | -------------- | --------- |
| MCP Server (STDIO)      | —              | ✅        |
| MCP Server (HTTP)       | ✅             | ✅        |
| Web Crawl               | ✅             | ✅        |
| Web Search              | ✅ (included)  | ✅¹       |
| CLI Tools               | via `exec`²    | ✅        |
| Python API              | —              | ✅        |
| CORS (HTTP)             | ✅             | ✅        |

¹ Requires a SearXNG instance. ² `docker compose exec searxncrawl crawl ...`

## Features

### Crawling
- Single page, multi-page, and **site crawling** (DFS with depth/page limits)
- Production-tested extraction config optimized for documentation sites
- Configurable timeouts with graceful error handling

### Content Quality
- **Markdown deduplication** — `exact` (default) removes repeated blocks, `off` disables it
- **Link removal** — strip all links for cleaner LLM context (`--remove-links`)
- **Dedup guardrails** — non-destructive metadata signals when removal is unusually aggressive

### Web Search
- SearXNG metasearch integration (privacy-respecting)
- Configurable language, time range, categories, engines, safe search

### MCP Server
- **STDIO transport** — for MCP harnesses (Zed, opencode, VS Code, Claude Code, etc.)
- **HTTP transport** — for remote access and browser clients
- **CORS support** — configurable origins for browser-based MCP clients
- Noise-free startup with UTF-8 encoding (cross-platform, incl. Windows)

### CLI Tools
- `crawl` — crawl pages from the command line
- `search` — search the web via SearXNG
- `crawl-capture` — session capture for authenticated crawling

## Installation

### Docker Compose

The Compose stack includes searxNcrawl + SearXNG + Playwright/Chromium.

```bash
cp .env.example .env
# Edit .env: set SEARXNG_URL if using external SearXNG, or keep default
docker compose up --build
```

| Variable    | Default                   | Description             |
| ----------- | ------------------------- | ----------------------- |
| `MCP_PORT`  | `9555`                    | MCP server HTTP port    |

The MCP server is available at `http://localhost:9555/mcp`.

### pip

```bash
cd searxNcrawl
python -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

### uv

```bash
cd searxNcrawl
uv sync
uv run playwright install chromium
```

### SearXNG (search feature)

The `search` tool and CLI command require a SearXNG instance with **JSON output enabled** (`search.formats` in `settings.yml`). Docker Compose includes one automatically. For pip/uv, you need your own — self-hosting is recommended over public instances (rate limits).

**Environment variables:**

| Variable          | Default                 | Description              |
| ----------------- | ----------------------- | ------------------------ |
| `SEARXNG_URL`     | `http://localhost:8888` | SearXNG instance URL     |
| `SEARXNG_USERNAME` | (none)                  | Optional basic auth user |
| `SEARXNG_PASSWORD` | (none)                  | Optional basic auth pass |

**Config file search order** (CLI tools only):

1. `./.env` — current directory
2. `~/.config/searxncrawl/.env` — user config

If no `.env` exists, `.env.example` is auto-copied to the user config path.

## Usage

### MCP Server

#### Start the server

```bash
# STDIO transport (for MCP harnesses)
python -m crawler.mcp_server

# HTTP transport
python -m crawler.mcp_server --transport http --port 8000

# HTTP with CORS
python -m crawler.mcp_server --transport http --cors-origins "http://localhost:3000"

# Docker (HTTP only)
docker compose up --build
```

#### MCP client configuration

**Python with venv:**

```json
{
  "mcpServers": {
    "crawler": {
      "command": "python",
      "args": ["-m", "crawler.mcp_server"],
      "cwd": "/path/to/searxNcrawl",
      "env": { "SEARXNG_URL": "http://your-searxng:8888" }
    }
  }
}
```

**With uv (no manual venv):**

```json
{
  "mcpServers": {
    "crawler": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/searxNcrawl", "python", "-m", "crawler.mcp_server"],
      "env": { "SEARXNG_URL": "http://your-searxng:8888" }
    }
  }
}
```

**Docker (HTTP endpoint):**

```json
{
  "mcpServers": {
    "crawler": {
      "url": "http://localhost:9555/mcp"
    }
  }
}
```

#### CORS

HTTP transport can emit CORS headers for browser-based MCP clients:

```bash
crawl-mcp --transport http --cors-origins "http://localhost:3000,https://myapp.com"
crawl-mcp --transport http --cors-origins "*"   # all origins — local dev only
```

Without `--cors-origins`, no CORS headers are sent (browsers will block cross-origin requests).

### CLI Tools

After `pip install -e .` (or `uv sync`), the following commands are available:

```bash
# Crawl a page
crawl https://docs.example.com

# Site crawl with depth limit
crawl https://docs.example.com --site --max-depth 2 --max-pages 10 -o docs/

# Clean output (no links)
crawl https://example.com --remove-links

# Search
search "python tutorials"
search "Rezepte" --language de --max-results 5

# Session capture for authenticated crawling
crawl-capture --start-url https://example.com/login \
    --completion-url 'https://example.com/dashboard.*' \
    --output ./state.json
```

See [Session Capture](docs/usage/session-capture.md) for the full `crawl-capture` guide.

### Python API

```python
from crawler import crawl_page, crawl_page_async, crawl_site, crawl_site_async

# Single page
doc = await crawl_page_async("https://docs.example.com/intro", dedup_mode="exact")
print(doc.markdown)

# Site crawl
result = crawl_site("https://docs.example.com", max_depth=2, max_pages=10)
for doc in result.documents:
    print(f"{doc.status}: {doc.final_url}")

# Authenticated crawl
doc = await crawl_page_async(
    "https://example.com/private",
    auth={"storage_state": "/path/to/state.json"},
)
```

## Reference

- **[MCP Tools](docs/usage/mcp-tools.md)** — full parameter reference for `crawl`, `crawl_site`, `search`
- **[Output Formats](docs/usage/output-formats.md)** — Markdown and JSON output structure, including `CrawledDocument`
- **[Session Capture](docs/usage/session-capture.md)** — manual login flow and CDP session export

## Configuration

Default config is optimized for documentation sites. Customize via overrides:

```python
from crawler import build_markdown_run_config, RunConfigOverrides

config = build_markdown_run_config(
    RunConfigOverrides(
        delay_before_return_html=1.0,
        mean_delay=1.0,
        scan_full_page=True,
    )
)
doc = await crawl_page_async("https://example.com", config=config)
```

## Dependencies

- `crawl4ai>=0.7.4` — crawler engine
- `playwright>=1.40.0` — browser automation
- `fastmcp>=2.0.0` — MCP server framework
- `httpx>=0.27.0` — HTTP client for SearXNG
- `tldextract>=5.1.2` — domain parsing for site crawls

## License

MIT — © 2026 DDM – Das Digitale Momentum GmbH & Co KG
