---
type: planning
entity: phase
plan: pr2-cleanup
phase: 3
status: pending
created: 2026-02-27
updated: 2026-02-27
---

# Phase 3: Search Parity

## Objective

Close the search parity gap by adding `search_async()` and `search()` convenience functions to the Python API, adding `--pageno` to the CLI, and writing comprehensive tests.

## Scope

### Includes

- **Python API** (`crawler/__init__.py`):
  - `search_async(query, *, language, time_range, categories, engines, safesearch, pageno, max_results) -> SearchResult`
  - `search(...)` sync wrapper
  - `SearchResult` dataclass (or TypedDict) for structured results
  - Export in `__all__`
- **CLI** (`crawler/cli.py`):
  - Add `--pageno` argument to search subcommand
  - Wire through to search execution
- **Core search module** (if needed):
  - Extract search logic from `mcp_server.py` into a reusable function (avoid duplication)
  - Both MCP and CLI should call the shared implementation
  - Resolve `SEARXNG_*` config/env values at call time (not module import time constants)
- **Tests**:
  - Unit tests for `search_async()` / `search()` (mocked httpx)
  - Unit test for CLI `--pageno`
  - E2E test for Python API search (in `test_e2e.py`)

### Excludes

- Auth for search (SearXNG basic auth already works via env vars — no change needed)
- Search result caching
- New search features beyond what MCP already supports

## Prerequisites

- [ ] Phase 2 completed (E2E infrastructure in place)
- [ ] Understanding of current search implementation in `mcp_server.py`

## Deliverables

- [ ] `search_async()` function in `crawler/__init__.py`
- [ ] `search()` sync wrapper in `crawler/__init__.py`
- [ ] `SearchResult` type exported from package
- [ ] `--pageno` CLI argument for search
- [ ] Shared search implementation (no logic duplication between MCP/CLI/API)
- [ ] Unit tests for all new code
- [ ] E2E test for Python API search

## Acceptance Criteria

- [ ] `from crawler import search_async, search, SearchResult` works
- [ ] `await search_async("test query")` returns structured results
- [ ] `search("test query")` (sync) returns same structure
- [ ] All SearXNG params supported: query, language, time_range, categories, engines, safesearch, pageno, max_results
- [ ] CLI: `crawl search --pageno 2 "test"` works
- [ ] MCP, CLI, and Python API all call the same underlying search function
- [ ] Search config/env resolution happens at call time to avoid stale env state and improve testability
- [ ] All existing + new tests pass

## Dependencies on Other Phases

| Phase | Dependency Type | Description                                      |
| ----- | --------------- | ------------------------------------------------ |
| 2     | Must complete   | E2E test infrastructure available for search test |

## Notes

- The search logic in `mcp_server.py` (lines 508-609) uses `httpx` to call SearXNG API. This should be extracted into a shared module (e.g., `crawler/search.py`) and called from MCP, CLI, and the new Python API.
- `SearchResult` should mirror the structure already returned by MCP: `query`, `number_of_results`, `results[]`, `answers[]`, `suggestions[]`, `corrections[]`.
- The CLI currently formats search results as markdown by default and JSON with `--json`. The Python API should always return structured data.
