---
type: documentation
entity: feature
feature: "cli"
version: 1.0
---

# Feature: CLI Interface

> Part of [searxNcrawl](../overview.md)

## Summary

The CLI provides three commands -- `crawl`, `search`, and `crawl-mcp` -- installed globally via `pip install -e .`. The `crawl` command handles single-page crawling, multi-page batch crawling, site crawling, and includes a `capture-auth` subcommand for interactive auth session capture. The `search` command queries SearXNG. The `crawl-mcp` command starts the MCP server.

## How It Works

### User Flow

#### Crawl
```bash
# Single page to stdout
crawl https://example.com

# To file
crawl https://example.com -o page.md

# Multiple pages to directory
crawl https://example.com/p1 https://example.com/p2 -o output/

# Site crawl
crawl https://docs.example.com --site --max-depth 2 --max-pages 10

# SPA with auth
crawl --storage-state auth.json --delay 3 --wait-until networkidle https://spa.example.com

# Capture auth
crawl capture-auth --url https://login.example.com --output auth.json
```

#### Search
```bash
# Markdown (default)
search "python tutorials"

# JSON to file
search "docker compose" --json -o results.json

# With filters
search "AI news" --time-range week --language en --max-results 5
```

### Technical Flow

1. **Entry points** are registered in `pyproject.toml`:
   - `crawl` -> `crawler.cli:main`
   - `search` -> `crawler.cli:search_main`
   - `crawl-mcp` -> `crawler.mcp_server:main`

2. **Config loading** (`_load_config()`):
   - Loads `.env` from CWD, then `~/.config/searxncrawl/.env`.
   - Auto-copies `.env.example` to user config if neither exists.

3. **Crawl command** (`main()`):
   - Detects `capture-auth` subcommand via `argv[0]` check.
   - Parses args via `_parse_crawl_args()` or `_parse_capture_auth_args()`.
   - Builds `AuthConfig` via `_build_cli_auth()` (CLI args > env vars).
   - Builds `RunConfig` with SPA overrides if `--delay`/`--wait-until`/`--aggressive-spa` set.
   - Uses discovery config for site mode and markdown config for single/batch mode.
   - Dispatches to `crawl_page_async`, `crawl_pages_async`, or `crawl_site_async`.
   - Writes output via `_write_output()`:
     - Single doc, no `-o`: stdout
     - Single doc, `-o file`: write to file
     - Multiple docs: write to directory (individual `.md` files or single `crawl_results.json`)

4. **Search command** (`search_main()`):
   - Parses args via `_parse_search_args()`.
   - Creates httpx client, queries SearXNG `/search`.
   - Formats as Markdown (default) or JSON.
   - Outputs to stdout or file.

5. **Error handling**:
   - `KeyboardInterrupt` returns exit code 130.
   - Exceptions logged and return exit code 1.
   - Failed crawls produce warning logs but continue.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-core](../modules/crawler-core.md) | `main` (`cli.py:597`) | `crawl` command entry point |
| [crawler-core](../modules/crawler-core.md) | `search_main` (`cli.py:775`) | `search` command entry point |
| [crawler-core](../modules/crawler-core.md) | `_parse_crawl_args` (`cli.py:300`) | Crawl argument parser |
| [crawler-core](../modules/crawler-core.md) | `_parse_capture_auth_args` (`cli.py:420`) | Capture-auth argument parser |
| [crawler-core](../modules/crawler-core.md) | `_parse_search_args` (`cli.py:633`) | Search argument parser (incl. `--pageno`) |
| [crawler-core](../modules/crawler-core.md) | `_run_crawl_async` (`cli.py:489`) | Crawl execution |
| [crawler-core](../modules/crawler-core.md) | `_run_search_async` (`cli.py:730`) | Search execution (delegates to `search.py`) |
| [crawler-core](../modules/crawler-core.md) | `_run_capture_auth_async` (`cli.py:577`) | Capture-auth execution |
| [crawler-core](../modules/crawler-core.md) | `_build_cli_auth` (`cli.py:210`) | Build AuthConfig from CLI args |
| [crawler-core](../modules/crawler-core.md) | `_add_auth_args` (`cli.py:264`) | Add auth flags to argparse |
| [crawler-core](../modules/crawler-core.md) | `_write_output` (`cli.py:147`) | Output routing (stdout/file/dir) |
| [crawler-core](../modules/crawler-core.md) | `_load_config` (`cli.py:23`) | .env loading with fallback |

