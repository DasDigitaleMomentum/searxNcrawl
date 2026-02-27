---
type: documentation
entity: module
module: "crawler-core"
version: 1.0
---

# Module: crawler-core

> Part of [searxNcrawl](../overview.md)

## Overview

The `crawler/` package is the sole Python package and contains the entire application logic. It exposes a public Python API (`crawl_page`, `crawl_pages`, `crawl_site`, `search_async`, `search`, `SearchResult`), an MCP server (`mcp_server.py`), and CLI entry points (`cli.py`). Internally it wraps crawl4ai (Playwright/Chromium) for page rendering, httpx for SearXNG queries, and a shared search module (`search.py`) used by all three interfaces.

### Responsibility

- **IS** responsible for: single-page crawling, multi-page batch crawling, BFS site crawling, SearXNG search, MCP tool registration, CLI argument parsing, authentication configuration, interactive auth capture, markdown extraction & formatting, reference parsing, and output formatting (markdown / JSON).
- **IS NOT** responsible for: hosting the SearXNG instance, browser installation (delegated to Playwright CLI), or persistent data storage (no database).

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| crawl4ai | library | Headless Chromium crawl orchestration, CrawlerRunConfig, AsyncWebCrawler, BFS strategies |
| playwright | library | Browser automation (Chromium), interactive auth capture |
| fastmcp | library | MCP server framework (STDIO + HTTP transports) |
| httpx | library | Async HTTP client for SearXNG search API |
| tldextract | library | Domain parsing for site-crawl domain filtering |
| python-dotenv | library | `.env` file loading |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/` | dir | Main Python package |
| `crawler/__init__.py` | file | Public API surface: `crawl_page`, `crawl_page_async`, `crawl_pages`, `crawl_pages_async`, `crawl_site`, `crawl_site_async`, re-exports of data types and config |
| `crawler/auth.py` | file | `AuthConfig` dataclass, `build_browser_config()`, env/file loaders, profile listing |
| `crawler/builder.py` | file | Translates crawl4ai `CrawlResult` into `CrawledDocument` instances |
| `crawler/capture.py` | file | Interactive headed-browser session capture (`capture_auth_state`) |
| `crawler/cli.py` | file | CLI entry points: `main()` (crawl + capture-auth), `search_main()` |
| `crawler/config.py` | file | `RunConfigOverrides` dataclass, `build_markdown_run_config()`, `build_discovery_run_config()`, CSS selector lists |
| `crawler/document.py` | file | `CrawledDocument` and `Reference` dataclasses |
| `crawler/mcp_server.py` | file | FastMCP server with `crawl`, `crawl_site`, `search`, `list_auth_profiles` tools |
| `crawler/references.py` | file | Reference/link parsing from crawl4ai markdown and link metadata |
| `crawler/search.py` | file | Shared SearXNG search: `search_async`, `search`, `SearchResult`, `SearchResultItem`, `SearchError` |
| `crawler/site.py` | file | BFS site crawler: `crawl_site_async`, `SiteCrawlResult`, domain filtering |

## Key Symbols

### `crawler/__init__.py`

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `__all__` | const | public | `crawler/__init__.py:55` | Explicit public API listing |
| `crawl_page_async` | function | public | `crawler/__init__.py:102` | Crawl a single page asynchronously, returns `CrawledDocument` |
| `crawl_page` | function | public | `crawler/__init__.py:138` | Synchronous wrapper for `crawl_page_async` |
| `crawl_pages_async` | function | public | `crawler/__init__.py:148` | Crawl multiple pages concurrently with semaphore, returns list of `CrawledDocument` |
| `crawl_pages` | function | public | `crawler/__init__.py:189` | Synchronous wrapper for `crawl_pages_async` |
| `search_async` | function | public | `crawler/__init__.py:52` | Re-export: async SearXNG search (from `search.py`) |
| `search` | function | public | `crawler/__init__.py:52` | Re-export: sync SearXNG search (from `search.py`) |
| `SearchResult` | class | public | `crawler/__init__.py:52` | Re-export: structured search response (from `search.py`) |
| `SearchResultItem` | class | public | `crawler/__init__.py:52` | Re-export: single search result item (from `search.py`) |
| `SearchError` | class | public | `crawler/__init__.py:52` | Re-export: search exception (from `search.py`) |
| `get_mcp_server` | function | public | `crawler/__init__.py:86` | Lazy-import accessor for the FastMCP `mcp` instance |
| `__getattr__` | function | internal | `crawler/__init__.py:94` | Module-level lazy import for `mcp` attribute |

### `crawler/auth.py`

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `AuthConfig` | class | public | `crawler/auth.py:44` | Dataclass holding cookies, headers, storage_state, user_data_dir for authenticated crawling |
| `AuthConfig.is_empty` | property | public | `crawler/auth.py:74` | Returns True when no auth fields are populated |
| `AuthConfig.resolved_storage_state` | method | public | `crawler/auth.py:85` | Load and return storage state from file or inline data |
| `build_browser_config` | function | public | `crawler/auth.py:102` | Build crawl4ai `BrowserConfig` from an `AuthConfig` instance |
| `load_auth_from_env` | function | public | `crawler/auth.py:147` | Load auth config from `CRAWL_AUTH_*` environment variables |
| `load_auth_from_file` | function | public | `crawler/auth.py:201` | Load auth config from a JSON file |
| `list_auth_profiles` | function | public | `crawler/auth.py:232` | List auth profiles in `~/.crawl4ai/profiles/` |
| `DEFAULT_PROFILES_DIR` | const | public | `crawler/auth.py:40` | Default path: `~/.crawl4ai/profiles` |

### `crawler/builder.py`

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `build_document_from_result` | function | public | `crawler/builder.py:15` | Convert a crawl4ai `CrawlResult` into a `CrawledDocument` |
| `_prepare_metadata` | function | internal | `crawler/builder.py:75` | Extract and normalize metadata dict from `CrawlResult` |
| `_derive_failure_reason` | function | internal | `crawler/builder.py:101` | Determine human-readable failure reason from result |
| `_ensure_markdown` | function | internal | `crawler/builder.py:116` | Ensure markdown generation result exists; re-generates if empty |
| `_extract_requested_url` | function | internal | `crawler/builder.py:154` | Extract the original requested URL from metadata |

### `crawler/capture.py`

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `capture_auth_state` | function | public | `crawler/capture.py:44` | Open headed browser, wait for user login, export storage state JSON |
| `capture_auth_state_sync` | function | public | `crawler/capture.py:260` | Synchronous wrapper for `capture_auth_state` |
| `_resolve_profile_dir` | function | internal | `crawler/capture.py:35` | Resolve profile name/path to absolute directory under `~/.crawl4ai/profiles/` |

### `crawler/cli.py`

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `main` | function | public | `crawler/cli.py:597` | CLI entry point for `crawl` command (and `capture-auth` subcommand) |
| `search_main` | function | public | `crawler/cli.py:775` | CLI entry point for `search` command |
| `_parse_crawl_args` | function | internal | `crawler/cli.py:300` | Parse CLI arguments for the crawl command |
| `_parse_capture_auth_args` | function | internal | `crawler/cli.py:420` | Parse CLI arguments for the capture-auth subcommand |
| `_parse_search_args` | function | internal | `crawler/cli.py:633` | Parse CLI arguments for the search command (incl. `--pageno`) |
| `_run_crawl_async` | function | internal | `crawler/cli.py:489` | Async crawl execution logic |
| `_run_search_async` | function | internal | `crawler/cli.py:730` | Async search execution logic |
| `_run_capture_auth_async` | function | internal | `crawler/cli.py:577` | Async capture-auth execution logic |
| `_build_cli_auth` | function | internal | `crawler/cli.py:210` | Build `AuthConfig` from CLI args with env fallback |
| `_add_auth_args` | function | internal | `crawler/cli.py:264` | Add `--cookies`, `--header`, `--storage-state`, `--auth-profile` args to argparse |
| `_load_config` | function | internal | `crawler/cli.py:23` | Load `.env` from CWD or `~/.config/searxncrawl/` with auto-copy from `.env.example` |
| `_write_output` | function | internal | `crawler/cli.py:147` | Write docs to stdout, file, or directory |
| `_format_search_markdown` | function | internal | `crawler/cli.py:88` | Format search results as Markdown |
| `_strip_markdown_links` | function | internal | `crawler/cli.py:77` | Remove markdown links, keeping only text |
| `_url_to_filename` | function | internal | `crawler/cli.py:137` | Convert URL to safe filename |
| `_doc_to_dict` | function | internal | `crawler/cli.py:121` | Convert `CrawledDocument` to JSON-serializable dict |
| `CONFIG_DIR` | const | internal | `crawler/cli.py:19` | `~/.config/searxncrawl` |
| `CONFIG_ENV_FILE` | const | internal | `crawler/cli.py:20` | `~/.config/searxncrawl/.env` |

### `crawler/config.py`

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `RunConfigOverrides` | class | public | `crawler/config.py:58` | Dataclass for optional crawl-run configuration overrides |
| `build_markdown_run_config` | function | public | `crawler/config.py:157` | Build optimised `CrawlerRunConfig` for single-page markdown extraction |
| `build_discovery_run_config` | function | public | `crawler/config.py:185` | Build `CrawlerRunConfig` optimised for link discovery (site crawling) |
| `build_markdown_generator` | function | public | `crawler/config.py:139` | Build `DefaultMarkdownGenerator` with pruning filter |
| `MAIN_SELECTORS` | const | public | `crawler/config.py:17` | CSS selectors for main content areas (main, article, .content, etc.) |
| `EXCLUDED_SELECTORS` | const | public | `crawler/config.py:34` | CSS selectors for elements to exclude (nav, footer, cookie banners, etc.) |
| `_apply_overrides` | function | internal | `crawler/config.py:99` | Apply `RunConfigOverrides` fields to a `CrawlerRunConfig` |
| `_convert_cache_mode` | function | internal | `crawler/config.py:82` | Convert string cache mode to crawl4ai `CacheMode` enum |

### `crawler/document.py`

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `CrawledDocument` | class | public | `crawler/document.py:18` | Slotted dataclass holding crawl output: URLs, status, markdown, html, headers, references, metadata, error_message |
| `Reference` | class | public | `crawler/document.py:9` | Slotted dataclass for an outgoing link reference (index, href, label) |

### `crawler/mcp_server.py`

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `mcp` | const | public | `crawler/mcp_server.py:63` | The `FastMCP` server instance |
| `crawl` | function (MCP tool) | public | `crawler/mcp_server.py:231` | MCP tool: crawl one or more URLs, supports auth + SPA params |
| `crawl_site` | function (MCP tool) | public | `crawler/mcp_server.py:355` | MCP tool: BFS site crawl, supports auth + SPA params |
| `search` | function (MCP tool) | public | `crawler/mcp_server.py:498` | MCP tool: SearXNG metasearch (delegates to `search.py`) |
| `list_auth_profiles` | function (MCP tool) | public | `crawler/mcp_server.py:465` | MCP tool: list available auth profiles |
| `main` | function | public | `crawler/mcp_server.py:574` | CLI entry point for `crawl-mcp` command |
| `OutputFormat` | enum | internal | `crawler/mcp_server.py:87` | Enum: `markdown`, `json` |
| `_format_output` | function | internal | `crawler/mcp_server.py:159` | Format crawl results to markdown or JSON string |
| `_format_single_doc_markdown` | function | internal | `crawler/mcp_server.py:131` | Format one `CrawledDocument` as markdown |
| `_format_multiple_docs_markdown` | function | internal | `crawler/mcp_server.py:147` | Concatenate multiple docs as markdown with separators |
| `_build_auth_config` | function | internal | `crawler/mcp_server.py:192` | Build `AuthConfig` from MCP tool params, falling back to env vars |
| `_doc_to_dict` | function | internal | `crawler/mcp_server.py:115` | Convert `CrawledDocument` to JSON dict |
| `_strip_markdown_links` | function | internal | `crawler/mcp_server.py:99` | Remove markdown links from text |
| `_format_timestamp` | function | internal | `crawler/mcp_server.py:94` | ISO UTC timestamp string |

### `crawler/references.py`

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `parse_references` | function | public | `crawler/references.py:13` | Build `Reference` objects from markdown block or fallback link metadata |
| `REFERENCE_LINE` | const | internal | `crawler/references.py:10` | Regex pattern for parsing `⟨N⟩ url: label` lines |
| `_parse_markdown_block` | function | internal | `crawler/references.py:24` | Parse references from crawl4ai's references markdown |
| `_build_from_links` | function | internal | `crawler/references.py:40` | Build references from crawl4ai's `links` dict (internal/external) |
| `_split_reference_tail` | function | internal | `crawler/references.py:58` | Split a reference tail into (href, label) |

### `crawler/search.py`

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `SearchResult` | class | public | `crawler/search.py:48` | Structured response from a SearXNG search query |
| `SearchResultItem` | class | public | `crawler/search.py:34` | Single search result item (title, url, content, engine, score, category) |
| `SearchError` | class | public | `crawler/search.py:91` | Exception raised when SearXNG search fails |
| `search_async` | function | public | `crawler/search.py:149` | Async search via SearXNG with full parameter support |
| `search` | function | public | `crawler/search.py:246` | Synchronous wrapper for `search_async` |
| `_get_searxng_client` | function | internal | `crawler/search.py:109` | Create httpx async client for SearXNG with optional basic auth |
| `_raw_to_item` | function | internal | `crawler/search.py:137` | Convert raw SearXNG result dict to `SearchResultItem` |
| `_KNOWN_ITEM_FIELDS` | const | internal | `crawler/search.py:104` | Known field names for `SearchResultItem` attributes |

### `crawler/site.py`

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `crawl_site_async` | function | public | `crawler/site.py:63` | BFS site crawl from a seed URL with domain filtering and page limits |
| `crawl_site` | function | public | `crawler/site.py:182` | Synchronous wrapper for `crawl_site_async` |
| `SiteCrawlResult` | class | public | `crawler/site.py:36` | Dataclass: documents list, errors list, stats dict |
| `SiteCrawlOptions` | class | public | `crawler/site.py:26` | Dataclass: max_depth, max_pages, include_subdomains, stream |
| `_iterate_results` | function | internal | `crawler/site.py:204` | Async generator that unifies different crawl4ai result types |
| `_normalize_host` | function | internal | `crawler/site.py:44` | Strip port and lowercase a hostname |
| `_registrable_domain` | function | internal | `crawler/site.py:51` | Extract registrable domain via tldextract (LRU-cached) |

## Data Flow

### Single Page Crawl

1. Caller invokes `crawl_page_async(url, config, auth)`.
2. `build_markdown_run_config()` creates a `CrawlerRunConfig` (if none provided).
3. `build_browser_config(auth)` creates a `BrowserConfig` with auth params.
4. `AsyncWebCrawler` (crawl4ai) launches headless Chromium, navigates to URL, renders JS.
5. crawl4ai returns a `CrawlResult` with HTML, markdown, metadata, links.
6. `build_document_from_result()` converts this to a `CrawledDocument`.
7. References are parsed via `parse_references()`.

### Site Crawl

1. `crawl_site_async(url, ...)` parses the seed URL's domain.
2. A `BFSDeepCrawlStrategy` is configured with depth/page limits and domain filters.
3. `AsyncWebCrawler.arun()` performs BFS traversal (stream=False).
4. `_iterate_results()` normalises the result container.
5. Each result is converted to a `CrawledDocument` via `build_document_from_result()`.
6. Deduplication by `request_url`, stats computed.

### Search

1. MCP `search()` tool, CLI `search_main()`, or Python API `search_async()`/`search()` is invoked.
2. `crawler/search.py` constructs query params and creates an httpx `AsyncClient` targeting `SEARXNG_URL`.
3. GET request sent to `/search`; JSON response parsed.
4. Results truncated to `max_results`, converted to `SearchResultItem` objects.
5. A `SearchResult` dataclass is returned to the caller.
6. MCP/CLI format the result as JSON string or Markdown for output.

### Auth Capture

1. `capture_auth_state()` opens a headed Chromium browser via Playwright.
2. User completes login manually.
3. URL-match polling or browser-close detection triggers capture.
4. `context.storage_state()` is exported to a JSON file.
5. The JSON file can be reused via `--storage-state` or `AuthConfig`.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SEARXNG_URL` | `http://localhost:8888` | SearXNG instance endpoint |
| `SEARXNG_USERNAME` | (none) | SearXNG basic-auth username |
| `SEARXNG_PASSWORD` | (none) | SearXNG basic-auth password |
| `CRAWL_AUTH_STORAGE_STATE` | (none) | Default Playwright storage state JSON path |
| `CRAWL_AUTH_COOKIES_FILE` | (none) | Default cookies JSON file |
| `CRAWL_AUTH_PROFILE` | (none) | Default persistent browser profile directory |

Config files: `.env` (CWD) > `~/.config/searxncrawl/.env` > auto-copy from `.env.example`.

## Inventory Notes

- **Coverage**: full
- **Notes**: All 11 source files in `crawler/` are documented. Every public function, class, and constant is listed. Internal helpers (prefixed with `_`) are included where they represent significant logic.
