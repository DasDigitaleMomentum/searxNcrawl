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

# Session capture for authenticated crawling
crawl-capture --start-url https://example.com/login \
    --completion-url 'https://example.com/dashboard.*' \
    --output ./state.json
```

See [Session Capture](session-capture.md) for the full `crawl-capture` guide.

