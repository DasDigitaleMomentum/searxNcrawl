# searxNcrawl

searxNcrawl is a minimal MCP server and CLI toolkit for crawling and search with searxng, a privacy-respecting metasearch engine, that delivers model‑ready Markdown with minimal overhead, saving tokens in coding workflows and replacing generic webfetch tools.

This project is published as **searxNcrawl** at https://github.com/DasDigitaleMomentum/searxNcrawl and is maintained by **DDM – Das Digitale Momentum GmbH & Co KG**. It is the successor to `searxng-mcp` https://github.com/tisDDM/searxng-mcp  (which should be marked deprecated).

Extracted from the l4l-crawl project - the core crawl4ai configuration that took forever to get right.

## Features

### Web Crawling
- **Single page crawling** - Crawl one URL, get markdown
- **Multiple pages** - Batch crawl a list of URLs with concurrency control
- **Site crawling** - BFS strategy with max depth and page limits
- **Clean markdown output** - Optimized for documentation sites
- **Link removal** - Strip all links from output for cleaner LLM context (`--remove-links`)
- **Reference extraction** - Captures all links from crawled pages

### Web Search
- **SearXNG integration** - Privacy-respecting metasearch engine
- **Configurable search** - Language, time range, categories, engines
- **Safe search** - Adjustable content filtering
- **Python API** - `search_async()` and `search()` with structured `SearchResult` return type
- **Pagination** - Navigate result pages via `--pageno` (CLI) or `pageno` parameter

### Authenticated Crawling
- **Cookies injection** - Pass session cookies directly
- **Custom headers** - Add `Authorization: Bearer` or any headers
- **Storage state** - Reuse Playwright browser state (cookies + localStorage)
- **Persistent profiles** - Saved browser profiles across crawls
- **Environment defaults** - Set auth via `CRAWL_AUTH_*` env vars

### Auth Session Capture
- **Interactive login** - Opens a headed browser for manual login
- **Storage state export** - Saves cookies + localStorage as JSON
- **Auto-capture** - Optional URL-match trigger (`--wait-for-url`)
- **Profile support** - Save to named persistent profiles

### SPA / JavaScript Rendering
- **Page load delay** - Wait for JS content to render (`--delay`)
- **Wait strategies** - `load`, `domcontentloaded`, `networkidle`, `commit`

### CLI Tools
- **`crawl`** - Crawl pages from the command line
- **`search`** - Search the web via SearXNG
- **`capture-auth`** - Capture login sessions interactively
- **Global installation** - Available system-wide after `pip install -e .`

### MCP Server
- **STDIO transport** - For MCP harnesses (Zed, opencode, antigravity, VS Code, Claude Code, Codex, OpenClaw, etc.)
- **HTTP transport** - For remote access and web integrations
- **4 tools** - `crawl`, `crawl_site`, `search`, `list_auth_profiles`

## Installation

```bash
cd searxNcrawl
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Install playwright browsers (required!)
playwright install chromium
```

## MCP Server

The crawler is available as an MCP (Model Context Protocol) server, compatible with common MCP harnesses (Zed, opencode, antigravity, VS Code, Claude Code, Codex, OpenClaw, etc.).

### Running the MCP Server

