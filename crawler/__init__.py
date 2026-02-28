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
from typing import Any, List, Optional, cast

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.models import CrawlResult, CrawlResultContainer

from .builder import build_document_from_result
from .auth import AuthConfig, AuthInput, resolve_auth
from .config import RunConfigOverrides, build_markdown_run_config
from .document import CrawledDocument, Reference
from .session_capture import CaptureResult, capture_session, capture_session_async
from .site import SiteCrawlResult, crawl_site_async as _crawl_site_async

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
    # Session capture (isolated)
    "CaptureResult",
    "capture_session",
    "capture_session_async",
    # Config (for advanced usage)
    "AuthConfig",
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
    auth: Optional[AuthInput] = None,
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
    resolved_auth = resolve_auth(auth)
    browser_cfg = (
        BrowserConfig(storage_state=resolved_auth.storage_state)
        if resolved_auth and resolved_auth.storage_state
        else None
    )

    if browser_cfg is None:
        async with AsyncWebCrawler() as crawler:
            container = await crawler.arun(url=url, config=run_config)
    else:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            container = await crawler.arun(url=url, config=run_config)

    first_result = await _extract_first_result(container)

    if first_result is None:
        raise ValueError(f"Crawler returned no results for {url}")

    return build_document_from_result(first_result, dedup_mode=dedup_mode)


async def _extract_first_result(container: Any) -> Optional[CrawlResult]:
    """Extract first result item from crawl4ai return shapes."""
    if isinstance(container, CrawlResult):
        return container

    if isinstance(container, CrawlResultContainer):
        for item in container:
            return cast(CrawlResult, item)
        return None

    if isinstance(container, list):
        for item in container:
            if isinstance(item, CrawlResult):
                return item
            if isinstance(item, CrawlResultContainer):
                for sub_item in item:
                    return cast(CrawlResult, sub_item)
        if container:
            return cast(CrawlResult, container[0])
        return None

    if inspect.isasyncgen(container):
        async for item in container:
            if isinstance(item, CrawlResult):
                return item
            if isinstance(item, CrawlResultContainer):
                for sub_item in item:
                    return cast(CrawlResult, sub_item)
            return cast(CrawlResult, item)

    return None


def crawl_page(
    url: str,
    *,
    config: Optional[CrawlerRunConfig] = None,
    dedup_mode: str = "exact",
    auth: Optional[AuthInput] = None,
) -> CrawledDocument:
    """Synchronous wrapper for crawl_page_async."""
    return asyncio.run(
        crawl_page_async(url, config=config, dedup_mode=dedup_mode, auth=auth)
    )


async def crawl_pages_async(
    urls: List[str],
    *,
    config: Optional[CrawlerRunConfig] = None,
    concurrency: int = 3,
    dedup_mode: str = "exact",
    auth: Optional[AuthInput] = None,
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
    resolved_auth = resolve_auth(auth)
    semaphore = asyncio.Semaphore(concurrency)

    async def crawl_one(url: str) -> CrawledDocument:
        async with semaphore:
            try:
                return await crawl_page_async(
                    url,
                    config=run_config,
                    dedup_mode=dedup_mode,
                    auth=resolved_auth,
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
    auth: Optional[AuthInput] = None,
) -> List[CrawledDocument]:
    """Synchronous wrapper for crawl_pages_async."""
    return asyncio.run(
        crawl_pages_async(
            urls,
            config=config,
            concurrency=concurrency,
            dedup_mode=dedup_mode,
            auth=auth,
        )
    )


async def crawl_site_async(
    url: str,
    *,
    max_depth: int = 2,
    max_pages: int = 25,
    include_subdomains: bool = False,
    dedup_mode: str = "exact",
    auth: Optional[AuthInput] = None,
) -> SiteCrawlResult:
    """Async wrapper that forwards dedup mode to site crawl."""
    return await _crawl_site_async(
        url,
        max_depth=max_depth,
        max_pages=max_pages,
        include_subdomains=include_subdomains,
        dedup_mode=dedup_mode,
        auth=auth,
    )


def crawl_site(
    url: str,
    *,
    max_depth: int = 2,
    max_pages: int = 25,
    include_subdomains: bool = False,
    dedup_mode: str = "exact",
    auth: Optional[AuthInput] = None,
) -> SiteCrawlResult:
    """Synchronous wrapper for crawl_site_async."""
    return asyncio.run(
        crawl_site_async(
            url,
            max_depth=max_depth,
            max_pages=max_pages,
            include_subdomains=include_subdomains,
            dedup_mode=dedup_mode,
            auth=auth,
        )
    )
