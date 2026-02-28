---
type: documentation
entity: module
module: "crawler-package-api"
version: 1.0
---

# Module: crawler-package-api

> Part of [searxNcrawl](../overview.md)

## Overview

This module documents the package-level public API surface in `crawler/__init__.py`, including synchronous/async crawl entry points and the lazy MCP server export.

### Responsibility

- Defines user-facing crawl functions for single-page, multi-page, and site crawls.
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

## Data Flow

1. Caller invokes one of the API entrypoints.
2. A run config is selected (`config` argument or `build_markdown_run_config`).
3. `AsyncWebCrawler.arun(...)` executes crawl operations.
4. First/single result is transformed through `build_document_from_result` (single-page path), while multi-page path aggregates per-URL outcomes.
5. Failures in batch mode are represented as `CrawledDocument(status="failed")` objects rather than hard failures.

## Configuration

- Optional runtime config injection via `config: Optional[CrawlerRunConfig]` (`crawler/__init__.py:88`, `crawler/__init__.py:130`).
- Concurrency control in batch crawling through `concurrency` and an `asyncio.Semaphore` (`crawler/__init__.py:131`, `crawler/__init__.py:146`).

## Inventory Notes

- **Coverage**: full
- **Notes**: Inventory is complete for `crawler/__init__.py` public API and lazy-load behaviors.
