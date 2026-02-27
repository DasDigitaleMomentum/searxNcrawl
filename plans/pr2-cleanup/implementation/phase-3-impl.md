---
type: planning
entity: implementation-plan
plan: pr2-cleanup
phase: 3
status: draft
created: 2026-02-27
updated: 2026-02-27
---

# Implementation Plan: Phase 3 — Search Parity

> Implements [Phase 3](../phases/phase-3.md) of [pr2-cleanup](../plan.md)

## Approach

Extract the duplicated SearXNG search logic from `mcp_server.py` and `cli.py` into a new shared module `crawler/search.py`. This module exposes `search_async()` as the canonical search implementation plus a sync `search()` wrapper. A `SearchResult` dataclass captures the structured response. Both MCP and CLI are then refactored to delegate to the shared function, eliminating ~100 lines of duplicated httpx/param-building code. The CLI gains `--pageno`, and `crawler/__init__.py` re-exports the new public symbols.

The pattern follows the existing project convention: async function as the primary implementation (`crawl_page_async` pattern at `__init__.py:95`), sync wrapper via `asyncio.run` (`crawl_page` at `__init__.py:131`), slotted dataclass for structured results (`CrawledDocument` at `document.py:18`).

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| [crawler-core](../../docs/modules/crawler-core.md) | **create** | New `crawler/search.py` — shared search implementation with `SearchResult`, `SearchResultItem`, `search_async()`, `search()` |
| [crawler-core](../../docs/modules/crawler-core.md) | **modify** | `crawler/__init__.py` — add re-exports for `search_async`, `search`, `SearchResult`, `SearchResultItem` |
| [crawler-core](../../docs/modules/crawler-core.md) | **modify** | `crawler/mcp_server.py` — replace inline search logic with call to shared `search_async()` |
| [crawler-core](../../docs/modules/crawler-core.md) | **modify** | `crawler/cli.py` — replace `_run_search_async` internals with call to shared `search_async()`, add `--pageno` arg |
| tests | **create** | `tests/test_search.py` — unit tests for new search module |
| tests | **modify** | `tests/test_cli.py` — add test for `--pageno` argument parsing |

## Required Context

| File | Why |
|------|-----|
| `crawler/mcp_server.py:485-609` | Current MCP search implementation to extract |
| `crawler/cli.py:634-833` | Current CLI search implementation to refactor |
| `crawler/cli.py:89-119` | `_format_search_markdown()` — kept in CLI, consumes new `SearchResult` |
| `crawler/__init__.py:1-192` | Current public API surface and export patterns |
| `crawler/document.py:1-31` | Dataclass pattern to follow for `SearchResult` |
| `crawler/site.py:26-42` | `SiteCrawlResult` pattern — analogous compound result dataclass |
| `tests/test_cli.py:41-71` | Existing search markdown formatting tests |
| `tests/test_cli.py:430-435` | Existing `TestSearchMain` tests |
| `docs/features/searxng-search.md` | Documented behavior to preserve |

## Implementation Steps

### Step 1: Create `crawler/search.py` with dataclasses and core function

- **What**: Create a new module containing:
  1. `SearchResultItem` — a slotted dataclass for a single search result
  2. `SearchResult` — a slotted dataclass for the full search response
  3. `_get_searxng_client()` — moved from `mcp_server.py:490-504`
  4. `search_async()` — the canonical search implementation, extracted from `mcp_server.py:508-609`
  5. `search()` — sync wrapper
- **Where**: `crawler/search.py` (new file)
- **Why**: Eliminates duplication between MCP (`mcp_server.py:553-604`) and CLI (`cli.py:734-773`). Creates a reusable Python API.
- **Considerations**:
  - The SearXNG env vars (`SEARXNG_URL`, `SEARXNG_USERNAME`, `SEARXNG_PASSWORD`) are currently module-level constants in `mcp_server.py:58-60` and read at import time in `cli.py:727-729`. The new module should read them at call time (inside `search_async`) to support test injection and late `.env` loading. Use `os.getenv()` calls inside `_get_searxng_client()`.
  - Error handling: MCP currently returns JSON strings with `{"error": ...}`. The shared function should raise typed exceptions (`SearchError`), letting callers decide on formatting.
  - The `_get_searxng_client()` function can optionally accept `base_url`, `username`, `password` overrides for testability, falling back to env vars.

