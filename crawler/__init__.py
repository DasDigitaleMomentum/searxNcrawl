"""Standalone web crawler with markdown extraction.

This module provides a clean API for crawling web pages and extracting
their content as markdown. It supports:

- Single page crawling
- Multiple pages crawling (batch)
- Site crawling with depth/page limits (BFS strategy)
- Authenticated crawling via cookies, headers, or storage state

Example usage:

    from crawler import crawl_page, crawl_pages, crawl_site

    # Single page
    doc = await crawl_page_async("https://example.com")
    print(doc.markdown)

    # Multiple pages
    docs = await crawl_pages_async([
        "https://example.com/page1",
        "https://example.com/page2",
    ])

    # Site crawl
    result = await crawl_site_async(
        "https://docs.example.com",
        max_depth=2,
        max_pages=10,
    )
    for doc in result.documents:
        print(f"--- {doc.final_url} ---")
        print(doc.markdown)

    # Authenticated crawl
    from crawler.auth import AuthConfig
    auth = AuthConfig(storage_state="./auth_state.json")
    doc = await crawl_page_async("https://protected.example.com", auth=auth)
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

from .auth import AuthConfig, build_browser_config
from .builder import build_document_from_result
from .config import RunConfigOverrides, build_markdown_run_config
from .document import CrawledDocument, Reference
from .site import SiteCrawlResult, crawl_site, crawl_site_async

__all__ = [
    # Document types
    "CrawledDocument",
    "Reference",
    "SiteCrawlResult",
    # Auth
    "AuthConfig",
    "build_browser_config",
    # Single page
    "crawl_page",
    "crawl_page_async",
    # Multiple pages
    "crawl_pages",
    "crawl_pages_async",
    # Site crawl
    "crawl_site",
    "crawl_site_async",
    # Config (for advanced usage)
    "RunConfigOverrides",
    "build_markdown_run_config",
    # MCP Server
    "mcp",
]


def get_mcp_server():
    """Get the MCP server instance (lazy import to avoid dependency if not needed)."""
    from .mcp_server import mcp

    return mcp


# Lazy import for mcp to avoid requiring fastmcp if not used
def __getattr__(name):
    if name == "mcp":
        from .mcp_server import mcp

        return mcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


async def crawl_page_async(
    url: str,
    *,
    config: Optional[CrawlerRunConfig] = None,
    auth: Optional[AuthConfig] = None,
) -> CrawledDocument:
    """
    Crawl a single page and return the extracted markdown.

    Args:
        url: The URL to crawl.
        config: Optional CrawlerRunConfig for advanced customization.
        auth: Optional AuthConfig for authenticated crawling.

    Returns:
        CrawledDocument with markdown content, references, and metadata.

    Raises:
        ValueError: If the crawler returns no results.
    """
    run_config = config or build_markdown_run_config()
    browser_cfg = build_browser_config(auth)
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        container = await crawler.arun(url=url, config=run_config)

    try:
        first_result = container[0]
    except (IndexError, TypeError):
        first_result = None

    if first_result is None:
        raise ValueError(f"Crawler returned no results for {url}")

    return build_document_from_result(first_result)


def crawl_page(
    url: str,
    *,
    config: Optional[CrawlerRunConfig] = None,
    auth: Optional[AuthConfig] = None,
) -> CrawledDocument:
    """Synchronous wrapper for crawl_page_async."""
    return asyncio.run(crawl_page_async(url, config=config, auth=auth))


async def crawl_pages_async(
    urls: List[str],
    *,
    config: Optional[CrawlerRunConfig] = None,
    auth: Optional[AuthConfig] = None,
    concurrency: int = 3,
) -> List[CrawledDocument]:
    """
    Crawl multiple pages and return their extracted markdown.

    Args:
        urls: List of URLs to crawl.
        config: Optional CrawlerRunConfig for advanced customization.
        auth: Optional AuthConfig for authenticated crawling.
        concurrency: Maximum number of concurrent crawls.

    Returns:
        List of CrawledDocument objects (in same order as input URLs).
        Failed crawls will have status="failed" and error_message set.
    """
    run_config = config or build_markdown_run_config()
    semaphore = asyncio.Semaphore(concurrency)

    async def crawl_one(url: str) -> CrawledDocument:
        async with semaphore:
            try:
                return await crawl_page_async(url, config=run_config, auth=auth)
            except Exception as exc:
                # Return a failed document instead of raising
                return CrawledDocument(
                    request_url=url,
                    final_url=url,
                    status="failed",
                    markdown="",
                    error_message=str(exc),
                )

    tasks = [crawl_one(url) for url in urls]
    return await asyncio.gather(*tasks)


def crawl_pages(
    urls: List[str],
    *,
    config: Optional[CrawlerRunConfig] = None,
    auth: Optional[AuthConfig] = None,
    concurrency: int = 3,
) -> List[CrawledDocument]:
    """Synchronous wrapper for crawl_pages_async."""
    return asyncio.run(
        crawl_pages_async(urls, config=config, auth=auth, concurrency=concurrency)
    )
