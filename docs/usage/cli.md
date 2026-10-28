# CLI Tools

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

