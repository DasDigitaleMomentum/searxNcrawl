---
type: documentation
entity: feature
feature: "cli-commands-and-output"
version: 1.0
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

1. Module import invokes `_load_config` to populate environment variables.
2. Entrypoint (`main` or `search_main`) parses args and configures logging.
3. Async runner executes core operation (`_run_crawl_async` / `_run_search_async`).
4. Output helpers serialize docs/results as markdown or JSON and write destinations.
5. Process exits with status code indicating success, partial failure, or full failure.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-cli](../modules/crawler-cli.md) | `_load_config`, `_parse_crawl_args`, `_run_crawl_async`, `_parse_search_args`, `_run_search_async`, `_write_output`, `main`, `search_main` | End-to-end CLI behavior. |
| [crawler-package-api](../modules/crawler-package-api.md) | `crawl_page_async`, `crawl_pages_async`, `crawl_site_async` | Core crawl operations invoked by CLI. |
| [crawler-document-pipeline](../modules/crawler-document-pipeline.md) | `CrawledDocument` | Structured crawl output consumed by serializers. |

## Configuration

- `.env` search order:
  1. `./.env`
  2. `~/.config/searxncrawl/.env`
  3. Auto-copy from `.env.example` when available (`crawler/cli.py:24`-`crawler/cli.py:61`)
- Important env vars: `SEARXNG_URL`, `SEARXNG_USERNAME`, `SEARXNG_PASSWORD` (`crawler/cli.py:494`-`crawler/cli.py:496`).
- Packaging entrypoints: `crawl`, `search` scripts (`pyproject.toml:23`, `pyproject.toml:24`).

## Edge Cases & Limitations

- Site crawl mode accepts only one URL and exits with error otherwise (`crawler/cli.py:321`-`crawler/cli.py:323`).
- Non-JSON crawl output fails hard if all pages fail; JSON output can still emit failure payloads (`crawler/cli.py:365`-`crawler/cli.py:376`).
- Output target semantics vary by count/path suffix (single file vs directory mode) (`crawler/cli.py:170`-`crawler/cli.py:219`).

## Related Features

- [crawling-workflows](crawling-workflows.md)
- [site-crawling-bfs](site-crawling-bfs.md)
- [search-with-searxng](search-with-searxng.md)
