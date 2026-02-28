---
type: documentation
entity: module
module: "crawler-site-crawl"
version: 1.0
---

# Module: crawler-site-crawl

> Part of [searxNcrawl](../overview.md)

## Overview

`crawler/site.py` implements whole-site crawling via Crawl4AI BFS deep crawling with domain scoping, deduplication, and aggregated stats.

### Responsibility

- Accept seed URL + BFS options.
- Configure deep-crawl strategy and domain filters.
- Execute crawl, normalize results, collect errors/stats, and return a stable `SiteCrawlResult`.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| `crawler-config` | module | Supplies base run config used before attaching BFS strategy (`crawler/site.py:18`). |
| `crawler-document-pipeline` | module | Converts each raw crawl item into `CrawledDocument` (`crawler/site.py:17`). |
| `crawl4ai.deep_crawling` | library | BFS strategy and filter-chain primitives (`crawler/site.py:14`). |
| `tldextract` | library | Registrable-domain extraction for include_subdomains behavior (`crawler/site.py:12`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/site.py` | file | Site crawl orchestration, result types, and result iteration compatibility helper. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `SiteCrawlOptions` | class | public | `crawler/site.py:25` | Option model for site crawling (currently informative alongside function params). |
| `SiteCrawlResult` | class | public | `crawler/site.py:35` | Aggregated site crawl output: documents, errors, stats. |
| `_normalize_host` | function | internal | `crawler/site.py:43` | Normalizes host casing and strips port for filtering. |
| `_registrable_domain` | function | internal | `crawler/site.py:51` | Cached registrable-domain extraction used by subdomain policy. |
| `crawl_site_async` | function | public | `crawler/site.py:62` | Main async BFS site crawl implementation with filter setup and result aggregation. |
| `crawl_site` | function | public | `crawler/site.py:176` | Sync wrapper around `crawl_site_async`. |
| `_iterate_results` | function | internal | `crawler/site.py:194` | Compatibility iterator supporting list/container/asyncgen/single-result return shapes. |

## Data Flow

1. Parse seed URL and derive host/registrable domain.
2. Build optional `DomainFilter`/`FilterChain` based on `include_subdomains`.
3. Build default run config, attach `BFSDeepCrawlStrategy`, force `stream=False` for reliability.
4. Execute crawl with `AsyncWebCrawler.arun`.
5. Iterate heterogeneous result container via `_iterate_results`.
6. Convert each result to `CrawledDocument`, deduplicate by `request_url`, record failures.
7. Return `SiteCrawlResult` with aggregate stats.

## Configuration

- Function options: `max_depth`, `max_pages`, `include_subdomains` (`crawler/site.py:65`-`crawler/site.py:68`).
- Internally sets `config.exclude_external_links = not include_subdomains` (`crawler/site.py:114`).
- Hardcoded `config.stream = False` due to documented crawl4ai BFS behavior (`crawler/site.py:103`-`crawler/site.py:113`).

## Inventory Notes

- **Coverage**: full
- **Notes**: Full coverage for `crawler/site.py`, including behavior notes embedded in code comments.
