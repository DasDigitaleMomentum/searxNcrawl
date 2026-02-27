---
type: documentation
entity: module
module: "tests"
version: 1.0
---

# Module: tests

> Part of [searxNcrawl](../overview.md)

## Overview

Comprehensive pytest test suite covering all modules in the `crawler/` package. Tests use `pytest-asyncio` for async test support and extensive mocking of crawl4ai and Playwright internals. Includes both unit tests and end-to-end integration tests.

### Responsibility

- **IS** responsible for: unit testing all public and internal functions, testing MCP tool registration, CLI argument parsing, auth configuration, capture flow, reference parsing, document building, site crawling, config factory functions, search module functions, and end-to-end integration testing (crawl, search, CLI, auth flows via `test_e2e.py`).
- **IS NOT** responsible for: real-world integration testing against live services (that's `scripts/test-realworld.sh`), or manual browser-based exploratory testing.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| pytest >= 8.0 | library | Test framework |
| pytest-asyncio >= 0.23 | library | Async test support (`asyncio_mode = "auto"`) |
| unittest.mock | stdlib | Mocking crawl4ai, Playwright, httpx, filesystem |
| crawler (all submodules) | module | Modules under test |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `tests/` | dir | Test files directory |
| `tests/test_init.py` | file | Tests for `crawler/__init__.py`: crawl_page, crawl_pages, __getattr__, get_mcp_server |
| `tests/test_auth.py` | file | Tests for `crawler/auth.py`: AuthConfig, build_browser_config, load_auth_from_env, load_auth_from_file, list_auth_profiles |
| `tests/test_builder.py` | file | Tests for `crawler/builder.py`: build_document_from_result, metadata extraction, failure handling, markdown regeneration |
| `tests/test_capture.py` | file | Tests for `crawler/capture.py`: capture_auth_state, URL matching, timeout, profile support, browser close detection |
| `tests/test_cli.py` | file | Tests for `crawler/cli.py`: argument parsing, crawl execution, search execution, capture-auth, output formatting, auth CLI flags |
| `tests/test_config.py` | file | Tests for `crawler/config.py`: RunConfigOverrides, build_markdown_run_config, build_discovery_run_config, cache mode conversion |
| `tests/test_document.py` | file | Tests for `crawler/document.py`: CrawledDocument and Reference dataclass construction |
| `tests/test_mcp_server.py` | file | Tests for `crawler/mcp_server.py`: MCP tool registration, crawl/crawl_site/search tools, output formatting, auth integration |
| `tests/test_references.py` | file | Tests for `crawler/references.py`: parse_references, markdown block parsing, link fallback |
| `tests/test_search.py` | file | Tests for `crawler/search.py`: search_async, search, SearchResult, SearchResultItem, SearchError, client creation |
| `tests/test_site.py` | file | Tests for `crawler/site.py`: crawl_site_async, domain filtering, result iteration, deduplication |
| `tests/test_coverage_extra.py` | file | Additional edge-case tests to fill coverage gaps |
| `tests/test_coverage_gaps.py` | file | Targeted tests for remaining uncovered code paths |
| `tests/test_e2e.py` | file | End-to-end integration tests: crawl, search, CLI, auth flows (marked `e2e`) |

## Key Symbols

Test files follow the pattern `test_<module>.py` with test functions named `test_<scenario>`. Key test classes/functions are not individually listed here as they mirror the module symbols in [crawler-core](crawler-core.md). The test structure is 1:1 with source modules.

## Data Flow

Tests are run via `pytest` from the repository root. Configuration is in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

All async test functions are automatically wrapped by pytest-asyncio. Mocking is used extensively to avoid real browser launches or network calls.

## Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| `asyncio_mode` | `auto` | Auto-detect and run async test functions |
| `testpaths` | `["tests"]` | Test discovery directory |

## Inventory Notes

- **Coverage**: full
- **Notes**: All 14 test files documented. The suite includes unit tests for every source module and E2E integration tests.
