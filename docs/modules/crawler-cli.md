---
type: documentation
entity: module
module: "crawler-cli"
version: 1.0
---

# Module: crawler-cli

> Part of [searxNcrawl](../overview.md)

## Overview

`crawler/cli.py` defines the `crawl`, `crawl-capture`, and `search` command-line interfaces, including environment bootstrapping, argument parsing, output formatting, and command execution wrappers.

### Responsibility

- Load runtime config from local/user `.env` and bootstrap defaults.
- Parse CLI options for crawl, isolated capture, and search commands.
- Orchestrate calls to package crawl/search functionality.
- Emit markdown/json to stdout, file, or directory depending on invocation mode.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| `crawler-env` | module | Shared `.env` config loading with CWD → user-config fallback (`crawler/env.py`). |
| `crawler-package-api` | module | Uses async crawl functions for single/multi/site crawl execution (`crawler/cli.py:421`). |
| `crawler-document-pipeline` | module | Uses `CrawledDocument` for type-safe output transforms (`crawler/cli.py:65`). |
| `httpx` | library | Performs SearXNG HTTP requests for `search` command (`crawler/cli.py:16`). |
| `argparse` | library | Defines command interfaces and help text (`crawler/cli.py:5`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/cli.py` | file | Full CLI implementation for crawl/capture/search commands and output handling. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `_setup_logging` | function | internal | `crawler/cli.py:68` | Standardized logging initialization with verbose toggle. |
| `_strip_markdown_links` | function | internal | `crawler/cli.py:77` | Removes markdown links + bare URLs for cleaner output. |
| `_format_search_markdown` | function | internal | `crawler/cli.py:88` | Converts search JSON payload into readable markdown summary. |
| `_doc_to_dict` | function | internal | `crawler/cli.py:138` | Serializes `CrawledDocument` for JSON output. |
| `_references_to_list` | function | internal | `crawler/cli.py:154` | Serializes only `CrawledDocument.references` as a JSON array for `--links-only --json` output. |
| `_format_references` | function | internal | `crawler/cli.py:162` | Renders references as `[N] label - href` lines for links-only markdown output. |
| `_url_to_filename` | function | internal | `crawler/cli.py:172` | Creates deterministic/safe filename from URL for multi-doc outputs. |
| `_write_output` | function | internal | `crawler/cli.py:182` | Handles stdout/file/dir output paths for crawl results, including links-only branching for single/multi document markdown and JSON modes. |
| `_parse_crawl_args` | function | internal | `crawler/cli.py:309` | Defines crawl command arguments, including mutually exclusive `--remove-links` and `--links-only` output controls. |
| `_run_crawl_async` | function | internal | `crawler/cli.py:419` | Executes crawl flow for single/multi/site modes and forwards `links_only`/format options into output materialization. |
| `main` | function | public | `crawler/cli.py:498` | Entrypoint for `crawl` script. |
| `_parse_capture_args` | function | internal | `crawler/cli.py` | Defines isolated session-capture CLI arguments. |
| `_run_capture_async` | function | internal | `crawler/cli.py` | Executes isolated session-capture flow and maps success/timeout/abort to deterministic exit codes. |
| `capture_main` | function | public | `crawler/cli.py` | Entrypoint for `crawl-capture` script. |
| `_parse_search_args` | function | internal | `crawler/cli.py:780` | Defines search command options and examples. |
| `_run_search_async` | function | internal | `crawler/cli.py:871` | Executes SearXNG query and formats markdown/json output. |
| `search_main` | function | public | `crawler/cli.py:963` | Entrypoint for `search` script. |

## Data Flow

1. Module import invokes shared `crawler.env.load_config()` to establish env variables.
2. Entrypoint parses args and sets logging.
3. Crawl command dispatches to package crawl APIs; capture command dispatches to isolated session-capture runtime; search command calls SearXNG via httpx.
4. Results are transformed and emitted to stdout/files with optional link stripping or links-only extraction.
5. Exit code reflects success/failure conditions.

## Configuration

- Environment variables read:
  - `SEARXNG_URL` (default `http://localhost:8888`) (`crawler/cli.py:494`)
  - `SEARXNG_USERNAME`, `SEARXNG_PASSWORD` (`crawler/cli.py:495`-`crawler/cli.py:496`)
- `.env` search order and auto-seeding behavior implemented in shared `crawler/env.py` (see [crawler-env](crawler-env.md)).
- Crawl CLI exposes `--dedup-mode` with choices `exact|off` (default: `exact`).
- Crawl CLI exposes `--storage-state <path>` to enable authenticated crawling via Playwright storage state JSON.
- `--dedup-mode exact` preserves backward-compatible default behavior and enables intra-document exact dedup in the document pipeline.
- `--dedup-mode off` disables markdown dedup for a crawl request without changing other pipeline behavior.
- CLI flags include crawl mode, output mode, and auth controls:

| Flag | Type | Default | Notes |
|------|------|---------|-------|
| `--json` | boolean | `False` | Emit JSON payloads instead of markdown. |
| `--remove-links` | boolean | `False` | Strip markdown links from rendered markdown output. Mutually exclusive with `--links-only`. |
| `--links-only` | boolean | `False` | Output only extracted references; markdown mode renders `[N] label - href`, JSON mode renders a references-only array. Mutually exclusive with `--remove-links`. |
| `--site` | boolean | `False` | Enable BFS site crawl mode for a seed URL. |
| `--max-depth` | integer | `2` | Site crawl depth limit. |
| `--max-pages` | integer | `25` | Site crawl page limit. |
| `--include-subdomains` | boolean | `False` | Include subdomains during site crawl. |
| `--concurrency` | integer | `3` | Parallel URL crawl count for multi-URL mode. |
| `--storage-state` | path | `None` | Playwright `storage_state` JSON path for authenticated crawling. |
| `--dedup-mode` | enum (`exact\|off`) | `exact` | Enables/disables per-document markdown dedup. |

## Auth Surface (Phase 2 MVP)

- Auth is a thin surface pass-through: CLI forwards `--storage-state` to package API `auth={"storage_state": ...}`.
- Validation and error semantics are owned by shared auth resolver code in package/core (no CLI-specific auth validation fork).
- Scope boundary: session-capture/login automation is intentionally out of scope in this phase.
- No-drift invariant: this surface work does not modify `crawler/config.py` defaults (wait/selectors/SPA/session behavior).

## Session Capture Surface (Phase 3)

- `crawl-capture` is a dedicated command, isolated from `crawl` runtime paths.
- Capture requires explicit completion signal via `--completion-url` regex and writes `storage_state` to `--output`.
- Deterministic outcomes:
  - success → exit `0`
  - timeout → exit `2`
  - abort (browser closed/user abort) → exit `130`
- Overwrite is opt-in via `--overwrite` to protect credential-bearing files.

## Inventory Notes

- **Coverage**: full
- **Notes**: Covers the complete CLI module, including command families (`crawl`, `crawl-capture`, `search`) and `--links-only` output handling.

### Test Inventory (CLI links-only)

- `tests/test_cli.py:74` — `test_parse_crawl_args_accepts_links_only`
- `tests/test_cli.py:79` — `test_parse_crawl_args_rejects_links_only_with_remove_links`
- `tests/test_cli.py:84` — `test_parse_crawl_args_help_includes_links_only`
- `tests/test_cli.py:228` — `test_write_output_links_only_single_doc_markdown_stdout`
- `tests/test_cli.py:242` — `test_write_output_links_only_single_doc_markdown_file`
- `tests/test_cli.py:251` — `test_write_output_links_only_single_doc_json_stdout`
- `tests/test_cli.py:262` — `test_write_output_links_only_multi_doc_markdown_stdout_with_headers`
- `tests/test_cli.py:279` — `test_write_output_links_only_multi_doc_markdown_to_single_file`
- `tests/test_cli.py:295` — `test_write_output_links_only_multi_doc_markdown_to_directory`
- `tests/test_cli.py:314` — `test_run_crawl_async_site_links_only_mode_supported`
- `tests/test_cli.py:366` — `test_write_output_links_only_zero_references_markdown_message`
- `tests/test_cli.py:379` — `test_write_output_links_only_zero_references_json_empty_array`
