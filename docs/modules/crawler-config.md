---
type: documentation
entity: module
module: "crawler-config"
version: 1.1
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
| `crawl4ai.CrawlerRunConfig` | library | Base runtime configuration object for crawl execution (`crawler/config.py`). |
| `crawl4ai.async_configs.CacheMode` | library | Cache behavior enum and parsing target (`crawler/config.py`). |
| `PruningContentFilter` | library | Content filtering strategy to reduce noisy markdown sections (`crawler/config.py`). |
| `DefaultMarkdownGenerator` | library | Markdown generation strategy and options (`crawler/config.py`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/config.py` | file | Crawl config factory and override utilities. |
| `crawler/page_hooks.py` | file | Awaited HTTP(S) page reload hook for default crawl configurations. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `MAIN_SELECTORS` | const | public | `crawler/config.py` | Preferred document content selectors used for extraction targeting. |
| `MIN_CONTENT_CHARS`, `CONTENT_WAIT_GRACE_MS` | consts | public | `crawler/config.py` | Main-content threshold (50 characters) and body fallback delay (3000 ms). |
| `build_content_wait_condition` | function | public | `crawler/config.py` | Builds the main-content/body readiness condition. |
| `wants_page_reload` | function | public | `crawler/config.py` | Identifies default configs without a custom non-empty `js_code` override. |
| `_shadow_dom_kwargs`, `_load_js_script_escaping_text` | functions | internal | `crawler/config.py` | Detect shadow-DOM support and escape text in Crawl4AI's flattening script. |
| `reload_after_goto`, `install_reload_hook` | functions | public | `crawler/page_hooks.py` | Reload HTTP(S) pages once before readiness checks; log reload failures and retain the first load. |
| `EXCLUDED_SELECTORS` | const | public | `crawler/config.py` | Noise selectors (nav/sidebar/cookie banners) excluded from extraction. |
| `RunConfigOverrides` | class | public | `crawler/config.py` | Dataclass for optional per-run configuration customization. |
| `_convert_cache_mode` | function | internal | `crawler/config.py` | Converts user cache-mode strings to `CacheMode` with fallback/warnings. |
| `_apply_overrides` | function | internal | `crawler/config.py` | Mutates `CrawlerRunConfig` with only explicitly set override fields. |
| `build_markdown_generator` | function | public | `crawler/config.py` | Creates tuned markdown generator with pruning and output options. |
| `build_markdown_run_config` | function | public | `crawler/config.py` | Produces default config for single-page extraction (including JS wait logic). |
| `build_discovery_run_config` | function | public | `crawler/config.py` | Produces discovery-oriented config for link-centric/deep crawling scenarios. |

## Data Flow

1. Caller requests a run config via a factory function.
2. Factory builds `DefaultMarkdownGenerator` and baseline `CrawlerRunConfig`.
3. Optional override object is applied field-by-field.
4. Config is consumed by higher-level crawl orchestration modules.

## Configuration

- Key defaults in `build_markdown_run_config`:
  - `cache_mode=CacheMode.BYPASS` (`crawler/config.py`)
  - JS scroll snippet; the page reload runs as a Playwright `after_goto` hook (`crawler/page_hooks.py`) for configs from `build_markdown_run_config()` without a custom `js_code` override
  - `flatten_shadow_dom=True` so content rendered into shadow roots (e.g. MDN code examples) reaches the markdown; skipped on Crawl4AI < 0.8.5, and Crawl4AI's flatten script is patched to escape text nodes (see `_load_js_script_escaping_text`)
  - `wait_for` condition from `build_content_wait_condition()` (`crawler/config.py`): ready when any `MAIN_SELECTORS` area has more than `MIN_CONTENT_CHARS` characters; otherwise falls back to the page body after `CONTENT_WAIT_GRACE_MS` once the document has loaded
- `build_discovery_run_config` provides a separate discovery profile (`wait_until="domcontentloaded"`, 2 s extraction delay); current site crawling uses `build_markdown_run_config`, not this factory.

## Inventory Notes

- **Coverage**: best-effort
- **Notes**: Configuration factories, override model, selectors and runtime hooks; private tracking/patch constants are omitted.

## Configuration Stability

- Deduplication runs after extraction in `crawler/builder.py`; it does not change selector, wait or browser configuration.
- Custom configs retain their own reload behavior; only configs tracked by `wants_page_reload` receive the default hook.
