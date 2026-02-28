---
type: documentation
entity: module
module: "crawler-config"
version: 1.0
---

# Module: crawler-config

> Part of [searxNcrawl](../overview.md)

## Overview

`crawler/config.py` encapsulates Crawl4AI run configuration and markdown generation tuning so crawl orchestration code can use a stable default profile with optional overrides.

### Responsibility

- Defines reusable selectors for main-content targeting and noise exclusion.
- Defines override schema (`RunConfigOverrides`) and safe application logic.
- Builds default run-configs for standard page crawling and discovery/deep-crawl scenarios.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| `crawl4ai.CrawlerRunConfig` | library | Base runtime configuration object for crawl execution (`crawler/config.py:9`). |
| `crawl4ai.async_configs.CacheMode` | library | Cache behavior enum and parsing target (`crawler/config.py:10`). |
| `PruningContentFilter` | library | Content filtering strategy to reduce noisy markdown sections (`crawler/config.py:11`). |
| `DefaultMarkdownGenerator` | library | Markdown generation strategy and options (`crawler/config.py:12`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/config.py` | file | Crawl config factory and override utilities. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `MAIN_SELECTORS` | const | public | `crawler/config.py:17` | Preferred document content selectors used for extraction targeting. |
| `EXCLUDED_SELECTORS` | const | public | `crawler/config.py:34` | Noise selectors (nav/sidebar/cookie banners) excluded from extraction. |
| `RunConfigOverrides` | class | public | `crawler/config.py:59` | Dataclass for optional per-run configuration customization. |
| `_convert_cache_mode` | function | internal | `crawler/config.py:82` | Converts user cache-mode strings to `CacheMode` with fallback/warnings. |
| `_apply_overrides` | function | internal | `crawler/config.py:99` | Mutates `CrawlerRunConfig` with only explicitly set override fields. |
| `build_markdown_generator` | function | public | `crawler/config.py:139` | Creates tuned markdown generator with pruning and output options. |
| `build_markdown_run_config` | function | public | `crawler/config.py:157` | Produces default config for single-page extraction (including JS wait logic). |
| `build_discovery_run_config` | function | public | `crawler/config.py:185` | Produces discovery-oriented config for link-centric/deep crawling scenarios. |

## Data Flow

1. Caller requests a run config via a factory function.
2. Factory builds `DefaultMarkdownGenerator` and baseline `CrawlerRunConfig`.
3. Optional override object is applied field-by-field.
4. Config is consumed by higher-level crawl orchestration modules.

## Configuration

- Key defaults in `build_markdown_run_config`:
  - `cache_mode=CacheMode.BYPASS` (`crawler/config.py:172`)
  - JS reload/scroll snippet (`crawler/config.py:174`)
  - `wait_for` condition requiring substantial `main` content (`crawler/config.py:178`)
- `build_discovery_run_config` adjusts wait and behavior for deep crawl/discovery use (`crawler/config.py:193`, `crawler/config.py:197`).

## Inventory Notes

- **Coverage**: full
- **Notes**: Includes all constants, dataclasses, and factories in `crawler/config.py`.

## Phase-2 Stability Note

- Selector and extraction configuration remain unchanged in dedup Phase 2.
- `MAIN_SELECTORS`, `EXCLUDED_SELECTORS`, `build_markdown_run_config`, and `build_discovery_run_config` are intentionally not modified by dedup surface/guardrail rollout work.
