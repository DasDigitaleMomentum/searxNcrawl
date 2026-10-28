# CLI Tools

<!-- Updated: 2026-10-28 -->

After `pip install -e .` (or `uv sync`), the following commands are available:

```bash
# Crawl a page
crawl https://docs.example.com

# Site crawl with depth limit
crawl https://docs.example.com --site --max-depth 2 --max-pages 10 -o docs/

# Clean output (no links)
crawl https://example.com --remove-links

# Search
search "python tutorials"
search "Rezepte" --language de --max-results 5
search "python tutorials" --providers searxng
search "crawl4ai release notes" --max-results 3 --include-content

# Session capture for authenticated crawling
crawl-capture --start-url https://example.com/login \
    --completion-url 'https://example.com/dashboard.*' \
    --output ./state.json
```

See [Session Capture](session-capture.md) for the full `crawl-capture` guide.

## Crawl options

| Option | Default | Behavior |
| --- | --- | --- |
| `-o`, `--output` | stdout for one page; current directory for multiple | File for one page; directory for multiple pages |
| `--site` | off | DFS crawl from one seed URL |
| `--max-depth`, `--max-pages` | `2`, `25` | Site limits; depth `0` keeps only the seed |
| `--include-subdomains` | off | Broaden site link discovery |
| `--concurrency` | `3` | Concurrent pages in a batch |
| `--dedup-mode` | `exact` | `exact` or `off` |
| `--storage-state` | unset | Playwright session JSON path |
| `--json` | off | Include metadata, references and failed documents |
| `--remove-links` | off | Strip links from Markdown; references stay in JSON |
| `--links-only` | off | Export references; mutually exclusive with `--remove-links` |
| `-v`, `--verbose` | off | Debug logging |

- Single-page and batch crawl timeouts use the Python API default of 30 s per page; a site uses 120 s. The CLI has no crawl `--timeout` flag.
- In content mode, multiple-page Markdown output creates one file per page; JSON creates `crawl_results.json` in the output directory. With `--links-only`, a batch prints combined references to stdout or writes per-page files to a directory; an explicit file path writes combined references. See [output formats](output-formats.md).
- Exit codes: `0` when at least one crawl succeeds, `1` when all fail or an error occurs, `130` on interruption.

## Search options

| Option | Default | Behavior |
| --- | --- | --- |
| `--language` | `en` | Provider language filter |
| `--time-range` | unset | `day`, `week`, `month` or `year` |
| `--categories`, `--engines` | unset | Space-separated SearXNG values |
| `--safesearch` | `1` | `0`, `1` or `2` |
| `--max-results` | `10` | Merged result limit, clamped to 1–50 |
| `--providers` | all configured | Comma-separated `searxng,youcom` subset |
| `--include-content` | off | Crawl result pages |
| `--json` | off | JSON instead of Markdown |
| `-o`, `--output` | stdout | Save the selected output format to a file |
| `-v`, `--verbose` | off | Debug logging |

- CLI search uses page `1` and one request attempt per provider; it has no `--pageno` or `--max-retries` option.
- Exit codes: `0` for a successful search, including zero results; `1` on failure; `130` on interruption.

## Protected SearXNG search

```bash
export SEARXNG_EXTRA_HEADERS='{"CF-Access-Client-Id":"@~/.config/searxncrawl/cf_id","CF-Access-Client-Secret":"@~/.config/searxncrawl/cf_secret"}'
search "python documentation" --providers searxng --json
```

- Extra headers apply only to SearXNG; Basic Auth remains available through `SEARXNG_USERNAME` and `SEARXNG_PASSWORD`.
- Secret files require absolute or `~/` references and are reread each call. Invalid configuration disables SearXNG; explicitly selecting it returns exit code 1. Other configured providers remain available.
- Names must be HTTP tokens; values must be ASCII strings without control characters. Required JSON headers cannot be overridden. [Complete rules](installation.md#searxng-behind-cloudflare-access).

## Search with page content

- `--include-content` adds `markdown` or `crawl_error` to every result in JSON output; search results survive individual page failures.
- Markdown output nests each page below its `##` result heading; page headings shift down two levels, capped at h6, with closed fenced code preserved.
- Crawling runs three pages at a time with a 15 s per-page timeout; use a small `--max-results` for faster calls.

