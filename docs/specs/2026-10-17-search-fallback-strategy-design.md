# Search Fallback Strategy: Design

Status: **planned**, design approved on 2026-10-17, not implemented yet. Nothing described here is available in a release until the implementation PR is merged.

## Goal

Close the searxncrawl.io comparison row "Fallback when a source fails" (open source today: "Partly: the other provider still answers"; Cloud: "Planned: Automatic") for open source and Cloud:

1. **Transparency (C):** a search response says which providers failed and why. Today failures only reach the server log.
2. **Primary with fallback (A):** an opt-in strategy that queries providers one after another and stops at the first with results, so the paid provider (You.com) is only used when the free one (SearXNG) fails.
3. **Empty counts as failure (D):** a provider that returns zero results triggers the fallback like an error (SearXNG often returns nothing when its engines are blocked).

## Non-goals

- Fallback for an explicit single-provider selection (B).
- Circuit breaker / skipping providers that failed recently (E).
- Topping up to `max_results` from further providers; a configurable result threshold.
- A server-wide fallback order variable.
- Changes to the provider calls, retries or timeouts.

## Current behaviour (`crawler/search_orchestrator.py`, v0.32)

- `search()` queries all selected providers in parallel (`asyncio.gather`) and merges with `_merge_results` (URL dedup, round-robin in the fixed order `searxng`, `youcom`, multi-provider results first).
- A provider exception is logged as a warning and skipped; if every provider raised, `SearchProviderError("All selected search providers failed: …")`.
- An empty provider result is a success.
- `_select_providers` reorders any explicit selection to the fixed order.
- `search()` is not part of the public Python API (not exported from `crawler/__init__.py`, not in `docs/usage/python-api.md`); callers are `mcp_server.search`, `cli._run_search_async` and tests.

## Decisions