**Exact dataclass definitions:**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(slots=True)
class SearchResultItem:
    """A single search result from SearXNG."""
    title: str
    url: str
    content: str = ""
    engine: str = ""
    score: float = 0.0
    category: str = ""
    # Preserve any extra fields from SearXNG
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class SearchResult:
    """Structured response from a SearXNG search query."""
    query: str
    number_of_results: int
    results: List[SearchResultItem] = field(default_factory=list)
    answers: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    corrections: List[str] = field(default_factory=list)

class SearchError(Exception):
    """Raised when the SearXNG search fails."""
    def __init__(self, message: str, query: str = ""):
        self.query = query
        super().__init__(message)
```

**Exact function signatures:**

```python
async def search_async(
    query: str,
    *,
    language: str = "en",
    time_range: Optional[str] = None,
    categories: Optional[List[str]] = None,
    engines: Optional[List[str]] = None,
    safesearch: int = 1,
    pageno: int = 1,
    max_results: int = 10,
    searxng_url: Optional[str] = None,
    searxng_username: Optional[str] = None,
    searxng_password: Optional[str] = None,
) -> SearchResult:
    """Search the web using SearXNG metasearch engine.

    Args:
        query: Search query string (required).
        language: Language code (default: 'en').
        time_range: 'day', 'week', 'month', or 'year' (default: None).
        categories: List of categories (default: None = all).
        engines: List of engines (default: None = all).
        safesearch: 0=off, 1=moderate, 2=strict (default: 1).
        pageno: Page number (minimum 1, default: 1).
        max_results: Maximum results 1-50 (default: 10).
        searxng_url: Override SEARXNG_URL env var.
        searxng_username: Override SEARXNG_USERNAME env var.
        searxng_password: Override SEARXNG_PASSWORD env var.

    Returns:
        SearchResult with structured results.

    Raises:
        SearchError: On authentication failure, HTTP error, or network error.
    """
    ...

def search(
    query: str,
    *,
    language: str = "en",
    time_range: Optional[str] = None,
    categories: Optional[List[str]] = None,
    engines: Optional[List[str]] = None,
    safesearch: int = 1,
    pageno: int = 1,
    max_results: int = 10,
    searxng_url: Optional[str] = None,
    searxng_username: Optional[str] = None,
    searxng_password: Optional[str] = None,
) -> SearchResult:
    """Synchronous wrapper for search_async."""
    return asyncio.run(search_async(
        query, language=language, time_range=time_range,
        categories=categories, engines=engines, safesearch=safesearch,
        pageno=pageno, max_results=max_results,
        searxng_url=searxng_url, searxng_username=searxng_username,
        searxng_password=searxng_password,
    ))
