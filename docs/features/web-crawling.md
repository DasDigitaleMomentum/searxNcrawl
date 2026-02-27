---
type: documentation
entity: feature
feature: "web-crawling"
version: 1.0
---

# Feature: Web Crawling

> Part of [searxNcrawl](../overview.md)

## Summary

Web crawling is the core feature of searxNcrawl. It renders web pages with a headless Chromium browser (via Playwright/crawl4ai), extracts clean Markdown optimised for LLM consumption, and supports single-page, multi-page batch, and BFS site-wide crawling modes. Output can be Markdown or structured JSON with metadata and extracted references.

## How It Works

### User Flow

1. User provides one or more URLs via CLI (`crawl`), MCP tool, or Python API.
2. Optionally specifies mode: single page (default), multi-page (multiple URLs), or site crawl (`--site`).
3. Optionally sets output format (`--json`), link removal (`--remove-links`), SPA delay (`--delay`), or wait strategy (`--wait-until`).
4. Receives clean Markdown (or JSON) content extracted from the rendered pages.

### Technical Flow

#### Single Page

1. `crawl_page_async(url, config, auth)` is called (`crawler/__init__.py:95`).
2. A `CrawlerRunConfig` is built via `build_markdown_run_config()` (`config.py:157`) with:
   - Target elements: `MAIN_SELECTORS` (main, article, .content, etc.)
   - Excluded elements: `EXCLUDED_SELECTORS` (nav, footer, cookie banners)
   - Pruning content filter (threshold 0.45, dynamic)
   - JS: page reload + scroll to bottom
   - Wait-for: main element with >50 chars of text
   - Cache: bypass
3. A `BrowserConfig` is built via `build_browser_config(auth)` (`auth.py:102`).
4. `AsyncWebCrawler.arun(url, config)` launches Chromium, renders the page.
5. The `CrawlResult` is translated to `CrawledDocument` by `build_document_from_result()` (`builder.py:15`):
   - Extracts fit_markdown > markdown_with_citations > raw_markdown (priority order).
   - Parses references from markdown block or link metadata.
   - Collects metadata (title, status code, URLs).
6. `CrawledDocument` is returned with `.markdown`, `.references`, `.metadata`, `.status`.

#### Multi-Page Batch

1. `crawl_pages_async(urls, config, auth, concurrency)` is called (`__init__.py:141`).
2. An `asyncio.Semaphore(concurrency)` limits parallel crawls.
3. Each URL is crawled via `crawl_page_async()` inside the semaphore.
4. Failed crawls produce a `CrawledDocument` with `status="failed"` instead of raising.
5. Results are returned in the same order as input URLs.

#### BFS Site Crawl

1. `crawl_site_async(url, max_depth, max_pages, include_subdomains, auth, run_config)` is called (`site.py:63`).
2. The seed URL's domain is parsed; `DomainFilter` restricts links to same domain (optionally with subdomains).
3. A `BFSDeepCrawlStrategy` is attached to the run config with depth/page limits.
4. `stream=False` is forced (crawl4ai BFS streaming has a known bug).
5. `AsyncWebCrawler.arun()` performs the complete BFS traversal.
6. `_iterate_results()` normalises the result into an async iterable.
7. Each result is converted to `CrawledDocument`; duplicates are filtered by `request_url`.
8. A `SiteCrawlResult` is returned with documents, errors, and stats.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-core](../modules/crawler-core.md) | `crawl_page_async`, `crawl_page`, `crawl_pages_async`, `crawl_pages` | Public API for single/multi-page crawling |
| [crawler-core](../modules/crawler-core.md) | `crawl_site_async`, `crawl_site`, `SiteCrawlResult`, `SiteCrawlOptions` | BFS site crawling |
| [crawler-core](../modules/crawler-core.md) | `build_markdown_run_config`, `build_discovery_run_config`, `RunConfigOverrides` | Crawl configuration factory |
| [crawler-core](../modules/crawler-core.md) | `build_document_from_result`, `_ensure_markdown` | Result-to-document translation |
| [crawler-core](../modules/crawler-core.md) | `CrawledDocument`, `Reference` | Output data structures |
| [crawler-core](../modules/crawler-core.md) | `parse_references` | Reference/link extraction |
| [crawler-core](../modules/crawler-core.md) | `MAIN_SELECTORS`, `EXCLUDED_SELECTORS` | Content targeting CSS selectors |

## Configuration

| Parameter | CLI Flag | MCP Param | Default | Purpose |
|-----------|----------|-----------|---------|---------|
| Output format | `--json` | `output_format` | `markdown` | Markdown or JSON output |
| Remove links | `--remove-links` | `remove_links` | `false` | Strip URLs from markdown for cleaner LLM context |
| Max depth | `--max-depth` | `max_depth` | `2` | BFS crawl depth limit |
| Max pages | `--max-pages` | `max_pages` | `25` | BFS page limit |
| Include subdomains | `--include-subdomains` | `include_subdomains` | `false` | Allow subdomain URLs in site crawl |
| Concurrency | `--concurrency` | `concurrency` | `3` | Max parallel crawls for batch mode |
| SPA delay | `--delay` | `delay` | `0.5` | Seconds to wait after page load |
| Wait strategy | `--wait-until` | `wait_until` | `load` | Playwright wait event (load, domcontentloaded, networkidle, commit) |

## Edge Cases & Limitations

- **SPA / JS-heavy pages**: Default config waits for `<main>` element with >50 chars. For SPAs that load data asynchronously, use `--delay` and `--wait-until networkidle`.
- **crawl4ai BFS streaming bug**: `stream=True` returns 0 results with BFS strategy. The code forces `stream=False`, meaning all results are held in RAM until the crawl completes. This is acceptable given the `max_pages` limit.
- **Markdown quality**: The pruning filter (threshold 0.45) may occasionally cut relevant content or include noise. The priority chain (fit_markdown > citations > raw) provides fallback.
- **Domain filtering**: Uses `tldextract` for registrable domain matching. Edge cases with unusual TLDs or IP-based URLs may not filter correctly.
- **No JavaScript interaction**: Pages requiring form submission or clicks beyond initial load are not supported (use `capture-auth` for login flows).

## Related Features

- [Authenticated Crawling](authenticated-crawling.md) -- auth parameters are threaded through all crawl functions
- [Auth Capture](auth-capture.md) -- capture sessions for reuse with crawling
- [MCP Server](mcp-server.md) -- exposes crawl tools to LLM agents
- [CLI Interface](cli.md) -- command-line access to crawling
