# MCP Tools

## `crawl`

Crawl one or more web pages and extract their content.

### Parameters

| Parameter      | Type       | Default      | Description                                         |
| -------------- | ---------- | ------------ | --------------------------------------------------- |
| `urls`         | `List[str]` | required     | URLs to crawl                                       |
| `output_format` | `str`       | `"markdown"` | `"markdown"` or `"json"`                              |
| `concurrency`  | `int`       | `3`          | Max concurrent crawls                               |
| `timeout`      | `int`       | `30`         | Per-URL timeout in seconds (≥ 1)                  |
| `remove_links` | `bool`      | `false`      | Remove all links from markdown output               |
| `dedup_mode`   | `str`       | `"exact"`    | `"exact"` or `"off"`                                  |
| `storage_state` | `str`       | `null`       | Path to Playwright storage state JSON for auth      |

### Examples

```
# Single page
crawl(urls=["https://docs.example.com"])

# Multiple pages with JSON output
crawl(urls=["https://example.com/page1", "https://example.com/page2"], output_format="json")

# Clean output without links
crawl(urls=["https://example.com"], remove_links=True)

# Disable markdown dedup
crawl(urls=["https://example.com"], dedup_mode="off")

# With authenticated state
crawl(urls=["https://example.com"], storage_state="/path/to/state.json")

# With custom timeout
crawl(urls=["https://slow-site.com"], timeout=60)
```

---

## `crawl_site`

Crawl an entire website starting from a seed URL using DFS strategy.

### Parameters

| Parameter          | Type  | Default      | Description                                         |
| ------------------ | ----- | ------------ | --------------------------------------------------- |
| `url`              | `str`  | required     | Seed URL to start from                              |
| `max_depth`        | `int`  | `2`          | Maximum crawl depth (0 = seed only)                 |
| `max_pages`        | `int`  | `25`         | Maximum pages to crawl                              |
| `include_subdomains` | `bool` | `false`     | Include subdomains                                  |
| `timeout`          | `int`  | `120`        | Overall site timeout in seconds (≥ 1)             |
| `output_format`    | `str`  | `"markdown"` | `"markdown"` or `"json"`                              |
| `remove_links`     | `bool` | `false`      | Remove all links from markdown output               |
| `dedup_mode`       | `str`  | `"exact"`    | `"exact"` or `"off"`                                  |
| `storage_state`    | `str`  | `null`       | Path to Playwright storage state JSON for auth      |

### Examples

```
# Basic site crawl
crawl_site(url="https://docs.example.com")

# Deep crawl with more pages
crawl_site(url="https://docs.example.com", max_depth=3, max_pages=50)

# JSON output with stats
crawl_site(url="https://docs.example.com", output_format="json")

# Without links
crawl_site(url="https://docs.example.com", remove_links=True)

# With auth
crawl_site(url="https://docs.example.com", storage_state="/path/to/state.json")
```

---

## `search`

Search the web using SearXNG metasearch engine.

### Parameters

| Parameter    | Type       | Default | Description                                           |
| ------------ | ---------- | ------- | ----------------------------------------------------- |
| `query`      | `str`       | required | Search query string                                   |
| `language`   | `str`       | `"en"`    | Language code (e.g. `"en"`, `"de"`, `"fr"`)                 |
| `time_range` | `str`       | `null`   | `"day"`, `"week"`, `"month"`, `"year"`                       |
| `categories` | `List[str]` | `null`   | `"general"`, `"images"`, `"news"`, etc.                        |
| `engines`    | `List[str]` | `null`   | Specific engines to use                               |
| `safesearch` | `int`       | `1`      | `0` (off), `1` (moderate), `2` (strict)                  |
| `pageno`     | `int`       | `1`      | Page number (≥ 1)                                    |
| `max_results` | `int`      | `10`     | Max results (1–50)                                    |
| `max_retries` | `int`      | `3`      | Max attempts for transient `RequestError` failures    |

### Examples

```
# Basic search
search(query="python tutorials")

# With time filter
search(query="latest AI news", time_range="week")

# Specific category
search(query="cute cats", categories=["images"])

# In German
search(query="Rezepte", language="de")

# Strict safe search
search(query="programming", safesearch=2)
```

### Response (JSON)

```json
{
  "query": "python tutorials",
  "number_of_results": 10,
  "results": [
    {
      "title": "Python Tutorial - W3Schools",
      "url": "https://www.w3schools.com/python/",
      "content": "Well organized tutorials...",
      "engine": "google",
      "category": "general"
    }
  ],
  "answers": [],
  "suggestions": ["python for beginners", "python course"],
  "corrections": []
}
```
