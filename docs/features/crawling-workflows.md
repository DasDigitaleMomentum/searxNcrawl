---
type: documentation
entity: feature
feature: "crawling-workflows"
version: 1.1
---

# Feature: crawling-workflows

> Part of [searxNcrawl](../overview.md)

## Summary

This feature provides single-page and multi-page web crawling that returns normalized `CrawledDocument` results and can be surfaced through both CLI and MCP interfaces in markdown or JSON form.

## How It Works

### User Flow

1. User provides one URL (single crawl) or multiple URLs (batch crawl).
2. User chooses interface: Python API, CLI (`crawl`), or MCP tool (`crawl`).
3. System crawls pages, extracts markdown, and returns either markdown or structured JSON.
4. Optional link-removal post-processing can strip URLs from output text.

### Technical Flow

1. Interface layer dispatches to `crawl_page_async` or `crawl_pages_async`.
2. Default `CrawlerRunConfig` is produced by `build_markdown_run_config` when caller does not pass custom config.
3. Crawl4AI `AsyncWebCrawler` executes requests.
4. `build_document_from_result` normalizes result objects into `CrawledDocument`.
5. Output adapters (`_write_output` in CLI / `_format_output` in MCP) render markdown/json and apply optional link stripping.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-package-api](../modules/crawler-package-api.md) | `crawl_page_async`, `crawl_pages_async`, `crawl_page`, `crawl_pages` | Core crawl orchestration APIs. |
| [crawler-config](../modules/crawler-config.md) | `build_markdown_run_config`, `build_markdown_generator` | Crawl defaults and markdown tuning. |
| [crawler-document-pipeline](../modules/crawler-document-pipeline.md) | `build_document_from_result`, `CrawledDocument`, `parse_references` | Normalized conversion and reference extraction. |
| [crawler-cli](../modules/crawler-cli.md) | `_run_crawl_async`, `_write_output`, `_strip_markdown_links` | CLI command path and output persistence. |
| [crawler-mcp-server](../modules/crawler-mcp-server.md) | `crawl`, `_format_output`, `_strip_markdown_links` | MCP tool path and response formatting. |

## Configuration

- CLI options: `--concurrency`, `--json`, `--remove-links` (`crawler/cli.py`).
- MCP tool arguments: `concurrency`, `output_format`, `remove_links` (`crawler/mcp_server.py`).
- Runtime crawl behavior comes from `build_markdown_run_config` in `crawler/config.py`.
- Async Python APIs accept `timeout` (default 30 s per URL); MCP `crawl` defaults to 15 s. CLI and sync Python wrappers use the core default.
- CLI and MCP expose `dedup_mode` / `--dedup-mode` (`exact` default, `off` disables section removal), plus `storage_state` / `--storage-state` for existing authentication state.
- `--links-only` is a crawl CLI output option; it is mutually exclusive with `--remove-links`.

## Edge Cases & Limitations

- Batch crawl captures per-URL failures as failed documents instead of raising global exceptions (`crawler/__init__.py`).
- Single-page crawl raises `ValueError` when crawler returns empty results (`crawler/__init__.py`).
- Default configs reload HTTP(S) pages once before readiness checks; custom non-empty `js_code` overrides disable that hook.
- Deduplication uses normalized sections within each document, not across pages; guardrails warn without restoring removed content.
- Link stripping is regex-based and may remove URL-like text aggressively in some markdown contexts (`crawler/cli.py`, `crawler/mcp_server.py`).

## Related Features

- [site-crawling-bfs](site-crawling-bfs.md)
- [cli-commands-and-output](cli-commands-and-output.md)
- [mcp-tools-and-transports](mcp-tools-and-transports.md)