```bash
# STDIO transport (for MCP harnesses such as Zed, opencode, antigravity, VS Code, Claude Code, Codex, OpenClaw, etc.)
python -m crawler.mcp_server

# HTTP transport (for remote access)
python -m crawler.mcp_server --transport http --port 8000

# Custom host binding
python -m crawler.mcp_server --transport http --host 0.0.0.0 --port 9000

# Or via installed script
crawl-mcp --transport http --port 8000

# With custom SearXNG instance
SEARXNG_URL=https://search.example.com python -m crawler.mcp_server
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG instance URL |
| `SEARXNG_USERNAME` | (none) | Optional basic auth username |
| `SEARXNG_PASSWORD` | (none) | Optional basic auth password |
| `CRAWL_AUTH_STORAGE_STATE` | (none) | Default Playwright storage state JSON path |
| `CRAWL_AUTH_COOKIES_FILE` | (none) | Default cookies JSON file path |
| `CRAWL_AUTH_PROFILE` | (none) | Default persistent browser profile directory |
| `MCP_PORT` | `9555` | HTTP port for Docker deployment |

#### SearXNG Instance Requirements

[SearXNG](https://github.com/searxng/searxng) is a privacy-respecting metasearch engine that aggregates results from multiple search engines without tracking users. To use the search functionality of searxNcrawl, you need access to a SearXNG instance with:

- **JSON output format enabled** – The instance must have JSON format enabled in its configuration (this is typically set in `settings.yml` under `search.formats`).
- **Network accessibility** – The instance must be reachable from where you run searxNcrawl.

You can either self-host a SearXNG instance or use a public one. For reliable results, self-hosting is recommended as public instances may have rate limits or restricted API access.

#### Configuration File Search Order

The CLI tools (`crawl`, `search`) look for `.env` files in this order:

1. **Current directory** - `./.env`
2. **User config** - `~/.config/searxncrawl/.env`

If no `.env` is found and `.env.example` exists in the package, it will be automatically copied to `~/.config/searxncrawl/.env` as a starting point.

**Quick setup for global CLI usage:**

```bash
# Option 1: Copy example to user config
mkdir -p ~/.config/searxncrawl
cp .env.example ~/.config/searxncrawl/.env
# Edit with your SEARXNG_URL

# Option 2: Export environment variable
export SEARXNG_URL=http://your-searxng:8888
```

### MCP Harness Configuration

Add to your MCP client configuration (examples include Zed, opencode, antigravity, VS Code, Claude Code, Codex, OpenClaw, etc.):

```json
{
  "mcpServers": {
    "crawler": {
      "command": "python",
      "args": ["-m", "crawler.mcp_server"],
      "cwd": "/path/to/searxNcrawl",
      "env": {
        "SEARXNG_URL": "http://your-searxng-instance:8888"
      }
    }
  }
}
```

Or with uv:

```json
{
  "mcpServers": {
    "crawler": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/searxNcrawl", "python", "-m", "crawler.mcp_server"],
      "env": {
        "SEARXNG_URL": "http://your-searxng-instance:8888"
      }
    }
  }
}
```

### OpenClaw Configuration

[OpenClaw](https://openclaw.ai) is a popular autonomous AI agent (150k+ GitHub stars) that supports MCP natively. To integrate searxNcrawl with OpenClaw, add the following to your OpenClaw MCP config file (`~/.clawdbot/mcp.json` or `openclaw.json`):

**Python with venv:**

```json
{
  "searxNcrawl": {
    "command": "python",
    "args": ["-m", "crawler.mcp_server"],
    "cwd": "/path/to/searxNcrawl",
    "env": {
      "SEARXNG_URL": "http://your-searxng-instance:8888"
    }
  }
}
```

**With uv (no manual venv needed):**

```json
{
  "searxNcrawl": {
    "command": "uv",
    "args": ["run", "--directory", "/path/to/searxNcrawl", "python", "-m", "crawler.mcp_server"],
    "env": {
      "SEARXNG_URL": "http://your-searxng-instance:8888"
    }
  }
}
```

**Docker HTTP endpoint:**

If you prefer running searxNcrawl via Docker, start the server with:

```bash
docker compose up --build
```

Then configure OpenClaw to connect to the HTTP endpoint at `http://localhost:9555/mcp`.

Once configured, OpenClaw will have access to the `crawl`, `crawl_site`, `search`, and `list_auth_profiles` tools.

### Running with Docker Compose

Create a `.env` file (see `.env.example`) and run:

```bash
docker compose up --build
```

The MCP HTTP port is configurable via `MCP_PORT` in `.env`. Default is `9555`, so the server is available at `http://localhost:9555/mcp`.

To run real‑world checks against the Docker setup (crawl, crawl_site, search), use:

```
scripts/test-realworld.sh
```

