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
import inspect
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.async_dispatcher import SemaphoreDispatcher

from .auth import AuthConfig, build_browser_config
from .builder import build_document_from_result
from .config import RunConfigOverrides, build_markdown_run_config
from .document import CrawledDocument, Reference
from .search import SearchError, SearchResult, SearchResultItem, search, search_async
from .site import SiteCrawlResult, crawl_site, crawl_site_async

__all__ = [
    # Document types
    "CrawledDocument",
    "Reference",
    "SiteCrawlResult",
    # Search
    "SearchResult",
    "SearchResultItem",
    "SearchError",
    "search",
    "search_async",
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
    if not urls:
        return []

    run_config = config or build_markdown_run_config()
    browser_cfg = build_browser_config(auth)
    dispatcher = SemaphoreDispatcher(semaphore_count=max(1, concurrency))

    docs: List[Optional[CrawledDocument]] = [None] * len(urls)
    slots_by_url: Dict[str, Deque[int]] = defaultdict(deque)
    for index, url in enumerate(urls):
        slots_by_url[url].append(index)

    try:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            results = await crawler.arun_many(
                urls=urls,
                config=run_config,
                dispatcher=dispatcher,
            )

            async for result in _iterate_many_results(results):
                result_url = str(getattr(result, "url", "") or "")
                slot = _next_slot(slots_by_url, docs, result_url)
                if slot is None:
                    continue
                try:
                    docs[slot] = build_document_from_result(result)
                except Exception as exc:
                    docs[slot] = _failed_document(urls[slot], str(exc))
    except Exception as exc:
        return [_failed_document(url, str(exc)) for url in urls]

    for index, doc in enumerate(docs):
        if doc is None:
            docs[index] = _failed_document(
                urls[index],
                "Crawler returned no result",
            )

    return [doc for doc in docs if doc is not None]


def _next_slot(
    slots_by_url: Dict[str, Deque[int]],
    docs: List[Optional[CrawledDocument]],
    result_url: str,
) -> Optional[int]:
    queue = slots_by_url.get(result_url)
    if queue:
        return queue.popleft()
    for index, doc in enumerate(docs):
        if doc is None:
            return index
    return None


def _failed_document(url: str, error_message: str) -> CrawledDocument:
    return CrawledDocument(
        request_url=url,
        final_url=url,
        status="failed",
        markdown="",
        error_message=error_message,
    )


async def _iterate_many_results(result):
    from crawl4ai.models import CrawlResultContainer

    if isinstance(result, list):
        for item in result:
            if isinstance(item, CrawlResultContainer):
                for sub_item in item:
                    yield sub_item
            else:
                yield item
        return

    if isinstance(result, CrawlResultContainer):
        for item in result:
            yield item
        return

    if inspect.isasyncgen(result):
        async for item in result:
            yield item
        return

    yield result


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
