---
type: documentation
entity: module
module: "crawler-cli"
version: 1.0
---

# Module: crawler-cli

> Part of [searxNcrawl](../overview.md)

## Overview

`crawler/cli.py` defines the `crawl` and `search` command-line interfaces, including environment bootstrapping, argument parsing, output formatting, and command execution wrappers.

### Responsibility

- Load runtime config from local/user `.env` and bootstrap defaults.
- Parse CLI options for crawl and search commands.
- Orchestrate calls to package crawl/search functionality.
- Emit markdown/json to stdout, file, or directory depending on invocation mode.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| `crawler-package-api` | module | Uses async crawl functions for single/multi/site crawl execution (`crawler/cli.py:316`). |
| `crawler-document-pipeline` | module | Uses `CrawledDocument` for type-safe output transforms (`crawler/cli.py:65`). |
| `httpx` | library | Performs SearXNG HTTP requests for `search` command (`crawler/cli.py:16`). |
| `python-dotenv` | library | Loads `.env` from local/user config locations (`crawler/cli.py:17`). |
| `argparse` | library | Defines command interfaces and help text (`crawler/cli.py:5`). |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/cli.py` | file | Full CLI implementation for crawl/search commands and output handling. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `CONFIG_DIR` | const | internal | `crawler/cli.py:20` | Default user config directory (`~/.config/searxncrawl`). |
| `CONFIG_ENV_FILE` | const | internal | `crawler/cli.py:21` | User-level `.env` fallback path. |
| `_load_config` | function | internal | `crawler/cli.py:24` | Loads local/user `.env`, optionally seeds user config from `.env.example`. |
| `_setup_logging` | function | internal | `crawler/cli.py:68` | Standardized logging initialization with verbose toggle. |
| `_strip_markdown_links` | function | internal | `crawler/cli.py:77` | Removes markdown links + bare URLs for cleaner output. |
| `_format_search_markdown` | function | internal | `crawler/cli.py:88` | Converts search JSON payload into readable markdown summary. |
| `_doc_to_dict` | function | internal | `crawler/cli.py:132` | Serializes `CrawledDocument` for JSON output. |
| `_url_to_filename` | function | internal | `crawler/cli.py:148` | Creates deterministic/safe filename from URL for multi-doc outputs. |
| `_write_output` | function | internal | `crawler/cli.py:158` | Handles stdout/file/dir output paths for crawl command results. |
| `_parse_crawl_args` | function | internal | `crawler/cli.py:226` | Defines crawl command arguments and examples. |
| `_run_crawl_async` | function | internal | `crawler/cli.py:314` | Executes crawl flow for single/multi/site modes and exit codes. |
| `main` | function | public | `crawler/cli.py:379` | Entrypoint for `crawl` script. |
| `_parse_search_args` | function | internal | `crawler/cli.py:401` | Defines search command options and examples. |
| `_run_search_async` | function | internal | `crawler/cli.py:492` | Executes SearXNG query and formats markdown/json output. |
| `search_main` | function | public | `crawler/cli.py:584` | Entrypoint for `search` script. |

## Data Flow

1. Module import triggers `_load_config()` to establish env variables.
2. Entrypoint parses args and sets logging.
3. Crawl command dispatches to package crawl APIs; search command calls SearXNG via httpx.
4. Results are transformed and emitted to stdout/files with optional link stripping.
5. Exit code reflects success/failure conditions.

## Configuration

- Environment variables read:
  - `SEARXNG_URL` (default `http://localhost:8888`) (`crawler/cli.py:494`)
  - `SEARXNG_USERNAME`, `SEARXNG_PASSWORD` (`crawler/cli.py:495`-`crawler/cli.py:496`)
- `.env` search order and auto-seeding behavior documented in `_load_config` (`crawler/cli.py:24`-`crawler/cli.py:61`).
- CLI flags include `--json`, `--remove-links`, `--site`, depth/page/concurrency controls.

## Inventory Notes

- **Coverage**: full
- **Notes**: Covers the complete CLI module, including both command families (`crawl`, `search`).
