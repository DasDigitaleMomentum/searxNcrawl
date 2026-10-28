---
type: documentation
entity: feature
feature: "cli-commands-and-output"
version: 1.1
---

# Feature: cli-commands-and-output

> Part of [searxNcrawl](../overview.md)

## Summary

This feature provides local command-line operation for crawl and search workflows, including environment auto-loading, argument validation, and flexible output routing to stdout/files/directories.

## How It Works

### User Flow

1. User runs `crawl ...` or `search ...` after package installation.
2. CLI loads config from local `.env` or user config directory fallback.
3. CLI executes crawl/search operation based on parsed options.
4. Results are printed or saved according to `-o/--output`, format flags, and mode.

### Technical Flow

1. Module import invokes shared `crawler.env.load_config()` to populate environment variables.
2. Entrypoint (`main` or `search_main`) parses args and configures logging.
3. Async runner executes core operation (`_run_crawl_async` / `_run_search_async`).
4. Output helpers serialize docs/results as markdown or JSON and write destinations.
5. Crawl exits 0 if any page succeeds, including partial failures; all failed pages exit 1. Search exits 0 for returned results and 1 for provider errors; interrupt exits 130.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-cli](../modules/crawler-cli.md) | `_parse_crawl_args`, `_run_crawl_async`, `_parse_search_args`, `_run_search_async`, `_write_output`, `main`, `search_main` | End-to-end CLI behavior. |
| [crawler-env](../modules/crawler-env.md) | `load_config` | Shared `.env` loading with CWD → config-dir fallback. |
| [crawler-package-api](../modules/crawler-package-api.md) | `crawl_page_async`, `crawl_pages_async`, `crawl_site_async` | Core crawl operations invoked by CLI. |
| [crawler-document-pipeline](../modules/crawler-document-pipeline.md) | `CrawledDocument` | Structured crawl output consumed by serializers. |

## Configuration

- `.env` search order (implemented in shared `crawler/env.py`, used by both CLI and MCP server):
  1. `./.env`
  2. `~/.config/searxncrawl/.env`
  3. Auto-copy from `.env.example` when available (`crawler/env.py`)
- Important env vars for `search`: `SEARXNG_URL`, `SEARXNG_USERNAME`, `SEARXNG_PASSWORD`, `SEARXNG_EXTRA_HEADERS`, `YDC_API_KEY`, `SEARCH_RESULT_FIELDS` (read by `crawler.search_orchestrator`).
- Packaging entrypoints: `crawl`, `crawl-capture`, `search`; native MCP aliases `crawl-mcp` and `searxncrawl` (`pyproject.toml`).
- `searxncrawl setup` configures detected coding agents with a native STDIO registration; [installation](../usage/installation.md).

## Edge Cases & Limitations

- Site crawl mode accepts only one URL and exits with error otherwise (`crawler/cli.py`).
- Non-JSON crawl output fails hard if all pages fail; JSON output can still emit failure payloads (`crawler/cli.py`).
- Output target semantics vary by count/path suffix (single file vs directory mode) (`crawler/cli.py`).
- `search` depends on the configured external providers (SearXNG and/or You.com); with none configured, or when all selected providers fail, it logs the error and exits with code 1.

## Related Features

- [crawling-workflows](crawling-workflows.md)
- [site-crawling-bfs](site-crawling-bfs.md)
- [search-with-searxng](search-with-searxng.md)