| # | Decision |
|---|----------|
| 1 | Strategies `parallel` (default, today's behaviour) and `fallback` (opt-in). |
| 2 | Strategy from the call (`strategy`), else env `SEARCH_STRATEGY`, else `parallel`. Value is trimmed and case-insensitive; unset or empty means `parallel`. |
| 3 | An unknown value (call or env) raises `SearchProviderError("Unknown search strategy: <value>")`; no silent default. |
| 4 | Fallback order: default `searxng` → `youcom`; an explicit `providers` list sets the order. Parallel keeps the fixed order. |
| 5 | Fallback advances only on an exception or zero results; a partial page (fewer than `max_results`) is accepted. |
| 6 | Response gets top-level `failed_providers: {provider: reason}` only when non-empty; otherwise the response is byte-identical to today. |
| 7 | If no provider returns results: all raised → the existing all-failed error; at least one returned empty → `results: []` plus `failed_providers`, no error. |
| 8 | Implementation approach: `search()` returns `SearchOutcome(results, failed_providers)` (one function, two strategies); no wrapper keeping the list return. |

## Interface

### Orchestrator

```python
@dataclass
class SearchOutcome:
    results: list[SearchResult]
    failed_providers: dict[str, str]  # provider -> sanitized reason, in query order


async def search(
    query: str,
    *,
    language: str = "en",
    time_range: Optional[str] = None,
    categories: Optional[list[str]] = None,
    engines: Optional[list[str]] = None,
    safesearch: int = 1,
    pageno: int = 1,
    max_results: int = 10,
    max_retries: int = 3,
    providers: Optional[Sequence[str] | str] = None,
    strategy: Optional[str] = None,
) -> SearchOutcome
```

`_select_providers(configured, providers, *, keep_order: bool = False)`: with `keep_order=True` an explicit selection keeps its order; default and `keep_order=False` behave as today.

### Serializer

`serialize_search_results(query, results, documents=None, failed_providers=None)` adds `"failed_providers"` after `"results"` when the dict is non-empty. `SEARCH_RESULT_FIELDS` filters result fields only and never removes it.

```json
{
  "query": "…",
  "number_of_results": 10,
  "results": [ … ],
  "failed_providers": {"searxng": "request failed"}
}
```

### MCP tool `search`

New parameter `strategy: Optional[str] = None` (after `include_content`), documented in the docstring and the server `instructions`. Errors (unknown strategy, all failed) keep the `{"error", "query"}` JSON.

### CLI `search`

`--strategy {parallel,fallback}` (default: env, else parallel). Markdown output adds, below `_Found N results_`:

```
_Failed providers: searxng (request failed), youcom (no results)_
```

`--json` includes `failed_providers`. Unknown strategy from env → exit code 1 with the error logged.

### Reasons

Existing sanitized `SearchProviderError` texts (e.g. `request failed`, `API key rejected, check YDC_API_KEY`, `rate limit exceeded, retry after 30s`), `unexpected error` for other exceptions (class name only in the log, as today), and `no results` for an empty provider result. Never exception messages from httpx, URLs, headers or keys.

## Flow

Classification per provider call: exception → `failed_providers[p] = reason`; empty list → `failed_providers[p] = "no results"`; otherwise success.

### `parallel`

1. Query all selected providers with `asyncio.gather(..., return_exceptions=True)`, fixed order.
2. Classify each outcome; merge the non-empty successes with `_merge_results` (unchanged).
3. If every provider raised → `SearchProviderError("All selected search providers failed: " + "; ".join(f"{p}: {reason}"))` (message unchanged).
4. Return `SearchOutcome(merged, failed_providers)`.

### `fallback`

1. Order: explicit `providers` order, else `searxng`, `youcom` (`keep_order=True`).
2. For each provider in order: await its call; classify. On success: `results = _merge_results([(provider, hits)], max_results)` (same cap, dedup and `providers` attribution as parallel), stop. Log `INFO fallback: <p> failed (<reason>), trying <next>` before moving on.
3. Providers after the winner are not queried and not listed.
4. No winner: all raised → the all-failed error; otherwise `SearchOutcome([], failed_providers)`.
5. One selected provider: same result as `parallel`.

### Consequences

- Fallback latency adds up: a SearXNG timeout costs up to `max_retries` × 30 s plus backoff before You.com is asked (MCP default 3 attempts, CLI 1).
- You.com pages beyond 10 return no results without a request → `no results`.
- Cancelling the call cancels the provider call in progress (sequential `await`).
- Logs stay on stderr.

## Error handling

| Situation | parallel | fallback |
|-----------|----------|----------|
| All providers succeed with hits | merged results, no `failed_providers` | first provider's results |
| One raises, other has hits | other's results + `failed_providers` | next provider's results + `failed_providers` |
| One empty, other has hits | results + `{p: "no results"}` | next provider's results + `{p: "no results"}` |
| All raise | `SearchProviderError` (unchanged) | `SearchProviderError` (unchanged) |
| Mixed raise / empty, no hits | `[]` + `failed_providers` | `[]` + `failed_providers` |
| All empty | `[]` + all `no results` | `[]` + all `no results` |
| Unknown strategy | `SearchProviderError` before any request | same |

## Testing

Unit tests in `tests/test_search_orchestrator.py`, providers mocked via `_mock_providers` (no network):

- Strategy resolution: default, env, call overrides env, case and whitespace, unknown value from call and from env.
- Parallel: existing tests read `.results`; exception → `failed_providers`; empty → `no results`; all empty → `[]` without error; all raise → unchanged error.
- Fallback: first hits → second not called (call counter 0); first raises or empty → second wins, only first listed; explicit order `["youcom", "searxng"]`; all raise → error; mixed → `[]` + both reasons; single provider equals parallel.
- Serializer: no key without failures (output identical to today); key present with failures; `SEARCH_RESULT_FIELDS` keeps it; works with `include_content` documents.
- MCP and CLI: `strategy` / `--strategy` passed through; CLI Markdown line; unknown strategy → error JSON / exit 1.
- Security: a reason never contains the API key (exception text containing the key).

Live acceptance (local SearXNG + You.com with a real key; CLI and MCP over STDIO):

1. `parallel`, both providers: results as before, no `failed_providers`.
2. `fallback`, both providers: only SearXNG queried (log shows no You.com request).
3. `fallback`, SearXNG on a dead port: You.com answers, `failed_providers: {"searxng": "request failed"}`.
4. `parallel`, SearXNG dead: You.com results + `failed_providers`.
5. `fallback`, `providers=["youcom","searxng"]`: You.com first.
6. Unknown `SEARCH_STRATEGY`: error.

## Docs

`docs/usage/installation.md` (env table, provider behaviour paragraph), `docs/usage/mcp-tools.md`, `docs/usage/cli.md`, `docs/features/search-with-searxng.md`, `crawler/mcp_server.py` module docstring and `--help` epilog, `CHANGELOG.md` (`Added`). `server.json` and `mcpb/manifest.json` env vars at release time (AGENTS.md release step 1).

## Delivery

Branch `feat/search-fallback-strategy` stacked on `feat/search-include-content`, because the serializer signature above (`documents`) and the MCP/CLI `search` code come from the open `include_content` PRs (searxNcrawl#57 / searxNcrawl-cloud#8). PRs in `DasDigitaleMomentum/searxNcrawl` and `DasDigitaleMomentum/searxNcrawl-cloud` (OSS + Cloud feature) with base `feat/search-include-content`, so each diff shows only this feature; after #57 / #8 merge, retarget both to `main`.
