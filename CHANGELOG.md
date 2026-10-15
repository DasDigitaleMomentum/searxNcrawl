# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.32.0] - 2026-10-15

**Upgrade note:** existing SearXNG-only setups must set `SEARXNG_URL` explicitly; there is no `http://localhost:8888` default any more. `SEARXNG_URL` must not embed credentials (`https://user:pw@host` is rejected); use `SEARXNG_USERNAME`/`SEARXNG_PASSWORD` instead.

### Added
- Multi-provider search: CLI `search` and MCP `search` query every configured provider (SearXNG, You.com) in parallel and return one merged list (conservative URL dedup, round-robin, results found by several providers first). A partial failure still returns the other providers' results.
- You.com provider, enabled by `YDC_API_KEY` (keyed API only; queries go to You.com, US). Requests use `POST /v1/search` with a JSON body. `safesearch` maps to `off`/`moderate`/`strict`; `language` maps to You.com's supported codes (`en-us` → `EN`; unsupported codes such as `zh` search without a language filter instead of failing with HTTP 422); pages beyond 10 return no You.com results; `content` falls back to the first snippet when the description is empty. HTTP 403 is reported as a missing key scope, separate from 401.
- Provider selection per call: MCP `providers` parameter, CLI `--providers searxng,youcom`.
- `providers` field on every result; the CLI markdown output shows it as a `**Sources:**` line.
- `searxncrawl setup` registers the MCP server with the installed coding agents (Claude Code, Codex, Gemini CLI, Cursor, VS Code, Claude Desktop) in one step. It shows each change, asks before applying it (`--yes` skips the prompt), backs up every file it touches, updates instead of duplicating on re-runs, and `setup --remove` unregisters again.
- `searxncrawl setup` can also store a You.com API key (`--ydc-api-key`, or a hidden prompt suggesting `$YDC_API_KEY`). The key is masked as `<hidden>` in everything `setup` prints, and `setup` warns when no search provider is configured.
- `server.json` for the official MCP Registry (`io.github.DasDigitaleMomentum/searxncrawl`). The release workflow now fails if its versions differ from `pyproject.toml`. See `docs/registry.md`.

### Changed
- **Breaking:** no `SEARXNG_URL` default any more (code, `docker-compose.yml`, `.env.example`); SearXNG is active only when `SEARXNG_URL` is set. Setups that relied on `http://localhost:8888` must set it explicitly.
- **Breaking:** `SEARXNG_URL` must be an http(s) URL without embedded credentials (`https://user:pw@host` and scheme-less values are rejected with a warning); use `SEARXNG_USERNAME`/`SEARXNG_PASSWORD` instead, both or neither.
- **Breaking:** unset `SEARCH_RESULT_FIELDS` now returns the normalized fields `title,url,content,publishedDate,providers`; the raw SearXNG payload passthrough ends, so fields such as `engine`, `score`, `suggestions`, `answers` are gone. Add `providers` to an existing `SEARCH_RESULT_FIELDS` to show attribution.
- **Breaking:** the CLI "Related searches" line (from SearXNG `suggestions`) is removed.
- Search errors are short per-provider reasons without secrets, URLs or response bodies (a SearXNG non-401 status no longer includes the response body).
- The Docker image is based on `python:3.14-slim` instead of `python:3.11-slim`.
- README rewritten around a demo, one-line agent setup and a comparison; installation, MCP server, CLI and Python API reference moved to `docs/usage/`.
- HTTP 429 from a search provider is retried once when `Retry-After` is at most 5 s and attempts remain (MCP `max_retries`; the CLI makes a single attempt and never retries). Otherwise the reason ends with `retry after Ns` or `try again later`.

### Fixed
- Pages could be captured mid-reload: the default config ran `window.location.reload()` in `js_code`, which Crawl4AI executes after `wait_for` without waiting for the new document. On docs.python.org this returned only `<head>` and failed as "Blocked by anti-bot protection". The reload now runs as a Playwright `after_goto` hook (`page.reload(wait_until="load")`), so `wait_for` and capture see the reloaded page. Custom configs and `js_code` overrides keep their previous behaviour (no reload).
- Content rendered into shadow DOM (e.g. MDN code examples) was missing from the markdown; `flatten_shadow_dom` is now enabled. Raises the minimum Crawl4AI version to 0.8.5, the first release with this option.
- Code samples lost `<` and `</` in the markdown: `PruningContentFilter` dropped Prism/highlight.js/CodeMirror token spans holding only those characters, so `<details>` became `details`. `<pre>`, `<code>` and CodeMirror's `.cm-content` are now exempt from pruning. Raises the minimum Crawl4AI version to 0.9.1, the first release with `preserve_tags`/`preserve_classes`.
- Every crawl failed with `CrawlerRunConfig.__init__() got an unexpected keyword argument 'flatten_shadow_dom'` when the code ran against Crawl4AI < 0.8.5 (e.g. a stale virtualenv). `flatten_shadow_dom` is now passed only if the installed Crawl4AI supports it; otherwise a warning is logged and shadow DOM content is skipped.
- Shadow DOM flattening corrupted pages whose text contains `<`, `>` or `&`: Crawl4AI's `flatten_shadow_dom.js` writes text nodes back unescaped, so text such as `<details>` was re-parsed as markup. Closing tags vanished from HTML code samples, and the broken tree defeated `target_elements`, pulling site navigation into the markdown (MDN: 38 kB with nav instead of 22 kB of article). The script is now patched at import to escape text nodes.

