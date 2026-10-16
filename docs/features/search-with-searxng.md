---
type: documentation
entity: feature
feature: "search-with-searxng"
version: 1.0
---

# Feature: search-with-searxng

> Part of [searxNcrawl](../overview.md)

## Summary

This feature provides web search over a fixed set of providers, SearXNG and You.com, available through both CLI and MCP. Every configured provider is queried in parallel; the results are merged into one list in which each result names the providers that returned it. (The file name is kept for link stability.)

## How It Works

### User Flow

1. The operator configures at least one provider: `SEARXNG_URL` (optional basic auth) and/or `YDC_API_KEY`.
2. User invokes the `search` CLI command or MCP `search` tool with a query, optional filters and an optional provider subset (`--providers` / `providers`).
3. All selected providers are queried in parallel.
4. Results are merged, bounded to `max_results` and returned as markdown (CLI default, with a `**Sources:**` line per result) or JSON.
5. Optional (`include_content` / `--include-content`): every result page is crawled and its Markdown is added to the result.

### Technical Flow

1. `search_orchestrator.search()` resolves provider configuration from the environment at call time (`_resolve_provider_config`) and applies the optional subset (`_select_providers`).
2. One call per selected provider runs under `asyncio.gather`:
   - `_search_searxng`: GET `<SEARXNG_URL>/search` with `q`, `format=json`, `language`, `safesearch`, `pageno`, optional `time_range`, `categories`, `engines`; basic auth only when both credentials are set.
   - `_search_youcom`: POST `https://ydc-index.io/v1/search` with `X-API-Key`, the You.com User-Agent and a JSON body: `query`, `count`, `safesearch` (`off`/`moderate`/`strict`), optional `language` (mapped to You.com's language enum, falling back to the primary subtag, otherwise omitted), `freshness`, `offset` (pages 2–10; a page beyond 10 returns no results without a request). `content` falls back to the first non-empty snippet when the description is empty.
   - Both use `_request_json`: fixed 30 s timeout per attempt, retry with backoff on request errors (timeouts included). HTTP status errors are not retried, except one retry on 429 when `Retry-After` is at most 5 s and attempts remain; otherwise the 429 reason ends with `retry after Ns` or `try again later`.
3. `_merge_results` merges round-robin in the fixed order `searxng`, `youcom`, with conservative URL dedup; results from several providers come first.
4. With `include_content`, `crawl_result_pages` crawls every result URL through `crawl_pages_async` (concurrency 3, 15 s per page; Crawl4AI is imported only then).
5. `serialize_search_results` builds `{query, number_of_results, results}`, applies `SEARCH_RESULT_FIELDS` and, given crawled documents, adds `markdown` or `crawl_error` per result.
6. A failed provider is logged as a warning; if every selected provider fails, `SearchProviderError` lists one sanitized reason per provider.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| `crawler/search_orchestrator.py` | `search`, `SearchResult`, `SearchProviderError`, `ProviderConfig`, `configured_providers`, `_resolve_provider_config`, `_select_providers`, `_request_json`, `_search_searxng`, `_search_youcom`, `_merge_results`, `crawl_result_pages`, `serialize_search_results`, `_parse_search_result_fields` | Provider configuration and selection, provider calls, merge, shared serializer. |
| [crawler-cli](../modules/crawler-cli.md) | `_run_search_async`, `_parse_search_args`, `_format_search_markdown`, `search_main` | CLI search UX (single attempt per provider) and output formatting. |
| [crawler-mcp-server](../modules/crawler-mcp-server.md) | `search` | MCP search tool (`max_retries` per provider); returns the envelope or `{"error", "query"}` JSON. |

## Configuration

- Environment variables (read at call time):
  - `SEARXNG_URL` — enables SearXNG; must be an http(s) URL without embedded credentials; no default.
  - `SEARXNG_USERNAME`, `SEARXNG_PASSWORD` — optional basic auth, both or neither.
  - `YDC_API_KEY` — enables You.com (stripped; whitespace-only counts as unset). You.com queries go to You.com in the US.
  - `SEARCH_RESULT_FIELDS` — comma-separated subset of `title,url,content,publishedDate,providers`; unset/empty returns all of them.
- CLI options: `--language`, `--time-range`, `--safesearch`, `--categories`, `--engines` (the last two SearXNG only), `--max-results`, `--providers`.
- MCP parameters: `language`, `time_range`, `safesearch`, `categories`, `engines` (the last two SearXNG only), `pageno`, `max_results`, `max_retries`, `providers`.

## Edge Cases & Limitations

- No provider configured, an unknown provider name or an unconfigured provider in the subset returns an error (MCP `error` JSON, CLI exit code 1).
- A set-but-invalid `SEARXNG_URL` or a single SearXNG credential disables SearXNG with a warning that names the variable, never its value.
- Partial failure returns the remaining providers' results; total failure reports e.g. `searxng: request failed; youcom: API key rejected, check YDC_API_KEY`. Reasons never contain secrets, URLs or response bodies.
- SearXNG 401 maps to a hint to check `SEARXNG_USERNAME/SEARXNG_PASSWORD`; You.com maps 401 (key rejected), 403 (key lacks the required scope), 402 (credits exhausted), 429 (rate limit), other statuses as `HTTP <status>`. A 429 reason from either provider ends with `retry after Ns` (from `Retry-After`) or `try again later`.
- Result counts are constrained to `[1, 50]`. Raw SearXNG fields (`engine`, `score`, `suggestions`, …) are not returned.
- URL dedup is conservative (scheme/host case, default port, fragment); no re-ranking or score normalization.

## Related Features

- [mcp-tools-and-transports](mcp-tools-and-transports.md)
- [cli-commands-and-output](cli-commands-and-output.md)
