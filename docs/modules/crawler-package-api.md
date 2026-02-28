---
type: documentation
entity: module
module: "crawler-package-api"
version: 1.0
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
| `crawler-config` | module | Supplies default `CrawlerRunConfig` and override model (`crawler/__init__.py:43`). |
| `crawler-document-pipeline` | module | Supplies data models and result conversion target types (`crawler/__init__.py:44`). |
| `crawler-site-crawl` | module | Re-exports site crawl APIs and result container (`crawler/__init__.py:45`). |
| `crawler.mcp_server` | module | Lazy-loaded MCP server object via `get_mcp_server` and `__getattr__` (`crawler/__init__.py:69`, `crawler/__init__.py:77`). |
| `crawl4ai.AsyncWebCrawler` | library | Runtime engine for page crawling (`crawler/__init__.py:40`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/__init__.py` | file | Package entrypoint and public API for crawling. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `__all__` | const | public | `crawler/__init__.py:47` | Declares supported package API exports for consumers/import tooling. |
| `get_mcp_server` | function | public | `crawler/__init__.py:69` | Returns MCP server instance via lazy import. |
| `__getattr__` | function | internal | `crawler/__init__.py:77` | Implements lazy `mcp` attribute loading and explicit attribute error behavior. |
| `crawl_page_async` | function | public | `crawler/__init__.py:85` | Crawls one URL and returns one `CrawledDocument`, raising when no result is returned. |
| `crawl_page` | function | public | `crawler/__init__.py:118` | Sync wrapper around `crawl_page_async` using `asyncio.run`. |
| `crawl_pages_async` | function | public | `crawler/__init__.py:127` | Concurrent crawl orchestration for multiple URLs with per-task error capture into failed docs. |
| `crawl_pages` | function | public | `crawler/__init__.py:166` | Sync wrapper around `crawl_pages_async`. |
| `CaptureResult` | dataclass | public | `crawler/session_capture.py` | Explicit capture outcome contract (`success`/`timeout`/`abort`). |
| `capture_session_async` | function | public | `crawler/session_capture.py` | Async isolated capture flow producing storage-state output when successful. |
| `capture_session` | function | public | `crawler/session_capture.py` | Sync wrapper around `capture_session_async`. |

## Data Flow

1. Caller invokes one of the API entrypoints.
2. A run config is selected (`config` argument or `build_markdown_run_config`).
3. `AsyncWebCrawler.arun(...)` executes crawl operations.
4. First/single result is transformed through `build_document_from_result` (single-page path), while multi-page path aggregates per-URL outcomes.
5. Failures in batch mode are represented as `CrawledDocument(status="failed")` objects rather than hard failures.
6. Session capture follows a separate flow and returns explicit capture statuses without altering crawl runtime defaults.

## Configuration

- Optional runtime config injection via `config: Optional[CrawlerRunConfig]` (`crawler/__init__.py:88`, `crawler/__init__.py:130`).
- Concurrency control in batch crawling through `concurrency` and an `asyncio.Semaphore` (`crawler/__init__.py:131`, `crawler/__init__.py:146`).

## Auth Semantics (Phase 1/2 MVP)

- Public crawl entrypoints accept `auth` input and resolve it through one canonical path: `resolve_auth(...)`.
- MVP contract supports `storage_state` only; unsupported keys raise resolver errors.
- CLI and MCP are expected to pass auth through to this API rather than duplicating validation.
- No-drift invariant: auth threading does not modify default crawl configuration behavior in `crawler/config.py`.

## Session Capture Semantics (Phase 3)

- Session capture is intentionally isolated from normal crawl execution (`crawl_page*`, `crawl_pages*`, `crawl_site*`).
- Completion/termination outcomes are explicit and deterministic (`success`, `timeout`, `abort`).
- Output overwrite is opt-in to avoid accidental replacement of credential-bearing files.

## Inventory Notes

- **Coverage**: full
- **Notes**: Inventory is complete for `crawler/__init__.py` public API and lazy-load behaviors.
