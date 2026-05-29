# Output Formats

## Markdown

When `output_format="markdown"`, pages are concatenated with URL headers and timestamps:

```markdown
# https://example.com/page1
_Crawled: 2025-01-09 12:00:00 UTC_

[Page content as markdown...]

---

# https://example.com/page2
_Crawled: 2025-01-09 12:00:01 UTC_

[Page content as markdown...]
```

## JSON

When `output_format="json"`, results include metadata, dedup metrics, guardrail signals, and extracted references:

```json
{
  "crawled_at": "2025-01-09 12:00:00 UTC",
  "documents": [
    {
      "request_url": "https://example.com",
      "final_url": "https://example.com/",
      "status": "success",
      "markdown": "...",
      "error_message": null,
      "metadata": {
        "title": "Example",
        "status_code": 200,
        "dedup_mode": "exact",
        "dedup_sections_total": 12,
        "dedup_sections_removed": 3,
        "dedup_chars_removed": 542,
        "dedup_applied": true,
        "dedup_guardrail_checked": true,
        "dedup_guardrail_triggered": false,
        "dedup_guardrail_reason": "within-threshold",
        "dedup_guardrail_section_removal_rate": 0.25,
        "dedup_guardrail_section_rate_threshold": 0.6
      },
      "references": [
        {"index": 1, "href": "https://example.com/about", "label": "About"}
      ]
    }
  ],
  "summary": {
    "total": 1,
    "successful": 1,
    "failed": 0
  },
  "stats": {
    "total_pages": 1,
    "successful_pages": 1,
    "failed_pages": 0
  }
}
```

## CrawledDocument

The Python class returned by the API:

```python
@dataclass
class CrawledDocument:
    request_url: str              # Original URL requested
    final_url: str                # Final URL after redirects
    status: str                   # "success", "failed", or "redirected"
    markdown: str                 # Extracted markdown content
    html: Optional[str]           # Raw HTML (if available)
    headers: Dict[str, Any]       # HTTP response headers
    references: List[Reference]   # Extracted links
    metadata: Dict[str, Any]      # Title, status code, dedup metrics, guardrail info
    raw_markdown: Optional[str]   # Unprocessed markdown
    error_message: Optional[str]  # Error details if failed

@dataclass
class Reference:
    index: int
    href: str
    label: str
```
