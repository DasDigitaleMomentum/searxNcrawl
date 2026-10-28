---
type: documentation
entity: feature
feature: "site-crawling-bfs"
version: 1.1
---

# Feature: site-crawling-bfs

> Part of [searxNcrawl](../overview.md)

## Summary

- Crawls a site from a seed URL using depth-first search (DFS), with depth/page limits and optional subdomain inclusion.
- Returns documents, errors and crawl statistics; the file name remains stable for existing links.

## How It Works

### User Flow

1. User submits a seed URL and crawl constraints (depth/pages/subdomains).
2. User runs through Python API (`crawl_site_async`/`crawl_site`), CLI (`crawl --site`), or MCP (`crawl_site`).
3. System crawls pages reachable under the configured policy.
4. User receives markdown or JSON output and summary stats.

### Technical Flow

1. `crawl_site_async` parses host and derives registrable domain.
2. Domain filters are built via `DomainFilter` and `FilterChain` as needed.
3. Base run config is augmented with `DFSDeepCrawlStrategy(max_depth, max_pages, filter_chain)`.
4. Crawl executes with `stream=False` and a 120 s default overall crawl timeout.
5. Results are iterated using `_iterate_results` compatibility helper.
6. Each result is transformed to `CrawledDocument`, deduplicated, and aggregated into `SiteCrawlResult` with stats.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-site-crawl](../modules/crawler-site-crawl.md) | `crawl_site_async`, `SiteCrawlResult`, `_iterate_results`, `_registrable_domain` | Core DFS crawl logic and aggregation. |
| [crawler-config](../modules/crawler-config.md) | `build_markdown_run_config` | Baseline extraction config for pages discovered by DFS. |
| [crawler-document-pipeline](../modules/crawler-document-pipeline.md) | `build_document_from_result` | Converts raw crawl results into normalized docs. |
| [crawler-cli](../modules/crawler-cli.md) | `_run_crawl_async` | CLI dispatch for `--site` mode and reporting. |
| [crawler-mcp-server](../modules/crawler-mcp-server.md) | `crawl_site` | MCP tool wrapper and output formatting. |

## Configuration

- Core defaults: `max_depth=2`, `max_pages=25`, `include_subdomains=False`, `dedup_mode="exact"`, `auth=None`.
- Async Python API: `timeout=None` uses 120 s; MCP `timeout=120` must be at least 1 s. CLI and sync wrappers use the core default.
- CLI flags: `--site --max-depth --max-pages --include-subdomains` (`crawler/cli.py`).
- MCP args mirror these options (`crawler/mcp_server.py`).

## Edge Cases & Limitations

- Results are buffered with `stream=False`; pages are returned after the DFS crawl completes.
- An overall timeout returns zero documents and one `crawl_timeout` error; callers can inspect `SiteCrawlResult.errors` and stats.
- Deduplication uses `request_url`; semantic duplicates with different query parameters are treated as distinct URLs (`crawler/site.py`).
- Crawl scope relies on host/domain filtering; custom policies beyond this are not currently exposed.

## Related Features

- [crawling-workflows](crawling-workflows.md)
- [mcp-tools-and-transports](mcp-tools-and-transports.md)