For extended tests including new features (remove_links, Unicode handling, schema validation):

```
scripts/test-extended.sh
```

For real-world regression checks (configurable URL list, including Mintlify-like docs):

```
scripts/test-regression.sh
```

### MCP Tools

#### `crawl`

Crawl one or more web pages and extract their content as markdown.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `urls` | `List[str]` | required | URLs to crawl |
| `output_format` | `str` | `"markdown"` | Output format: `"markdown"` or `"json"` |
| `concurrency` | `int` | `3` | Max concurrent crawls |
| `remove_links` | `bool` | `false` | Remove all links from markdown output |
| `cookies` | `List[Dict[str,str]]` | `null` | Cookie dicts for authenticated crawling (`name`, `value`, `domain`) |
| `headers` | `Dict[str,str]` | `null` | Custom HTTP headers (e.g. `Authorization: Bearer xyz`) |
| `storage_state` | `str` | `null` | Path to Playwright storage state JSON file |
| `auth_profile` | `str` | `null` | Path to persistent browser profile directory |
| `delay` | `float` | `null` | Seconds to wait after page load (SPA/JS) |
| `wait_until` | `str` | `null` | Wait event: `load`, `domcontentloaded`, `networkidle`, `commit` |
| `aggressive_spa` | `bool` | `false` | Opt in to aggressive SPA fallback (reload + strict `main` wait) |

**Output Formats:**
- `markdown`: Clean concatenated markdown with URL headers and timestamps
- `json`: Full JSON with metadata, references, and statistics

**Examples:**
```
# Single page
crawl(urls=["https://docs.example.com"])

# Multiple pages with JSON output
crawl(urls=["https://example.com/page1", "https://example.com/page2"], output_format="json")

# Clean output without links
crawl(urls=["https://example.com"], remove_links=True)

# Authenticated with cookies
crawl(
    urls=["https://protected.example.com"],
    cookies=[{"name": "sid", "value": "abc", "domain": ".example.com"}]
)

# Authenticated with storage state
crawl(
    urls=["https://protected.example.com"],
    storage_state="/path/to/auth_state.json"
)

# SPA with delay and wait strategy
crawl(
    urls=["https://spa.example.com"],
    delay=3,
    wait_until="networkidle"
)
```

#### `crawl_site`

Crawl an entire website starting from a seed URL using BFS strategy.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | Seed URL to start from |
| `max_depth` | `int` | `2` | Maximum crawl depth (0 = seed only) |
| `max_pages` | `int` | `25` | Maximum pages to crawl |
| `include_subdomains` | `bool` | `false` | Include subdomains |
| `output_format` | `str` | `"markdown"` | Output format: `"markdown"` or `"json"` |
| `remove_links` | `bool` | `false` | Remove all links from markdown output |
| `cookies` | `List[Dict[str,str]]` | `null` | Cookie dicts for authenticated crawling (`name`, `value`, `domain`) |
| `headers` | `Dict[str,str]` | `null` | Custom HTTP headers (e.g. `Authorization: Bearer xyz`) |
| `storage_state` | `str` | `null` | Path to Playwright storage state JSON file |
| `auth_profile` | `str` | `null` | Path to persistent browser profile directory |
| `delay` | `float` | `null` | Seconds to wait after page load (SPA/JS) |
| `wait_until` | `str` | `null` | Wait event: `load`, `domcontentloaded`, `networkidle`, `commit` |
| `aggressive_spa` | `bool` | `false` | Opt in to aggressive SPA fallback (reload + strict `main` wait) |
| `site_stream` | `bool` | `false` | Enable crawl4ai streaming mode for BFS site crawl |

**Examples:**
```
# Basic site crawl
crawl_site(url="https://docs.example.com")

# Deep crawl with more pages
crawl_site(url="https://docs.example.com", max_depth=3, max_pages=50)

# JSON output with full stats
crawl_site(url="https://docs.example.com", output_format="json")

# Clean output without links
crawl_site(url="https://docs.example.com", remove_links=True)

# Authenticated site crawl with browser profile
crawl_site(
    url="https://internal.example.com",
    auth_profile="/path/to/chrome-profile",
    max_depth=3,
    max_pages=50
)

# SPA site crawl with delay
crawl_site(
    url="https://spa.example.com",
    delay=3,
    wait_until="networkidle"
)
```