```

**Key implementation detail** — `search_async` body:
- Build params dict (lines currently at `mcp_server.py:556-571`)
- Call `_get_searxng_client()` with optional overrides
- Execute GET `/search`, parse JSON response
- Convert raw dicts to `SearchResultItem` objects, mapping known fields explicitly and putting the rest in `extra`
- Truncate to `max_results`
- Return a `SearchResult` instance
- On `httpx.HTTPStatusError` 401: raise `SearchError("Authentication failed. Check SEARXNG_USERNAME and SEARXNG_PASSWORD.", query=query)`
- On `httpx.HTTPStatusError` other: raise `SearchError(f"SearXNG API error: {status} - {text}", query=query)`
- On `httpx.RequestError`: raise `SearchError(f"Request failed: {exc}", query=query)`

### Step 2: Update `crawler/__init__.py` to re-export search symbols

- **What**: Import and re-export `search_async`, `search`, `SearchResult`, `SearchResultItem`, and `SearchError` from `crawler.search`.
- **Where**: `crawler/__init__.py` — add imports near line 52, extend `__all__` at lines 54-76.
- **Why**: Acceptance criteria requires `from crawler import search_async, search, SearchResult` to work.
- **Considerations**: Follow the existing import pattern — direct imports at the top, listed in `__all__` grouped by category.

**Exact changes to `__all__`:**

Add after the `"SiteCrawlResult"` entry (line 58):

```python
# Search
"SearchResult",
"SearchResultItem",
"SearchError",
"search",
"search_async",
```

Add import line after the `.site` import (line 52):

```python
from .search import SearchError, SearchResult, SearchResultItem, search, search_async
```

### Step 3: Refactor MCP `search` tool to delegate to shared function

- **What**: Replace the inline httpx logic in `mcp_server.py:553-609` with a call to the shared `search_async()`, then `json.dumps()` the result for MCP output.
- **Where**: `crawler/mcp_server.py` — the `search()` MCP tool function (lines 508-609).
- **Why**: Eliminates the first copy of duplicated search logic. MCP tool becomes a thin adapter.
- **Considerations**:
  - The MCP tool must continue to return a JSON string (its current interface contract).
  - Error handling: catch `SearchError` and return `json.dumps({"error": str(e), "query": e.query})` to preserve the existing MCP error format.
  - Remove `_get_searxng_client()` from `mcp_server.py` (it moves to `search.py`).
  - Remove the `SEARXNG_URL`, `SEARXNG_USERNAME`, `SEARXNG_PASSWORD` constants from `mcp_server.py:58-60` (they are no longer needed there; the shared module reads env vars directly).
  - The `@mcp.tool` decorator and the docstring stay on the MCP function (important for MCP tool discovery).
  - Add `from .search import search_async as _search_async, SearchError` to MCP imports.

**Refactored MCP search tool body (approximately):**

```python
@mcp.tool
async def search(
    query: str,
    language: str = "en",
    time_range: Optional[str] = None,
    categories: Optional[List[str]] = None,
    engines: Optional[List[str]] = None,
    safesearch: int = 1,
    pageno: int = 1,
    max_results: int = 10,
):
    """<existing docstring preserved>"""
    LOGGER.info("Searching SearXNG for: %s", query)
    try:
        result = await _search_async(
            query,
            language=language,
            time_range=time_range,
            categories=categories,
            engines=engines,
            safesearch=safesearch,
            pageno=pageno,
            max_results=max_results,
        )
        LOGGER.info("Search returned %d results", result.number_of_results)
        # Convert to JSON dict matching current MCP output format
        return json.dumps({
            "query": result.query,
            "number_of_results": result.number_of_results,
            "results": [
                {
                    "title": item.title,
                    "url": item.url,
                    "content": item.content,
                    "engine": item.engine,
                    "score": item.score,
                    "category": item.category,
                    **item.extra,
                }
                for item in result.results
            ],
            "answers": result.answers,
            "suggestions": result.suggestions,
            "corrections": result.corrections,
        }, indent=2, ensure_ascii=False)
    except SearchError as exc:
        LOGGER.error(str(exc))
        return json.dumps({"error": str(exc), "query": query}, ensure_ascii=False)
```

**Note**: The MCP JSON output schema is preserved exactly — callers see identical JSON keys. The `**item.extra` spread ensures any additional SearXNG fields (e.g., `parsed_url`, `publishedDate`, `thumbnail`) pass through.

### Step 4: Add `--pageno` to CLI search and refactor to use shared function

- **What**:
  1. Add `--pageno` argument to `_parse_search_args()` (around `cli.py:696`, after `--max-results`).
  2. Replace the inline httpx logic in `_run_search_async()` (`cli.py:725-814`) with a call to the shared `search_async()`.
  3. Adapt `_format_search_markdown()` to accept a `SearchResult` object (or keep it accepting a dict — convert `SearchResult` to dict at the call site).
- **Where**: `crawler/cli.py` — functions `_parse_search_args` (lines 634-722), `_run_search_async` (lines 725-814).
- **Why**: Eliminates the second copy of duplicated search logic. Adds pagination support per acceptance criteria.
- **Considerations**:
  - `_format_search_markdown()` currently takes a `Dict[str, Any]`. Rather than refactoring all its callers and existing tests, the simplest approach is to convert `SearchResult` to a dict at the `_run_search_async` call site before passing to the formatter. Alternatively, add a `SearchResult.to_dict()` method.
  - Add a `to_dict()` method on `SearchResult` (and `SearchResultItem`) to facilitate both CLI formatting and JSON output, keeping the conversion centralized.
  - Remove the `httpx` import from `cli.py` if no other code in the file uses it (it is currently only used by `_run_search_async`). Actually — verify first; if `_run_crawl_async` or other code uses httpx, keep the import. Checking: `cli.py` imports `httpx` at line 16 and uses it only in `_run_search_async` (lines 753-764). After refactoring, `httpx` can be removed from `cli.py` imports.
  - Error handling: catch `SearchError` from the shared function and handle it the same way the CLI currently handles `httpx.HTTPStatusError` (log + return 1).

**`--pageno` argument addition:**

```python
parser.add_argument(
    "--pageno",
    type=int,
    default=1,
    help="Page number for results (default: 1)",
)
```

Insert after `--max-results` block (after line 701).

**`SearchResult.to_dict()` method:**

```python
def to_dict(self) -> Dict[str, Any]:
    """Convert to a JSON-serializable dictionary."""
    return {
        "query": self.query,
        "number_of_results": self.number_of_results,
        "results": [
            {
                "title": item.title,
                "url": item.url,
                "content": item.content,
                "engine": item.engine,
                "score": item.score,
                "category": item.category,
                **item.extra,
            }
            for item in self.results
        ],
        "answers": self.answers,
        "suggestions": self.suggestions,
        "corrections": self.corrections,
    }
