# Python API

```python
from crawler import crawl_page, crawl_page_async, crawl_site, crawl_site_async

# Single page
doc = await crawl_page_async("https://docs.example.com/intro", dedup_mode="exact")
print(doc.markdown)

# Site crawl
result = crawl_site("https://docs.example.com", max_depth=2, max_pages=10)
for doc in result.documents:
    print(f"{doc.status}: {doc.final_url}")

# Authenticated crawl
doc = await crawl_page_async(
    "https://example.com/private",
    auth={"storage_state": "/path/to/state.json"},
)
```


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

