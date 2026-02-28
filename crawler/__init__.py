"""Standalone web crawler with markdown extraction.

This module provides a clean API for crawling web pages and extracting
their content as markdown. It supports:

- Single page crawling
- Multiple pages crawling (batch)
- Site crawling with depth/page limits (BFS strategy)

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
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, List, Optional

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.models import CrawlResult, CrawlResultContainer

from .builder import build_document_from_result
from .config import RunConfigOverrides, build_markdown_run_config
from .document import CrawledDocument, Reference
from .site import SiteCrawlResult, crawl_site, crawl_site_async

__all__ = [
    # Document types
    "CrawledDocument",
    "Reference",
    "SiteCrawlResult",
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
    dedup_mode: str = "exact",
) -> CrawledDocument:
    """
    Crawl a single page and return the extracted markdown.

    Args:
        url: The URL to crawl.
        config: Optional CrawlerRunConfig for advanced customization.

    Returns:
        CrawledDocument with markdown content, references, and metadata.

    Raises:
        ValueError: If the crawler returns no results.
    """
    run_config = config or build_markdown_run_config()
    async with AsyncWebCrawler() as crawler:
        container = await crawler.arun(url=url, config=run_config)

    first_result = await _extract_first_result(container)

    if first_result is None:
        raise ValueError(f"Crawler returned no results for {url}")

    return build_document_from_result(first_result, dedup_mode=dedup_mode)


async def _extract_first_result(container: Any) -> Optional[CrawlResult]:
    """Extract first CrawlResult from any crawl4ai return shape."""
    if isinstance(container, CrawlResult):
        return container

    if isinstance(container, CrawlResultContainer):
        for item in container:
            return item
        return None

    if isinstance(container, list):
        for item in container:
            if isinstance(item, CrawlResult):
                return item
            if isinstance(item, CrawlResultContainer):
                for sub_item in item:
                    return sub_item
        return None

    if inspect.isasyncgen(container):
        async for item in container:
            if isinstance(item, CrawlResult):
                return item
            if isinstance(item, CrawlResultContainer):
                for sub_item in item:
                    return sub_item
            return item

    return None


def crawl_page(
    url: str,
    *,
    config: Optional[CrawlerRunConfig] = None,
    dedup_mode: str = "exact",
) -> CrawledDocument:
    """Synchronous wrapper for crawl_page_async."""
    return asyncio.run(crawl_page_async(url, config=config, dedup_mode=dedup_mode))


async def crawl_pages_async(
    urls: List[str],
    *,
    config: Optional[CrawlerRunConfig] = None,
    concurrency: int = 3,
    dedup_mode: str = "exact",
) -> List[CrawledDocument]:
    """
    Crawl multiple pages and return their extracted markdown.

    Args:
        urls: List of URLs to crawl.
        config: Optional CrawlerRunConfig for advanced customization.
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
                return await crawl_page_async(
                    url,
                    config=run_config,
                    dedup_mode=dedup_mode,
                )
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
    concurrency: int = 3,
    dedup_mode: str = "exact",
) -> List[CrawledDocument]:
    """Synchronous wrapper for crawl_pages_async."""
    return asyncio.run(
        crawl_pages_async(
            urls,
            config=config,
            concurrency=concurrency,
            dedup_mode=dedup_mode,
        )
    )
