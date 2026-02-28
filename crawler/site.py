"""Site crawler for multi-page BFS crawling."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import tldextract
from crawl4ai import AsyncWebCrawler, BrowserConfig
from crawl4ai.deep_crawling.bfs_strategy import BFSDeepCrawlStrategy, FilterChain
from crawl4ai.deep_crawling.filters import DomainFilter

from .builder import build_document_from_result
from .auth import AuthInput, resolve_auth
from .config import build_markdown_run_config
from .document import CrawledDocument

LOGGER = logging.getLogger(__name__)


@dataclass
class SiteCrawlOptions:
    """Options for site crawling."""

    max_depth: int = 2
    max_pages: int = 25
    include_subdomains: bool = False
    stream: bool = True


@dataclass
class SiteCrawlResult:
    """Result of a site crawl operation."""

    documents: List[CrawledDocument] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


def _normalize_host(host: Optional[str]) -> str:
    """Normalize hostname by removing port and lowercasing."""
    if not host:
        return ""
    return host.split(":")[0].lower()


@lru_cache(maxsize=256)
def _registrable_domain(host: str) -> Optional[str]:
    """Extract the registrable domain from a hostname."""
    if not host:
        return None
    extracted = tldextract.extract(host)
    if not extracted.domain or not extracted.suffix:
        return host
    domain = ".".join(part for part in (extracted.domain, extracted.suffix) if part)
    return domain or host


async def crawl_site_async(
    url: str,
    *,
    max_depth: int = 2,
    max_pages: int = 25,
    include_subdomains: bool = False,
    dedup_mode: str = "exact",
    auth: Optional[AuthInput] = None,
) -> SiteCrawlResult:
    """
    Crawl a website starting from a seed URL using BFS strategy.

    Args:
        url: The seed URL to start crawling from.
        max_depth: Maximum depth to crawl (0 = seed page only).
        max_pages: Maximum number of pages to crawl.
        include_subdomains: Whether to include subdomains in the crawl.

    Returns:
        SiteCrawlResult containing documents, errors, and stats.
    """
    seed_url = str(url)
    parsed = urlparse(seed_url)
    seed_host = _normalize_host(parsed.netloc or parsed.hostname)
    registrable = _registrable_domain(seed_host) if seed_host else None

    # Build domain filters
    filters = []
    if seed_host:
        allowed_hosts = {seed_host}
        if include_subdomains and registrable and registrable != seed_host:
            allowed_hosts.add(registrable)
        filters.append(DomainFilter(allowed_domains=sorted(allowed_hosts)))

    filter_chain = FilterChain(filters)

    # Configure the crawl
    config = build_markdown_run_config()
    config.deep_crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=max_depth,
        max_pages=max_pages,
        filter_chain=filter_chain,
    )
    # NOTE: stream must be False for BFS deep crawl.
    #
    # With stream=True, crawl4ai returns an async generator that yields 0 items
    # despite successful crawls - this is a bug in crawl4ai's BFS implementation.
    #
    # With stream=False, crawl4ai waits for all pages to complete and returns
    # a list of results. Trade-offs:
    #   - Memory: All results held in RAM (acceptable for max_pages limit)
    #   - Latency: Response only after last page (acceptable for MCP request/response)
    #   - Reliability: Works correctly ✓
    config.stream = False
    config.exclude_external_links = not include_subdomains

    documents: List[CrawledDocument] = []
    seen_urls: Set[str] = set()
    errors: List[Dict[str, str]] = []

    resolved_auth = resolve_auth(auth)
    browser_cfg = BrowserConfig(
        use_persistent_context=False,
        storage_state=resolved_auth.storage_state if resolved_auth else None,
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        crawl_result = await crawler.arun(url=seed_url, config=config)

        async for result in _iterate_results(crawl_result):
            try:
                document = build_document_from_result(result, dedup_mode=dedup_mode)
            except Exception as exc:
                LOGGER.warning("Failed to build document for %s: %s", result.url, exc)
                errors.append(
                    {
                        "url": str(result.url),
                        "error": str(exc),
                        "stage": "build",
                    }
                )
                continue

            # Deduplicate by request_url
            if document.request_url in seen_urls:
                continue
            seen_urls.add(document.request_url)

            documents.append(document)

            if document.status == "failed":
                errors.append(
                    {
                        "url": document.request_url,
                        "error": document.error_message or "Unknown",
                        "stage": "crawl",
                    }
                )
            else:
                LOGGER.debug(
                    "Crawled %s (%d/%d)",
                    document.request_url,
                    len(documents),
                    max_pages,
                )

            if len(documents) >= max_pages:
                LOGGER.info("Reached page limit of %d", max_pages)
                break

    stats = {
        "total_pages": len(documents),
        "successful_pages": sum(1 for d in documents if d.status == "success"),
        "failed_pages": sum(1 for d in documents if d.status == "failed"),
        "error_count": len(errors),
    }

    return SiteCrawlResult(documents=documents, errors=errors, stats=stats)


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


async def _iterate_results(result):
    """Iterate over crawl results, handling different result types."""
    import inspect

    from crawl4ai.models import CrawlResult, CrawlResultContainer

    # Handle list of results (returned when stream=False)
    if isinstance(result, list):
        for item in result:
            # Each item might be a CrawlResultContainer or CrawlResult
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

    # Fallback: single CrawlResult
    if isinstance(result, CrawlResult):
        yield result
