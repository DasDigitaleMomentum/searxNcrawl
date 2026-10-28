---
type: documentation
entity: module
module: "crawler-site-crawl"
version: 1.1
---

# Module: crawler-site-crawl

> Part of [searxNcrawl](../overview.md)

## Overview

`crawler/site.py` implements multi-page crawling via Crawl4AI DFS deep crawling with domain scoping, deduplication, and aggregated stats.

### Responsibility

- Accept seed URL + depth/page/subdomain limits.
- Configure deep-crawl strategy and domain filters.
- Execute crawl, normalize results, collect errors/stats, and return a stable `SiteCrawlResult`.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| `crawler-config` | module | Supplies base run config used before attaching DFS strategy (`crawler/site.py`). |
| `crawler-document-pipeline` | module | Converts each raw crawl item into `CrawledDocument` (`crawler/site.py`). |
| `crawl4ai.deep_crawling` | library | DFS strategy and filter-chain primitives (`crawler/site.py`). |
| `tldextract` | library | Registrable-domain extraction for include_subdomains behavior (`crawler/site.py`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/site.py` | file | Site crawl orchestration, result types, and result iteration compatibility helper. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `SiteCrawlOptions` | class | public | `crawler/site.py` | Option model for site crawling (currently informative alongside function params). |
| `SiteCrawlResult` | class | public | `crawler/site.py` | Aggregated site crawl output: documents, errors, stats. |
| `_normalize_host` | function | internal | `crawler/site.py` | Normalizes host casing and strips port for filtering. |
| `_registrable_domain` | function | internal | `crawler/site.py` | Cached registrable-domain extraction used by subdomain policy. |
| `crawl_site_async` | function | public | `crawler/site.py` | Main async DFS site crawl implementation with filter setup and result aggregation. |
| `crawl_site` | function | public | `crawler/site.py` | Sync wrapper around `crawl_site_async`. |
| `DEFAULT_SITE_TIMEOUT` | const | public | `crawler/site.py` | Default 120-second timeout around the deep-crawl operation. |
| `_iterate_results` | function | internal | `crawler/site.py` | Compatibility iterator supporting list/container/asyncgen/single-result return shapes. |

## Data Flow

1. Parse seed URL and derive host/registrable domain.
2. Build optional `DomainFilter`/`FilterChain` based on `include_subdomains`.
3. Build default run config, attach `DFSDeepCrawlStrategy`, and set `stream=False` to collect results before conversion.
4. Execute crawl with `AsyncWebCrawler.arun`.
5. Iterate heterogeneous result container via `_iterate_results`.
6. Convert each result to `CrawledDocument`, deduplicate by `request_url`, record failures.
7. Return `SiteCrawlResult` with aggregate stats.

## Configuration

- Function defaults: `max_depth=2`, `max_pages=25`, `include_subdomains=False`, `dedup_mode="exact"`, `auth=None`; `crawl_site_async` also accepts `timeout=None` (120 s).
- `SiteCrawlOptions` is informational; its `stream=True` field does not control execution.
- Internally sets `config.exclude_external_links = not include_subdomains` (`crawler/site.py`).
- Execution sets `config.stream = False`; results are buffered until the DFS crawl completes.
- Timeout returns no documents, one `crawl_timeout` error and zero-page stats; partial in-progress results are not returned.

## Inventory Notes

- **Coverage**: full
- **Notes**: Full coverage for `crawler/site.py`, including behavior notes embedded in code comments.