### Security
- nltk is no longer installed from `uv.lock` or in the Docker image. It has an unpatched advisory ([GHSA-8mgp-746c-j5xp](https://github.com/advisories/GHSA-8mgp-746c-j5xp), all versions up to 3.10.3) and comes in only through crawl4ai, which imports it in chunking and legacy helpers that searxNcrawl does not use. `pip`/`uvx` installs from PyPI still pull it in through crawl4ai's metadata; the affected functions are not called there either.

## [0.31.0] - 2026-10-09

### Added
- Zero-setup runs with `uvx`: `uvx --from git+https://github.com/DasDigitaleMomentum/searxNcrawl searxncrawl` starts the MCP server without a clone or virtualenv. (refs #14)
- Playwright's Chromium is installed automatically once per process before the first browser launch if it is missing (`python -m playwright install chromium`, idempotent; output goes to stderr so MCP stdio stays clean). Disable with `PLAYWRIGHT_AUTO_INSTALL=false`. (refs #14)
- `searxncrawl` console script as an alias for `crawl-mcp`, so the package name doubles as the MCP server command.

### Fixed
- Single-page crawls no longer time out on pages without a `<main>` element (e.g. example.com). The `wait_for` condition now accepts any `MAIN_SELECTORS` area (`article`, `[role='main']`, `.markdown-body`, …) with more than 50 characters and falls back to the page body after a 3 s grace period once the document has loaded, instead of waiting for the 30 s page timeout.

## [0.30.0] - 2026-07-15

### Added
- `--allowed-hosts` for configuring trusted HTTP `Host` headers when exposing the MCP server through Docker, a reverse proxy, or another remote deployment. Comma-separated values are normalized before being passed to FastMCP. (closes #25)
- Documented FastMCP's existing `FASTMCP_HTTP_ALLOWED_HOSTS` JSON-list environment setting as the environment-based alternative.

### Changed
- Raised the FastMCP minimum version from 2.0.0 to 3.4.3 so the declared dependency range guarantees support for the Host/Origin guard configuration used by searxNcrawl.
- `--cors-origins` now configures both FastMCP's request-time Origin allowlist and Starlette's CORS response middleware.

### Fixed
- Restored configurable remote HTTP access after FastMCP 3.4.3 introduced Host/Origin protection that rejected non-loopback Host headers with HTTP 421 when binding to `0.0.0.0`. Secure defaults remain active unless an allowlist is explicitly configured. (closes #25)

## [0.25.0] - 2026-07-03

### Added
- `SEARCH_RESULT_FIELDS` environment variable to control which fields are returned per search result (MCP + CLI). Default recommended value: `title,url,content,publishedDate`. Unset = all SearXNG fields (backward-compatible). Available fields: title, url, content, publishedDate, engine, score, category, img_src, thumbnail. (closes #23)
- `LOG_LEVEL` environment variable for MCP server log verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL). Controls both root logger and uvicorn/FastMCP log level via `mcp.run(log_level=...)`. Default: INFO. (closes #24)
- Version logging at MCP server startup (`searxNcrawl v0.25.0 starting`).

### Changed
- MCP `crawl()` default timeout reduced from 30s to 15s for faster feedback on unresponsive pages.
- README: corrected Docker Compose SearXNG documentation (SearXNG is not bundled, must be provided separately).

### Fixed
- `.env` is now loaded before logging configuration, enabling `LOG_LEVEL` to take effect at startup.

## [0.24.2] - 2026-05-29

### Changed
- Restructured README from 731 to 291 lines with Quick Start, feature matrix, and compact sections.
- Extracted MCP tool reference, output format details, and session capture guide to `docs/usage/`.
- Docker Compose promoted to first-class installation path with SearXNG included.

## [0.24.1] - 2026-05-28

### Fixed
- Corrected BFS→DFS documentation references in README, MCP tool docstring, CLI help text, and module docstring to match the actual `DFSDeepCrawlStrategy` implementation (closes #18).

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
