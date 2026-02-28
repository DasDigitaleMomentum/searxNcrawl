---
type: documentation
entity: module
module: "crawler-document-pipeline"
version: 1.0
---

# Module: crawler-document-pipeline

> Part of [searxNcrawl](../overview.md)

## Overview

This module groups the internal data pipeline that turns raw Crawl4AI results into stable, tool-friendly documents with references and metadata.

### Responsibility

- Define core document/reference datatypes.
- Parse references from Crawl4AI markdown/link metadata.
- Transform `CrawlResult` into `CrawledDocument` for downstream CLI/MCP formatting.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| `crawler-config` | module | Reuses markdown generator for fallback markdown production (`crawler/builder.py:10`). |
| `crawl4ai.models` | library | Source result types (`CrawlResult`, `MarkdownGenerationResult`) (`crawler/builder.py:8`). |
| Python `re` | library | Reference-line parsing from markdown blocks (`crawler/references.py:5`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/document.py` | file | Dataclasses for normalized crawl output (`Reference`, `CrawledDocument`). |
| `crawler/references.py` | file | Reference parsing and fallback generation helpers. |
| `crawler/builder.py` | file | Core conversion logic from Crawl4AI results to internal docs. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `Reference` | class | public | `crawler/document.py:10` | Outgoing link representation with index/href/label. |
| `CrawledDocument` | class | public | `crawler/document.py:19` | Canonical crawl result container used across APIs, CLI, MCP. |
| `REFERENCE_LINE` | const | internal | `crawler/references.py:10` | Regex for parsing numbered reference markdown lines. |
| `parse_references` | function | public | `crawler/references.py:13` | Parses references from markdown, falling back to internal/external link metadata. |
| `_parse_markdown_block` | function | internal | `crawler/references.py:24` | Emits `Reference` objects parsed from markdown lines. |
| `_build_from_links` | function | internal | `crawler/references.py:40` | Builds deduplicated references from link buckets when markdown references are unavailable. |
| `_split_reference_tail` | function | internal | `crawler/references.py:58` | Splits reference tail into href and label. |
| `build_document_from_result` | function | public | `crawler/builder.py:15` | Main transformation pipeline for success/failure mapping and metadata shaping. |
| `_prepare_metadata` | function | internal | `crawler/builder.py:75` | Normalizes URL/title fields and records markdown lengths. |
| `_derive_failure_reason` | function | internal | `crawler/builder.py:101` | Builds user-visible failure reason from result fields/metadata/status. |
| `_ensure_markdown` | function | internal | `crawler/builder.py:116` | Ensures markdown is available by re-generating from HTML when needed. |
| `_extract_requested_url` | function | internal | `crawler/builder.py:154` | Resolves original request URL from metadata fallbacks. |

## Data Flow

1. Crawl layer passes `CrawlResult` into `build_document_from_result`.
2. Metadata is normalized (`requested_url`, `resolved_url`, title aliases).
3. Failed results return immediately as `CrawledDocument(status="failed")` with reason.
4. Successful results ensure markdown availability and select best content variant (`fit_markdown` → citations → raw).
5. References are parsed from markdown or reconstructed from link metadata.
6. Completed `CrawledDocument` is returned to API/CLI/MCP layers.

## Configuration

- No direct environment variables.
- Behavior depends on crawl result richness (presence/absence of markdown/html/metadata fields).
- Uses `build_markdown_generator` fallback from config module for resilience when Crawl4AI output is incomplete.

## Inventory Notes

- **Coverage**: full
- **Notes**: Exhaustive for files in the pipeline cluster (`document.py`, `references.py`, `builder.py`).
