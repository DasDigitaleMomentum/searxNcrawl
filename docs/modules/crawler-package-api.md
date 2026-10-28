---
type: documentation
entity: module
module: "crawler-package-api"
version: 1.1
---

# Module: crawler-package-api

> Part of [searxNcrawl](../overview.md)

## Overview

This module documents the package-level public API surface in `crawler/__init__.py`, including synchronous/async crawl entry points, isolated session-capture helpers, and the lazy MCP server export.

### Responsibility

- Defines user-facing crawl functions for single-page, multi-page, and site crawls.
- Defines user-facing isolated session-capture helpers for generating `storage_state` files.
- Exposes primary datatypes and config helpers through `__all__`.
- Provides lazy access to the MCP server object to avoid hard dependency loading until needed.

Out of scope: CLI argument parsing, MCP tool definitions, and deep crawl strategy internals.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| `crawler-config` | module | Supplies default `CrawlerRunConfig` and override model (`crawler/__init__.py`). |
| `crawler-document-pipeline` | module | Supplies data models and result conversion target types (`crawler/__init__.py`). |
| `crawler-site-crawl` | module | Re-exports site crawl APIs and result container (`crawler/__init__.py`). |
| `crawler.mcp_server` | module | Lazy-loaded MCP server object via `get_mcp_server` and `__getattr__` (`crawler/__init__.py`). |
| `crawl4ai.AsyncWebCrawler` | library | Runtime engine for page crawling (`crawler/__init__.py`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/__init__.py` | file | Package entrypoint and public API for crawling. |
| `crawler/auth.py` | file | Storage-state path and JSON-object validation shared by all crawl surfaces. |
| `crawler/browser_setup.py` | file | Chromium installation and concurrent/repeated-loop protection. |
| `crawler/session_capture.py` | file | Isolated browser login capture and existing-context CDP export. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `__all__` | const | public | `crawler/__init__.py` | Declares supported package API exports for consumers/import tooling. |
| `get_mcp_server` | function | public | `crawler/__init__.py` | Returns MCP server instance via lazy import. |
| `__getattr__` | function | internal | `crawler/__init__.py` | Implements lazy `mcp` attribute loading and explicit attribute error behavior. |
| `crawl_page_async` | function | public | `crawler/__init__.py` | Crawls one URL and returns one `CrawledDocument`, raising when no result is returned. |
| `crawl_page` | function | public | `crawler/__init__.py` | Sync wrapper around `crawl_page_async` using `asyncio.run`. |
| `crawl_pages_async` | function | public | `crawler/__init__.py` | Concurrent crawl orchestration for multiple URLs with per-task error capture into failed docs. |
| `crawl_pages` | function | public | `crawler/__init__.py` | Sync wrapper around `crawl_pages_async`. |
| `crawl_site_async`, `crawl_site` | functions | public | `crawler/__init__.py` | Package wrappers forwarding site-crawl options to `crawler.site`. |
| `_extract_first_result` | function | internal | `crawler/__init__.py` | Accepts single results, containers, lists and async generators. |
| `DEFAULT_PAGE_TIMEOUT` | const | public | `crawler/__init__.py` | Default 30-second per-page crawl timeout. |
| `AuthConfig`, `AuthConfigError`, `ResolvedAuth`, `AuthInput`, `resolve_auth` | types/function | public | `crawler/auth.py` | Resolve the supported `storage_state` input; only `AuthConfig` is listed in the package `__all__`. |
| `BrowserSetupError`, `auto_install_enabled`, `ensure_chromium` | type/functions | public | `crawler/browser_setup.py` | Install Chromium once per process, or skip when automatic installation is disabled. |
| `CdpSessionEntry`, `list_cdp_sessions_async`, `export_cdp_storage_state_async` | type/functions | public | `crawler/session_capture.py` | Inspect a running CDP browser and export a selected context; import from this submodule. |
| `SessionCaptureError`, `SessionCaptureConfigError` | types | public | `crawler/session_capture.py` | Capture runtime and validation errors. |
| `CaptureResult` | dataclass | public | `crawler/session_capture.py` | Explicit capture outcome contract (`success`/`timeout`/`abort`). |
| `capture_session_async` | function | public | `crawler/session_capture.py` | Async isolated capture flow producing storage-state output when successful. |
| `capture_session` | function | public | `crawler/session_capture.py` | Sync wrapper around `capture_session_async`. |

## Data Flow

1. Caller invokes one of the API entrypoints.
2. A run config is selected (`config` argument or `build_markdown_run_config`).
3. `ensure_chromium` prepares the browser; default configs receive the awaited reload hook before `AsyncWebCrawler.arun(...)` executes.
4. First/single result is transformed through `build_document_from_result` (single-page path), while multi-page path aggregates per-URL outcomes.
5. Failures in batch mode are represented as `CrawledDocument(status="failed")` objects rather than hard failures.
6. Session capture follows a separate flow and returns explicit capture statuses without altering crawl runtime defaults.

## Configuration

- Optional runtime config injection via `config: Optional[CrawlerRunConfig]` (`crawler/__init__.py`).
- Concurrency control in batch crawling through `concurrency=3` and an `asyncio.Semaphore` (`crawler/__init__.py`).

## Auth Semantics

- Public crawl entrypoints accept `auth` input and resolve it through one canonical path: `resolve_auth(...)`.
- Contract supports `storage_state` only; unsupported keys, missing/unreadable paths, invalid JSON and non-object JSON raise resolver errors. Paths expand `~` and resolve relative to the current working directory.
- CLI and MCP are expected to pass auth through to this API rather than duplicating validation.
- Storage state is passed into `BrowserConfig`; crawl extraction settings still come from `crawler/config.py`.

## Session Capture Semantics

- Session capture is intentionally isolated from normal crawl execution (`crawl_page*`, `crawl_pages*`, `crawl_site*`).
- Completion/termination outcomes are explicit and deterministic (`success`, `timeout`, `abort`).
- Output overwrite is opt-in to avoid accidental replacement of credential-bearing files.
- Existing Chromium contexts can be listed/exported through the CDP submodule helpers; [session-capture usage](../usage/session-capture.md).

## Inventory Notes

- **Coverage**: best-effort
- **Notes**: Package exports and entrypoints are covered; auth/browser/capture support lists its public types and functions, omitting private helpers.
- `timeout` is exposed only by async crawl APIs: 30 s per page, 120 s per site by default. Sync wrappers use those defaults.
- `PLAYWRIGHT_AUTO_INSTALL` defaults to enabled; `0`, `false`, `no` or `off` disable it. Browser install progress goes to stderr. Default download does not install Linux system libraries.