#### `list_auth_profiles`

List available persistent browser profiles for authenticated crawling.

**Parameters:** None

**Returns:** JSON string with list of profiles, each with `name`, `path`, and `modified` timestamp.

**Example:**
```
list_auth_profiles()
```

#### `search`

Search the web using SearXNG metasearch engine.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | required | Search query string |
| `language` | `str` | `"en"` | Language code (e.g., 'en', 'de', 'fr') |
| `time_range` | `str` | `null` | Time filter: 'day', 'week', 'month', 'year' |
| `categories` | `List[str]` | `null` | Categories: 'general', 'images', 'news', etc. |
| `engines` | `List[str]` | `null` | Specific engines to use |
| `safesearch` | `int` | `1` | 0 (off), 1 (moderate), 2 (strict) |
| `pageno` | `int` | `1` | Page number (minimum 1) |
| `max_results` | `int` | `10` | Maximum results (1-50) |

**Examples:**
```
# Basic search
search(query="python tutorials")

# Search with time filter
search(query="latest AI news", time_range="week")

# Search specific category
search(query="cute cats", categories=["images"])

# Search in German
search(query="Rezepte", language="de")

# Strict safe search
search(query="programming", safesearch=2)
```

**Response Format (JSON):**
```json
{
  "query": "python tutorials",
  "number_of_results": 10,
  "results": [
    {
      "title": "Python Tutorial - W3Schools",
      "url": "https://www.w3schools.com/python/",
      "content": "Well organized tutorials...",
      "engine": "google",
      "category": "general"
    }
  ],
  "answers": [],
  "suggestions": ["python for beginners", "python course"],
  "corrections": []
}
```

### Markdown Output Format

When using `output_format="markdown"`, the output includes:

```markdown
# https://example.com/page1
_Crawled: 2025-01-09 12:00:00 UTC_

[Page content as markdown...]

---

# https://example.com/page2
_Crawled: 2025-01-09 12:00:01 UTC_

[Page content as markdown...]
```

### JSON Output Format

When using `output_format="json"`, the output includes:

```json
{
  "crawled_at": "2025-01-09 12:00:00 UTC",
  "documents": [
    {
      "request_url": "https://example.com",
      "final_url": "https://example.com/",
      "status": "success",
      "markdown": "...",
      "error_message": null,
      "metadata": {
        "title": "Example",
        "status_code": 200
      },
      "references": [
        {"index": 1, "href": "https://example.com/about", "label": "About"}
      ]
    }
  ],
  "summary": {
    "total": 1,
    "successful": 1,
    "failed": 0
  },
  "stats": {
    "total_pages": 1,
    "successful_pages": 1,
    "failed_pages": 0
  }
}
```

## Python API

### Single Page

```python
from crawler import crawl_page, crawl_page_async

# Sync
doc = crawl_page("https://docs.example.com/intro")
print(doc.markdown)
print(doc.final_url)
print(doc.references)  # List of Reference(index, href, label)

# Async
doc = await crawl_page_async("https://docs.example.com/intro")
```

### Multiple Pages

```python
from crawler import crawl_pages, crawl_pages_async

urls = [
    "https://docs.example.com/page1",
    "https://docs.example.com/page2",
    "https://docs.example.com/page3",
]

# Sync (with concurrency limit)
docs = crawl_pages(urls, concurrency=3)

for doc in docs:
    if doc.status == "success":
        print(f"--- {doc.final_url} ---")
        print(doc.markdown[:500])
    else:
        print(f"FAILED: {doc.request_url} - {doc.error_message}")

# Async
docs = await crawl_pages_async(urls, concurrency=5)
```

### Site Crawl (BFS)