## Configuration

### Crawl Command Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `urls` | positional | required | URL(s) to crawl |
| `-o, --output` | str | stdout | Output file or directory |
| `--site` | flag | false | Enable BFS site crawl |
| `--max-depth` | int | 2 | BFS crawl depth |
| `--max-pages` | int | 25 | BFS page limit |
| `--include-subdomains` | flag | false | Include subdomains |
| `--concurrency` | int | 3 | Parallel crawls |
| `--json` | flag | false | JSON output |
| `--remove-links` | flag | false | Strip links from markdown |
| `--delay` | float | (none) | SPA delay seconds |
| `--wait-until` | choice | (none) | load, domcontentloaded, networkidle, commit |
| `--aggressive-spa` | flag | false | Opt in to reload + strict `main` wait |
| `--site-stream` | flag | false | Enable crawl4ai `stream=True` for site crawl |
| `-v, --verbose` | flag | false | Debug logging |
| `--cookies` | str | (none) | JSON string or file path |
| `--header` | repeatable | (none) | Custom HTTP header |
| `--storage-state` | str | (none) | Playwright storage state file |
| `--auth-profile` | str | (none) | Persistent browser profile |

### Capture-Auth Subcommand Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--url` | str | required | Login page URL |
| `--output` | str | `auth_state.json` | Storage state output path |
| `--wait-for-url` | str | (none) | Regex for auto-capture |
| `--timeout` | int | 300 | Timeout seconds |
| `--profile` | str | (none) | Profile name or path |
| `-v, --verbose` | flag | false | Debug logging |

### Search Command Arguments

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `query` | positional | required | Search query |
| `--language` | str | `en` | Language code |
| `--time-range` | choice | (none) | day, week, month, year |
| `--categories` | list | (all) | Search categories |
| `--engines` | list | (all) | Specific engines |
| `--safesearch` | int | 1 | 0=off, 1=moderate, 2=strict |
| `--max-results` | int | 10 | Max results (1-50) |
| `--pageno` | int | 1 | Page number for results |
| `-o, --output` | str | stdout | Output file |
| `--json` | flag | false | JSON output |
| `-v, --verbose` | flag | false | Debug logging |

### .env File Search Order

1. `./.env` (current working directory)
2. `~/.config/searxncrawl/.env`
3. Auto-copy from `.env.example` to user config if neither exists

## Edge Cases & Limitations

- **capture-auth subcommand detection**: Uses `argv[0] == "capture-auth"` before argparse runs, allowing the subcommand to have its own argument parser.
- **Output routing heuristic**: If `-o` ends with `/`, output is treated as a directory. Otherwise it's a file for single-URL crawls.
- **JSON output for failed crawls**: When `--json` is set, failed documents are included in output. Without `--json`, only successful documents are written; all-failures results in exit code 1.
- **Link removal**: Applied in-place on `CrawledDocument.markdown` for the CLI path (modifies the objects).

## Related Features

- [Web Crawling](web-crawling.md) -- core crawl logic
- [SearXNG Search](searxng-search.md) -- search logic
- [Authenticated Crawling](authenticated-crawling.md) -- auth CLI flags
- [Auth Capture](auth-capture.md) -- capture-auth subcommand
- [MCP Server](mcp-server.md) -- alternative interface (`crawl-mcp`)