```

**Refactored `_run_search_async` body:**

```python
async def _run_search_async(args: argparse.Namespace) -> int:
    """Main async entry point for search."""
    from .search import search_async, SearchError

    logging.info("Searching for: %s", args.query)
    try:
        result = await search_async(
            args.query,
            language=args.language,
            time_range=args.time_range,
            categories=args.categories,
            engines=args.engines,
            safesearch=args.safesearch,
            pageno=args.pageno,
            max_results=args.max_results,
        )
    except SearchError as exc:
        logging.error(str(exc))
        return 1

    logging.info("Found %d results", result.number_of_results)

    data = result.to_dict()
    if args.json_output:
        output = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        output = _format_search_markdown(data)

    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output)
        logging.info("Wrote results to %s", path)
    else:
        print(output)

    return 0
```

### Step 5: Write unit tests for `crawler/search.py`

- **What**: Create `tests/test_search.py` with comprehensive unit tests covering:
  1. `SearchResultItem` and `SearchResult` dataclass construction and defaults
  2. `SearchResult.to_dict()` round-trip fidelity
  3. `search_async()` — successful search (mocked httpx response)
  4. `search_async()` — parameter pass-through (categories, engines joined, time_range filtered)
  5. `search_async()` — `max_results` clamping (1-50)
  6. `search_async()` — `pageno` floor at 1
  7. `search_async()` — HTTP 401 raises `SearchError` with auth message
  8. `search_async()` — other HTTP errors raise `SearchError`
  9. `search_async()` — network errors raise `SearchError`
  10. `search()` sync wrapper works
  11. `search_async()` — env var override params (`searxng_url`, etc.)
- **Where**: `tests/test_search.py` (new file)
- **Why**: Phase deliverable requires unit tests for all new code.
- **Considerations**:
  - Mock `httpx.AsyncClient` using `unittest.mock.patch` + `AsyncMock`, following the existing test patterns in `tests/test_cli.py` (e.g., `AsyncMock` at line 10).
  - Use `pytest.mark.asyncio` for async tests (already in use — see `test_cli.py:439`).
  - Mock at `crawler.search.httpx.AsyncClient` to isolate from network.

### Step 6: Add CLI `--pageno` unit test

- **What**: Add test(s) to `tests/test_cli.py` verifying:
  1. `_parse_search_args(["query", "--pageno", "3"])` correctly parses `pageno=3`
  2. `_parse_search_args(["query"])` defaults `pageno` to `1`
- **Where**: `tests/test_cli.py` — add to or near `TestSearchMain` class (line 430).
- **Why**: Phase deliverable requires unit tests for the new CLI argument.
- **Considerations**: Follow existing `_parse_crawl_args` test patterns in the file.

### Step 7: Add E2E test for Python API search

- **What**: Add an E2E test that calls `search("test query")` against a live SearXNG instance and validates the `SearchResult` structure.
- **Where**: `tests/test_e2e.py` (create if doesn't exist; per phase-2 deliverable it should already exist).
- **Why**: Phase deliverable requires E2E test for Python API search.
- **Considerations**:
  - Mark with `@pytest.mark.e2e` so it can be skipped in CI without SearXNG.
  - If `test_e2e.py` doesn't exist yet (phase 2 is a prerequisite), create a minimal file with just the search E2E test. Phase 2 may add the file first.
  - Validate: `isinstance(result, SearchResult)`, `result.query == "test query"`, `len(result.results) > 0`, each item has `title` and `url`.

## Verify Command

```bash
pytest tests/test_search.py tests/test_cli.py tests/test_init.py tests/test_mcp_server.py -v
```

For E2E (requires running SearXNG):

```bash
pytest tests/test_e2e.py -m e2e -v
```

## Acceptance / Verification Checklist

- [ ] `search_async()` / `search()` are exported from `crawler/__init__.py` and usable via `from crawler import ...`
- [ ] CLI `--pageno` works and shared search implementation is used by CLI + MCP + Python API
- [ ] Search config/env lookup (`SEARXNG_URL`, `SEARXNG_USERNAME`, `SEARXNG_PASSWORD`) happens at call time, not via module-level frozen constants
- [ ] Tests include runtime-env behavior coverage (e.g., monkeypatch env between calls and verify updated values are honored)

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Unit | `SearchResult` / `SearchResultItem` dataclass construction | Fields populated correctly, defaults work |
| Unit | `SearchResult.to_dict()` | Returns dict matching current MCP JSON schema |
| Unit | `search_async()` success path (mocked httpx) | Returns `SearchResult` with correct items |
| Unit | `search_async()` parameter pass-through | Query params include categories, engines, time_range, pageno |
| Unit | `search_async()` runtime env lookup | Env updates between calls are honored without re-importing module |
| Unit | `search_async()` max_results clamping | Results list truncated to min(max(1, n), 50) |
| Unit | `search_async()` HTTP 401 | Raises `SearchError` with auth message |
| Unit | `search_async()` HTTP 500 | Raises `SearchError` with status message |
| Unit | `search_async()` network error | Raises `SearchError` with request message |
| Unit | `search()` sync wrapper | Returns same result as async version |
| Unit | CLI `--pageno` parsing | `args.pageno` correctly set |
| Unit | CLI `--pageno` default | `args.pageno == 1` |
| Integration | MCP search tool still returns valid JSON | Existing MCP tests pass (if any; currently none for search) |
| E2E | `search("test query")` against live SearXNG | Returns `SearchResult` with results |
| Regression | Existing baseline tests | All pass without modification |

## Rollback Strategy

All changes are additive (new file `crawler/search.py`, new tests) or refactoring (MCP/CLI delegate to shared function). Rollback steps:

1. Delete `crawler/search.py` and `tests/test_search.py`.
2. Revert changes to `crawler/__init__.py` (remove search imports/exports).
3. Revert `crawler/mcp_server.py` to restore inline search logic.
4. Revert `crawler/cli.py` to restore inline search logic and remove `--pageno`.
5. Revert any new tests in `tests/test_cli.py`.

Git: `git checkout HEAD~1 -- crawler/__init__.py crawler/mcp_server.py crawler/cli.py && git rm crawler/search.py tests/test_search.py`

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| SearchResult: dataclass vs TypedDict | dataclass (slots=True), TypedDict | dataclass (slots=True) | Matches project convention (`CrawledDocument`, `Reference`, `SiteCrawlResult` are all slotted dataclasses). Dataclass provides `__init__`, `__repr__`, and attribute access. |
| Error handling: exception vs error result | Raise `SearchError`, return `Optional[SearchResult]` with error field | Raise `SearchError` | Cleaner API — callers decide error format. MCP wraps in JSON, CLI logs and exits. Returning error-as-data would complicate the type signature. |
| Env var reading: import-time vs call-time | Module-level constants (current pattern), read inside function | Read inside function | Enables test isolation without monkeypatching module globals. Enables late `.env` loading (CLI's `_load_config()` runs before imports). |
| `_format_search_markdown` input | Refactor to accept `SearchResult`, keep accepting `Dict` | Keep accepting `Dict`, use `to_dict()` | Minimizes changes to existing tested function. Existing tests (`test_cli.py:41-71`) continue to pass unchanged. |
| Extra SearXNG result fields | Drop unknown fields, preserve in `extra` dict | Preserve in `extra` dict | SearXNG returns variable fields per engine (e.g., `publishedDate`, `thumbnail`, `img_src`). Dropping them loses data. `**item.extra` in `to_dict()` preserves them in JSON output for MCP backward compatibility. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/mcp_server.py:490-504` | `_get_searxng_client()` | This is the httpx client factory to extract. Uses `SEARXNG_URL`, basic auth. |
| `crawler/mcp_server.py:508-609` | `search()` MCP tool | Primary search implementation to extract. ~100 lines of param building, httpx call, error handling. |
| `crawler/mcp_server.py:556-561` | params dict | Confirms exact query params: `q`, `format`, `language`, `safesearch`, `pageno`. |
| `crawler/mcp_server.py:564-571` | conditional params | `time_range` validated against `("day", "week", "month", "year")`, categories/engines comma-joined. |
| `crawler/mcp_server.py:580-583` | result truncation | `max_results` clamped to 1-50, results sliced, `number_of_results` re-counted. |
| `crawler/mcp_server.py:587` | return format | `json.dumps(data, indent=2, ensure_ascii=False)` — the MCP JSON contract. |
| `crawler/mcp_server.py:58-60` | `SEARXNG_*` constants | Module-level env var reads. Will be removed from mcp_server, moved to search.py (read at call time). |
| `crawler/cli.py:634-722` | `_parse_search_args()` | CLI arg parser. Currently missing `--pageno`. All other params match MCP. |
| `crawler/cli.py:725-814` | `_run_search_async()` | Second copy of search logic. Reads env vars at lines 727-729. Duplicates httpx client creation and param building. |
| `crawler/cli.py:89-119` | `_format_search_markdown()` | CLI markdown formatter. Takes a dict with keys `query`, `results`, `suggestions`. Must remain compatible. |
| `crawler/__init__.py:54-76` | `__all__` | Current exports. New search symbols added here. |
| `crawler/__init__.py:95-128` | `crawl_page_async` | Pattern for async API function (keyword-only params, docstring, type hints). |
| `crawler/__init__.py:131-138` | `crawl_page` | Pattern for sync wrapper (`asyncio.run`). |
| `crawler/document.py:9-31` | `Reference`, `CrawledDocument` | Dataclass pattern: `@dataclass(slots=True)`, `field(default_factory=...)`. |
| `crawler/site.py:36-42` | `SiteCrawlResult` | Compound result dataclass pattern — lists + stats. Analog for `SearchResult`. |
| `tests/test_cli.py:41-71` | `TestFormatSearchMarkdown` | Tests for `_format_search_markdown`. These must continue to pass unchanged. |
| `tests/test_cli.py:430-435` | `TestSearchMain` | Minimal existing search CLI test. |
| `tests/test_cli.py:10` | `AsyncMock` import | Confirms test tooling available for mocking async functions. |