```python
from crawler import crawl_site, crawl_site_async

# Crawl entire site with limits
result = crawl_site(
    "https://docs.example.com",
    max_depth=2,           # How deep to follow links
    max_pages=10,          # Stop after N pages
    include_subdomains=False,
)

print(f"Crawled {result.stats['total_pages']} pages")
print(f"Successful: {result.stats['successful_pages']}")
print(f"Failed: {result.stats['failed_pages']}")

for doc in result.documents:
    print(f"{doc.status}: {doc.final_url}")
```

### Authenticated Crawling

```python
from crawler import crawl_page_async
from crawler.auth import AuthConfig

# With storage state (from capture-auth)
auth = AuthConfig(storage_state="./auth_state.json")
doc = await crawl_page_async("https://protected.example.com", auth=auth)

# With cookies
auth = AuthConfig(cookies=[{"name": "sid", "value": "abc", "domain": ".example.com"}])
doc = await crawl_page_async("https://protected.example.com", auth=auth)

# With headers
auth = AuthConfig(headers={"Authorization": "Bearer xyz123"})
doc = await crawl_page_async("https://api.example.com/docs", auth=auth)
```

### Search

```python
from crawler import search_async, search, SearchResult

# Async search
result: SearchResult = await search_async("python tutorials")
print(result.query)
print(f"Found {result.number_of_results} results")
for item in result.results:
    print(f"  {item.title} - {item.url}")

# Sync search
result = search("python tutorials", language="de", max_results=5)

# With pagination
page2 = search("python tutorials", pageno=2)

# All parameters
result = await search_async(
    "AI news",
    language="en",
    time_range="week",
    categories=["news"],
    safesearch=1,
    pageno=1,
    max_results=20,
)
```

## Authenticated Crawling

Crawl pages behind login walls (OAuth, SSO, MFA) by providing authentication context.

### Auth Methods

| Method | CLI Flag | MCP Param | Env Var | Description |
|--------|----------|-----------|---------|-------------|
| Cookies | `--cookies` | `cookies` | `CRAWL_AUTH_COOKIES_FILE` | JSON string, file path, or list of cookie dicts |
| Headers | `--header` (repeatable) | `headers` | -- | Custom HTTP headers |
| Storage state | `--storage-state` | `storage_state` | `CRAWL_AUTH_STORAGE_STATE` | Playwright storage state JSON |
| Browser profile | `--auth-profile` | `auth_profile` | `CRAWL_AUTH_PROFILE` | Persistent Chromium profile |

### Priority Order

Explicit parameters (CLI/MCP/API) > Environment variables > No auth

### Quick Start

```bash
# 1. Capture a login session interactively
crawl capture-auth --url https://login.example.com

# 2. Use the captured session for crawling
crawl --storage-state auth_state.json https://protected.example.com

# Or set as environment default for all crawls
export CRAWL_AUTH_STORAGE_STATE=./auth_state.json
crawl https://protected.example.com
```

## SPA / JavaScript Rendering

Default crawling is intentionally conservative and does **not** force page reloads or strict `<main>` checks.
For SPA/JS-heavy sites, use delay/wait strategy first, and enable aggressive mode only if needed:

```bash
# CLI: Wait 3 seconds after page load
crawl https://spa.example.com --delay 3

# CLI: Wait for all network requests to finish
crawl https://spa.example.com --wait-until networkidle

# CLI: Combined (recommended for complex SPAs)
crawl https://spa.example.com --delay 3 --wait-until networkidle

# CLI: Last-resort fallback for difficult SPA pages
crawl https://spa.example.com --aggressive-spa
```

```python
# Python API
from crawler import crawl_page_async, build_markdown_run_config

config = build_markdown_run_config()
config.delay_before_return_html = 3.0
config.wait_until = "networkidle"
doc = await crawl_page_async("https://spa.example.com", config=config)
```

| Wait Strategy | Description | Use When |
|---------------|-------------|----------|
| `load` | Default — waits for `load` event | Most static sites |
| `domcontentloaded` | DOM parsed, stylesheets may still load | Fast initial render |
| `networkidle` | No network activity for 500ms | SPAs that fetch data via API |
| `commit` | First byte received | Fastest, for known-quick pages |

