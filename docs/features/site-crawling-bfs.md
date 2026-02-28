---
type: documentation
entity: feature
feature: "site-crawling-bfs"
version: 1.0
---

# Feature: site-crawling-bfs

> Part of [searxNcrawl](../overview.md)

## Summary

This feature crawls a site from a seed URL using breadth-first strategy, enforcing depth/page limits and optional subdomain inclusion, then returns aggregated documents plus crawl statistics.

## How It Works

### User Flow

1. User submits a seed URL and crawl constraints (depth/pages/subdomains).
2. User runs through Python API (`crawl_site_async`/`crawl_site`), CLI (`crawl --site`), or MCP (`crawl_site`).
3. System crawls pages reachable under the configured policy.
4. User receives markdown or JSON output and summary stats.

### Technical Flow

1. `crawl_site_async` parses host and derives registrable domain.
2. Domain filters are built via `DomainFilter` and `FilterChain` as needed.
3. Base run config is augmented with `BFSDeepCrawlStrategy(max_depth, max_pages, filter_chain)`.
4. Crawl executes with `stream=False` due to documented BFS stream behavior.
5. Results are iterated using `_iterate_results` compatibility helper.
6. Each result is transformed to `CrawledDocument`, deduplicated, and aggregated into `SiteCrawlResult` with stats.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-site-crawl](../modules/crawler-site-crawl.md) | `crawl_site_async`, `SiteCrawlResult`, `_iterate_results`, `_registrable_domain` | Core BFS crawl logic and aggregation. |
| [crawler-config](../modules/crawler-config.md) | `build_markdown_run_config` | Baseline extraction config for pages discovered by BFS. |
| [crawler-document-pipeline](../modules/crawler-document-pipeline.md) | `build_document_from_result` | Converts raw crawl results into normalized docs. |
| [crawler-cli](../modules/crawler-cli.md) | `_run_crawl_async` | CLI dispatch for `--site` mode and reporting. |
| [crawler-mcp-server](../modules/crawler-mcp-server.md) | `crawl_site` | MCP tool wrapper and output formatting. |

## Configuration

- Core options: `max_depth`, `max_pages`, `include_subdomains` (`crawler/site.py:65`-`crawler/site.py:68`).
- CLI flags: `--site --max-depth --max-pages --include-subdomains` (`crawler/cli.py:266`, `crawler/cli.py:271`, `crawler/cli.py:277`, `crawler/cli.py:283`).
- MCP args mirror these options (`crawler/mcp_server.py:257`-`crawler/mcp_server.py:261`).

## Edge Cases & Limitations

- `stream=False` is intentionally forced due to a noted BFS streaming issue in crawl4ai (`crawler/site.py:103`-`crawler/site.py:113`).
- Deduplication uses `request_url`; semantic duplicates with different query parameters are treated as distinct URLs (`crawler/site.py:139`-`crawler/site.py:143`).
- Crawl scope relies on host/domain filtering; custom policies beyond this are not currently exposed.

## Related Features

- [crawling-workflows](crawling-workflows.md)
- [mcp-tools-and-transports](mcp-tools-and-transports.md)