### Mismatches / Notes

- **Local `.env` with `SEARXNG_URL`**: A gitignored `.env` exists in the repo root containing `SEARXNG_URL` and `MCP_PORT`. The MCP server reads env vars at import time (`mcp_server.py:58-60`), the CLI reads at runtime via `os.getenv()`. The new `search.py` module reads at call time (inside `search_async`), which is correct — it picks up both direct env vars and late `.env` loading. E2E search tests work out of the box with the local `.env`.
- **No `--pageno` in CLI**: Confirmed at `cli.py:634-722` — the argument parser has no `--pageno`. The MCP tool does have `pageno` at `mcp_server.py:515`. This is the parity gap this phase closes.
- **CLI missing `pageno` in params**: The CLI's `_run_search_async()` at `cli.py:734-738` does not include `pageno` in the params dict at all (compare MCP's `mcp_server.py:561`). This means even if manually added to `params`, the SearXNG default (page 1) would be used.
- **No existing MCP search tests**: `tests/test_mcp_server.py` does not contain any search-related tests (confirmed via grep). The MCP refactoring should not break anything, but there are no existing assertions to verify against.
- **`_format_search_markdown` takes raw dict**: The function at `cli.py:89` operates on the raw SearXNG JSON dict shape (`data["query"]`, `data["results"]`, `data["suggestions"]`). The `SearchResult.to_dict()` method must produce this exact shape for backward compatibility.
- **`httpx` import in `cli.py`**: After refactoring, `httpx` (imported at `cli.py:16`) will no longer be used in `cli.py`. It should be removed to keep imports clean. Verify no other usage first — confirmed only `_run_search_async` uses it.
- **Regression target**: Plan requires the existing baseline test suite to continue passing. New tests may increase total count over time.
- **`test_e2e.py` does not exist yet**: Phase 2 is a prerequisite that should create this file. If phase 2 hasn't run, step 7 should create the file with proper pytest markers.