## CLI Usage

After installation (`pip install -e .`), the `crawl` and `search` commands are available globally.

### crawl

```bash
# Single page to stdout
crawl https://example.com

# Single page to file
crawl https://example.com -o page.md

# Multiple pages to directory
crawl https://example.com/page1 https://example.com/page2 -o output/

# Site crawl
crawl https://docs.example.com --site --max-depth 2 --max-pages 10 -o docs/

# Site crawl with crawl4ai streaming enabled
crawl https://docs.example.com --site --site-stream --max-pages 50

# Output as JSON (includes metadata and references)
crawl https://example.com --json

# Clean output without links (better for LLM context)
crawl https://example.com --remove-links

# JSON output for site crawl
crawl https://docs.example.com --site --max-pages 5 --json -o result.json

# Authenticated crawl with storage state
crawl --storage-state auth_state.json https://protected.example.com

# With custom headers
crawl --header "Authorization: Bearer xyz" https://api.example.com/docs

# SPA with auth combined
crawl --storage-state auth.json --delay 3 --wait-until networkidle https://spa.example.com

# Aggressive SPA fallback (opt-in only)
crawl https://spa.example.com --aggressive-spa

# Verbose logging
crawl https://example.com -v
```

### search

Requires `SEARXNG_URL` environment variable (or `.env` file).

```bash
# Basic search (markdown output)
search "python tutorials"

# Search in German
search "Rezepte" --language de

# Search with time filter
search "latest AI news" --time-range week

# JSON output
search "python" --json

# Save JSON results to file
search "python asyncio" --json -o results.json

# Limit results
search "docker compose" --max-results 5

# Page 2 of results
search "python tutorials" --pageno 2
```

### capture-auth

Capture a login session interactively for reuse with authenticated crawling.

```bash
# Open browser for login, export storage state
crawl capture-auth --url https://login.example.com

# Export to specific file
crawl capture-auth --url https://login.example.com --output my_auth.json

# Use persistent browser profile
crawl capture-auth --url https://login.example.com --profile my-site

# Auto-capture when redirected to dashboard
crawl capture-auth --url https://login.example.com --wait-for-url "/dashboard"

# With custom timeout (default: 300s)
crawl capture-auth --url https://login.example.com --timeout 600
```

## CrawledDocument Structure

```python
@dataclass
class CrawledDocument:
    request_url: str          # Original URL requested
    final_url: str            # Final URL after redirects
    status: str               # "success", "failed", or "redirected"
    markdown: str             # Extracted markdown content
    html: Optional[str]       # Raw HTML (if available)
    headers: Dict[str, Any]   # HTTP response headers
    references: List[Reference]  # Extracted links
    metadata: Dict[str, Any]  # Title, status code, etc.
    raw_markdown: Optional[str]  # Unprocessed markdown
    error_message: Optional[str]  # Error details if failed

@dataclass
class Reference:
    index: int
    href: str
    label: str
```

## Configuration

The default configuration is optimized for documentation sites. For advanced customization:

```python
from crawler import crawl_page_async, build_markdown_run_config, RunConfigOverrides

# Custom configuration
config = build_markdown_run_config(
    RunConfigOverrides(
        delay_before_return_html=1.0,  # Wait longer for JS
        mean_delay=1.0,                # Delay between requests
        scan_full_page=True,
    )
)

doc = await crawl_page_async("https://example.com", config=config)
```

## Dependencies

Minimal dependencies:

- `crawl4ai>=0.7.4,<0.8.0` - The underlying crawler engine (pinned to tested API range)
- `tldextract>=5.1.2` - Domain parsing for site crawls
- `playwright>=1.40.0` - Browser automation
- `fastmcp>=2.0.0` - MCP server framework
- `httpx>=0.27.0` - HTTP client for SearXNG

## License

MIT — © 2026 DDM – Das Digitale Momentum GmbH & Co KG
