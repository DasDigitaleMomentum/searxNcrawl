# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.24.0] - 2026-05-28

### Fixed
- Prevented MCP stdio protocol corruption from noisy Crawl4AI initialization output by disabling verbose defaults in `build_markdown_run_config()` and `build_discovery_run_config()`.
- Hardened MCP stdio startup for Windows and other non-UTF-8 locales by forcing UTF-8 stdio encoding with replacement error handling.

## [0.23.0] - 2026-05-28

### Added
- CORS support for HTTP transport via `--cors-origins` flag, enabling browser-based MCP clients to connect.

### Fixed
- Shared `.env` config loading between CLI and MCP server for consistent environment resolution.

## [0.22.0] - 2026-04-08

### Added
- Configurable timeout parameters for MCP tools:
  - `crawl(..., timeout: int = 30)` — per-page timeout in seconds
  - `crawl_site(..., timeout: int = 120)` — overall site timeout in seconds
  - Validation: `timeout >= 1` with `ValueError("timeout must be >= 1")`
- Elapsed-time logging for all crawl paths:
  - Per-URL completion and timeout logs in `crawl_page_async()` and `crawl_pages_async()`
  - Batch total elapsed log after `crawl_pages_async()` completes
  - Site crawl completion and timeout logs in `crawl_site_async()`
  - Search success/failure elapsed logs in MCP `search()` tool
- Search retry with exponential backoff for `httpx.RequestError`:
  - Default 3 attempts (2 retries) with configurable `max_retries`
  - `httpx.HTTPStatusError` remains non-retry (fails immediately)
- Unit tests for timeout handling and search retry (`tests/test_timeout.py`):
  - Single-page timeout test (`crawl_page_async`)
  - Batch timeout isolation test (`crawl_pages_async`)
  - Site timeout graceful result test (`crawl_site_async`)
  - MCP structured timeout output test (`crawl_site`)
  - Search retry and non-retry path tests (`search`)

### Changed
- Switched site crawling from BFS to DFS strategy:
  - Eliminates non-deterministic empty pages caused by Crawl4AI's concurrent
    `arun_many()` racing against `wait_for` predicate timeouts
  - DFS processes URLs one at a time (like stable single-page path)
  - Preserves `js_code` reload for lazy-load and bot-protected sites
  - Before: 5/10 pages empty on docs.agno.com (BFS)
  - After: 10/10 pages successful (DFS)
- Added `page_timeout=30000` to Crawl4AI run config (was 60000ms default)
  for faster failure detection on stuck pages
- Changed discovery config `wait_until` from `networkidle` to `domcontentloaded`
  for faster initial page readiness

### Fixed
- Graceful timeout handling in `crawl_site_async()` — returns structured
  `SiteCrawlResult` with error entry instead of raising `TimeoutError`
- Defensive MCP timeout catch in `crawl_site` tool — returns structured
  failed output via `_format_output()` for consistent JSON/markdown contracts
- Per-URL timeout isolation in `crawl_pages_async()` — timeout on one URL
  produces failed `CrawledDocument` without affecting other URLs in batch

## [0.2.1] - 2026-02-28

### Added
- Switchable markdown dedup mode across crawl surfaces:
  - CLI: `crawl --dedup-mode {exact,off}` (default: `exact`)
  - MCP tools: `crawl(..., dedup_mode=...)` and `crawl_site(..., dedup_mode=...)`
  - Python API: `crawl_page(_async)`, `crawl_pages(_async)`, and `crawl_site(_async)` accept `dedup_mode`
- New exact intra-document markdown dedup core with per-document dedup metrics in metadata:
  - `dedup_mode`, `dedup_sections_total`, `dedup_sections_removed`, `dedup_chars_removed`, `dedup_applied`
- Non-destructive dedup guardrail metadata and warning signal fields:
  - `dedup_guardrail_checked`, `dedup_guardrail_triggered`, `dedup_guardrail_reason`
  - `dedup_guardrail_section_removal_rate`, `dedup_guardrail_section_rate_threshold`
- Integration and regression test coverage for dedup behavior and parameter propagation across builder/API/CLI/MCP paths.
- Authenticated crawling MVP with `storage_state` support across:
  - CLI: `crawl --storage-state <path>`
  - MCP tools: `crawl(..., storage_state=...)` and `crawl_site(..., storage_state=...)`
  - Python API auth threading in page/pages/site crawl functions
- Isolated session capture flow via `crawl-capture` with explicit outcomes (`success`, `timeout`, `abort`).
- CDP-based session export flow in `crawl-capture` for real Chrome/Chromium sessions:
  - `--cdp-url` to connect to an existing browser started with `--remote-debugging-port`
  - `--list-sessions` to enumerate selectable sessions in CLI
  - `--cdp-session <index>` for deterministic export selection
  - `--select` for interactive CLI selection before export
  - Compatible with login providers that often block automated-browser sign-in (for example Google)
- Auth/capture test coverage for resolver behavior, API/CLI/MCP auth propagation, and capture lifecycle.

### Fixed
- Resolved duplicate markdown blocks by improving exact dedup section segmentation around heading boundaries.

### Changed
- Updated README documentation for dedup controls, defaults, metadata fields, and usage examples.
- Updated README and module docs for authenticated crawling and isolated session capture usage.
- Expanded README intro/features to highlight CDP-assisted auth capture as part of the authenticated crawling story.
- Added step-by-step user guidance for both capture modes:
  - manual capture flow (`--start-url` + `--completion-url`)
  - running-browser CDP export flow (`--cdp-url` + list/select/export)
- Kept crawler extraction selectors/configuration unchanged while introducing dedup controls (no selector/config drift).
- Preserved crawler extraction/runtime defaults while adding auth + capture support (no wait/SPA/persistent-session default drift).

## [0.1.1] - 2026-01-26

### Fixed
- Added explicit `name: searxncrawl` field for Dockge compatibility
- Converted docker-compose.yml to block-style YAML for better editor support

---

## [0.1.0] - 2026-01-26

### Added
- Initial release of searxNcrawl MCP Server
- Health check configuration in `docker-compose.yml` for container monitoring
- **Web Crawling Tools:**
  - `crawl`: Crawl one or more URLs and extract markdown content
  - `crawl_site`: Crawl entire websites with BFS strategy, depth/page limits
- **Web Search Tool:**
  - `search`: Search the web using SearXNG metasearch engine
- Output format options: `markdown` (default) and `json`
- `remove_links` option to strip URLs from markdown output
- Support for both STDIO and HTTP transports
- Docker and Docker Compose support
- CLI tools: `crawl`, `search`, `crawl-mcp`
- Environment-based configuration for SearXNG (URL, auth)
- Comprehensive README with usage examples

### Technical Details
- Built on [crawl4ai](https://github.com/unclecode/crawl4ai) for headless browser crawling
- Uses Playwright with Chromium for JavaScript rendering
- FastMCP for MCP protocol implementation
- httpx for async HTTP requests to SearXNG
