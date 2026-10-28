---
type: documentation
entity: module
module: "crawler-cli"
version: 1.2
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
| `crawler-package-api` | module | Uses async crawl functions for single/multi/site crawl execution (`crawler/cli.py`). |
| `crawler-document-pipeline` | module | Uses `CrawledDocument` for type-safe output transforms (`crawler/cli.py`). |
| `crawler.search_orchestrator` | module | Multi-provider search and result serializer for the `search` command (`crawler/cli.py`). |
| `argparse` | library | Defines command interfaces and help text (`crawler/cli.py`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/cli.py` | file | Full CLI implementation for crawl/capture/search commands and output handling. |
| `crawler/setup.py` | file | Coding-agent discovery, registration/removal, config backups and confirmation. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `_setup_logging` | function | internal | `crawler/cli.py` | Standardized logging initialization with verbose toggle. |
| `_strip_markdown_links` | function | internal | `crawler/cli.py` | Removes markdown links + bare URLs for cleaner output. |
| `_format_search_markdown` | function | internal | `crawler/cli.py` | Renders result headings, source attribution, optional page Markdown nested two heading levels lower and per-page crawl errors. |
| `_doc_to_dict` | function | internal | `crawler/cli.py` | Serializes `CrawledDocument` for JSON output. |
| `_references_to_list` | function | internal | `crawler/cli.py` | Serializes only `CrawledDocument.references` as a JSON array for `--links-only --json` output. |
| `_format_references` | function | internal | `crawler/cli.py` | Renders references as `[N] label - href` lines for links-only markdown output. |
| `_url_to_filename` | function | internal | `crawler/cli.py` | Creates deterministic/safe filename from URL for multi-doc outputs. |
| `_write_output` | function | internal | `crawler/cli.py` | Handles stdout/file/dir output paths for crawl results, including links-only branching for single/multi document markdown and JSON modes. |
| `_parse_crawl_args` | function | internal | `crawler/cli.py` | Defines crawl command arguments, including mutually exclusive `--remove-links` and `--links-only` output controls. |
| `_run_crawl_async` | function | internal | `crawler/cli.py` | Executes crawl flow for single/multi/site modes and forwards `links_only`/format options into output materialization. |
| `main` | function | public | `crawler/cli.py` | Entrypoint for `crawl` script. |
| `_parse_capture_args` | function | internal | `crawler/cli.py` | Defines isolated session-capture CLI arguments. |
| `_format_cdp_session`, `_print_cdp_sessions`, `_select_cdp_session_interactive`, `_resolve_cdp_session_index` | functions | internal | `crawler/cli.py` | Format discovered CDP sessions and select a validated session index. |
| `_run_capture_async` | function | internal | `crawler/cli.py` | Executes isolated session-capture flow and maps success/timeout/abort to deterministic exit codes. |
| `capture_main` | function | public | `crawler/cli.py` | Entrypoint for `crawl-capture` script. |
| `_parse_search_args` | function | internal | `crawler/cli.py` | Defines search options, including `--providers` and `--include-content`, and examples. |
| `_run_search_async` | function | internal | `crawler/cli.py` | Runs provider search, optional result-page crawling and shared JSON/Markdown serialization. |
| `search_main` | function | public | `crawler/cli.py` | Entrypoint for `search` script. |
| `Agent`, `detect_agents`, `cli_commands`, `json_change`, `backup`, `main` | type/functions | public | `crawler/setup.py` | Native STDIO registration via agent CLIs or JSON config; preserve backups and refuse unsafe JSON rewrites. |

## Data Flow

1. Module import invokes shared `crawler.env.load_config()` to establish env variables.
2. Entrypoint parses args and sets logging.
3. Crawl dispatches to package APIs; capture uses isolated session capture; search resolves provider settings and validated SearXNG-only extra headers through `crawler.search_orchestrator.search`.
4. `search --include-content` crawls result pages and adds `markdown` or `crawl_error` without discarding search results.
5. Results are transformed and emitted to stdout/files with optional link stripping or links-only extraction.
6. Exit code reflects success/failure conditions.

## Configuration

- Environment variables read:
  - Search providers, read at call time by `crawler.search_orchestrator`: `SEARXNG_URL` (no default), `SEARXNG_USERNAME`/`SEARXNG_PASSWORD` (both or neither), `SEARXNG_EXTRA_HEADERS`, `YDC_API_KEY`; plus `SEARCH_RESULT_FIELDS`.
- Extra headers apply only to SearXNG. Invalid header configuration disables that provider before a request; a configured You.com provider remains available. Secret-file values are reread each call. [Header rules](../usage/installation.md#searxng-behind-cloudflare-access).
- `.env` search order and auto-seeding behavior implemented in shared `crawler/env.py` (see [crawler-env](crawler-env.md)).
- Crawl CLI exposes `--dedup-mode` with choices `exact|off` (default: `exact`).
- Crawl CLI exposes `--storage-state <path>` to enable authenticated crawling via Playwright storage state JSON.
- `--dedup-mode exact` preserves backward-compatible default behavior and enables intra-document exact dedup in the document pipeline.
- `--dedup-mode off` disables section removal for a crawl request; line endings still normalize to LF.
- CLI flags include crawl mode, output mode, and auth controls:

| Flag | Type | Default | Notes |
|------|------|---------|-------|
| `--json` | boolean | `False` | Emit JSON payloads instead of markdown. |
| `--include-content` | boolean | `False` | Search only: add result-page Markdown or `crawl_error`; three pages at a time, 15 s per page. |
| `--remove-links` | boolean | `False` | Strip markdown links from rendered markdown output. Mutually exclusive with `--links-only`. |
| `--links-only` | boolean | `False` | Output only extracted references; markdown mode renders `[N] label - href`, JSON mode renders a references-only array. Mutually exclusive with `--remove-links`. |
| `--site` | boolean | `False` | Enable DFS site crawl mode for a seed URL. |
| `--max-depth` | integer | `2` | Site crawl depth limit. |
| `--max-pages` | integer | `25` | Site crawl page limit. |
| `--include-subdomains` | boolean | `False` | Include subdomains during site crawl. |
| `--concurrency` | integer | `3` | Parallel URL crawl count for multi-URL mode. |
| `--storage-state` | path | `None` | Playwright `storage_state` JSON path for authenticated crawling. |
| `--dedup-mode` | enum (`exact\|off`) | `exact` | Enables/disables per-document markdown dedup. |

## Auth Surface

- Auth is a thin surface pass-through: CLI forwards `--storage-state` to package API `auth={"storage_state": ...}`.
- Validation and error semantics are owned by shared auth resolver code in package/core (no CLI-specific auth validation fork).
- Session capture is provided by the separate `crawl-capture` command; the crawl command consumes an existing state file.
- Capture supports isolated login and selected-context export from a running CDP browser; [usage](../usage/session-capture.md).

## Session Capture Surface

- `crawl-capture` is a dedicated command, isolated from `crawl` runtime paths.
- Isolated capture requires a `--completion-url` regex; CDP mode selects an existing context. Both write `storage_state` to `--output`.
- Deterministic outcomes:
  - success → exit `0`
  - timeout → exit `2`
  - abort (browser closed/user abort) → exit `130`
- Overwrite is opt-in via `--overwrite` to protect credential-bearing files.

## Inventory Notes

- **Coverage**: best-effort
- **Notes**: CLI command functions and setup registration entrypoints; private setup helpers are omitted.
- `searxncrawl setup` detects Claude Code, Codex, Gemini CLI, Cursor, VS Code and Claude Desktop. Each change is shown and confirmed unless `--yes` is supplied.
- Setup stores only `SEARXNG_URL` and `YDC_API_KEY`; the key is masked in setup output but stored as plaintext in agent configs. Other native configuration remains available through shared `.env` loading.

### Test Inventory (CLI links-only)

- `tests/test_cli.py` — `test_parse_crawl_args_accepts_links_only`
- `tests/test_cli.py` — `test_parse_crawl_args_rejects_links_only_with_remove_links`
- `tests/test_cli.py` — `test_parse_crawl_args_help_includes_links_only`
- `tests/test_cli.py` — `test_write_output_links_only_single_doc_markdown_stdout`
- `tests/test_cli.py` — `test_write_output_links_only_single_doc_markdown_file`
- `tests/test_cli.py` — `test_write_output_links_only_single_doc_json_stdout`
- `tests/test_cli.py` — `test_write_output_links_only_multi_doc_markdown_stdout_with_headers`
- `tests/test_cli.py` — `test_write_output_links_only_multi_doc_markdown_to_single_file`
- `tests/test_cli.py` — `test_write_output_links_only_multi_doc_markdown_to_directory`
- `tests/test_cli.py` — `test_run_crawl_async_site_links_only_mode_supported`
- `tests/test_cli.py` — `test_write_output_links_only_zero_references_markdown_message`
- `tests/test_cli.py` — `test_write_output_links_only_zero_references_json_empty_array`
