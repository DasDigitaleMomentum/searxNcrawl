# Python API

<!-- Updated: 2026-10-28 -->

```python
from crawler import crawl_page_async, crawl_pages_async, crawl_site_async

# Single page
doc = await crawl_page_async("https://docs.example.com/intro", dedup_mode="exact")
print(doc.markdown)

# Site crawl
result = await crawl_site_async("https://docs.example.com", max_depth=2, max_pages=10)
for doc in result.documents:
    print(f"{doc.status}: {doc.final_url}")

# Multiple pages, preserving input order
pages = await crawl_pages_async(
    ["https://docs.example.com/intro", "https://docs.example.com/api"],
    concurrency=3,
    timeout=30,
)

# Authenticated crawl
doc = await crawl_page_async(
    "https://example.com/private",
    auth={"storage_state": "/path/to/state.json"},
)
```

- The examples run inside an async function or an environment supporting top-level `await`.
- Synchronous counterparts are `crawl_page`, `crawl_pages` and `crawl_site`; call them outside a running event loop. They do not accept `timeout`.

| API | Defaults and optional parameters |
| --- | --- |
| `crawl_page_async(url, ...)` | `config=None`, `dedup_mode="exact"`, `auth=None`, `timeout=None` → 30 s |
| `crawl_pages_async(urls, ...)` | Same page options, plus `concurrency=3`; failed pages become failed documents |
| `crawl_site_async(url, ...)` | `max_depth=2`, `max_pages=25`, `include_subdomains=False`, `dedup_mode="exact"`, `auth=None`, `timeout=None` → 120 s |

- `auth` accepts `AuthConfig(storage_state=...)` or a mapping with only `storage_state`; the path must resolve to a readable JSON object.
- Page timeouts raise `TimeoutError`; batch calls keep per-page failures. Site timeouts return an empty `documents` list with an entry in `errors` and `stats.error_count=1`.
- Chromium installation and browser startup are outside the crawl timeout.
- `dedup_mode="exact"` removes repeated Markdown sections within each document; use `"off"` to keep them.
- Environment files are loaded by CLI/MCP entrypoints. Direct API users must load configuration themselves if needed.

## Configuration

Default config is optimized for documentation sites. Customize via overrides:

```python
from crawler import build_markdown_run_config, RunConfigOverrides

config = build_markdown_run_config(
    RunConfigOverrides(
        delay_before_return_html=1.0,
        mean_delay=1.0,
        scan_full_page=True,
    )
)
doc = await crawl_page_async("https://example.com", config=config)
```

