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
2. A `CrawlerRunConfig` is built via `build_markdown_run_config()` (`config.py`) with:
   - Target elements: `MAIN_SELECTORS` (main, article, .content, etc.)
   - Excluded elements: `EXCLUDED_SELECTORS` (nav, footer, cookie banners)
   - Pruning content filter (threshold 0.45, dynamic)
   - Cache: bypass
   - Optional aggressive SPA fallback (reload + strict main wait) as explicit opt-in
3. A `BrowserConfig` is built via `build_browser_config(auth)` (`auth.py:102`).
4. `AsyncWebCrawler.arun(url, config)` launches Chromium, renders the page.
5. The `CrawlResult` is translated to `CrawledDocument` by `build_document_from_result()` (`builder.py:15`):
   - Extracts fit_markdown > markdown_with_citations > raw_markdown (priority order).
   - Parses references from markdown block or link metadata.
   - Collects metadata (title, status code, URLs).
6. `CrawledDocument` is returned with `.markdown`, `.references`, `.metadata`, `.status`.

#### Multi-Page Batch

1. `crawl_pages_async(urls, config, auth, concurrency)` is called (`__init__.py`).
2. A single `AsyncWebCrawler` is created for the full batch.
3. `AsyncWebCrawler.arun_many()` executes URLs with `SemaphoreDispatcher(semaphore_count=concurrency)`.
4. Failed crawls produce a `CrawledDocument` with `status="failed"` instead of raising.
5. Results are mapped back to input URL order.

#### BFS Site Crawl

1. `crawl_site_async(url, max_depth, max_pages, include_subdomains, auth, run_config)` is called (`site.py:63`).
2. The seed URL's domain is parsed; `DomainFilter` restricts links to same domain (optionally with subdomains).
3. A `BFSDeepCrawlStrategy` is attached to the run config with depth/page limits.
4. `stream` defaults to buffered mode (`False`) for deterministic responses, but can be enabled via CLI/MCP override.
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
| SPA delay | `--delay` | `delay` | `null` | Optional seconds to wait after page load |
| Wait strategy | `--wait-until` | `wait_until` | `null` | Optional Playwright wait event (load, domcontentloaded, networkidle, commit) |
| Aggressive SPA | `--aggressive-spa` | `aggressive_spa` | `false` | Opt in to reload + strict `main` wait |
| Site streaming | `--site-stream` | `site_stream` | `false` | Enable crawl4ai streaming mode for BFS crawl |

## Edge Cases & Limitations

- **SPA / JS-heavy pages**: Default config is conservative. For async-rendered content, first use `--delay` + `--wait-until networkidle`. Use `--aggressive-spa` only as fallback.
- **BFS streaming trade-off**: `stream=False` buffers results in memory; `--site-stream` can reduce memory pressure on large crawls, depending on crawl4ai behavior/version.
- **Markdown quality**: The pruning filter (threshold 0.45) may occasionally cut relevant content or include noise. The priority chain (fit_markdown > citations > raw) provides fallback.
- **Domain filtering**: Uses `tldextract` for registrable domain matching. Edge cases with unusual TLDs or IP-based URLs may not filter correctly.
- **No JavaScript interaction**: Pages requiring form submission or clicks beyond initial load are not supported (use `capture-auth` for login flows).

## Related Features

- [Authenticated Crawling](authenticated-crawling.md) -- auth parameters are threaded through all crawl functions
- [Auth Capture](auth-capture.md) -- capture sessions for reuse with crawling
- [MCP Server](mcp-server.md) -- exposes crawl tools to LLM agents
- [CLI Interface](cli.md) -- command-line access to crawling
