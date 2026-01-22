# searxNcrawl

searxNcrawl is a minimal MCP server and CLI toolkit for crawling and search that delivers model‑ready Markdown with minimal overhead, saving tokens in coding workflows and replacing generic webfetch tools.

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

### CLI Tools
- **`crawl`** - Crawl pages from the command line
- **`search`** - Search the web via SearXNG
- **Global installation** - Available system-wide after `pip install -e .`

### MCP Server
- **STDIO transport** - For MCP harnesses (Zed, opencode, antigravity, VS Code, Claude Code, Codex, etc.)
- **HTTP transport** - For remote access and web integrations

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

The crawler is available as an MCP (Model Context Protocol) server, compatible with common MCP harnesses (Zed, opencode, antigravity, VS Code, Claude Code, Codex, etc.).

### Running the MCP Server

```bash
# STDIO transport (for MCP harnesses such as Zed, opencode, antigravity, VS Code, Claude Code, Codex, etc.)
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

Add to your MCP client configuration (examples include Zed, opencode, antigravity, VS Code, Claude Code, Codex, etc.):

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

# Output as JSON (includes metadata and references)
crawl https://example.com --json

# Clean output without links (better for LLM context)
crawl https://example.com --remove-links

# JSON output for site crawl
crawl https://docs.example.com --site --max-pages 5 --json -o result.json

# Verbose logging
crawl https://example.com -v
```

### search

Requires `SEARXNG_URL` environment variable (or `.env` file).

```bash
# Basic search
search "python tutorials"

# Search in German
search "Rezepte" --language de

# Search with time filter
search "latest AI news" --time-range week

# Limit results
search "docker compose" --max-results 5

# Save results to file
search "python asyncio" -o results.json

# Specific categories
search "cute cats" --categories images
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

- `crawl4ai>=0.7.4` - The underlying crawler engine
- `tldextract>=5.1.2` - Domain parsing for site crawls
- `playwright>=1.40.0` - Browser automation
- `fastmcp>=2.0.0` - MCP server framework
- `httpx>=0.27.0` - HTTP client for SearXNG

## License

MIT — © 2026 DDM – Das Digitale Momentum GmbH & Co KG
