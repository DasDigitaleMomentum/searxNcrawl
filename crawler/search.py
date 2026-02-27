"""Shared SearXNG search implementation.

This module provides the canonical search functions used by the MCP server,
CLI, and Python API. Environment variables are read at call time (inside
``search_async``) so that tests can monkeypatch them freely and late ``.env``
loading works correctly.

Public API::

    from crawler.search import search_async, search, SearchResult, SearchResultItem, SearchError

    result = await search_async("python tutorials")
    print(result.number_of_results)
    for item in result.results:
        print(item.title, item.url)
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SearchResultItem:
    """A single search result from SearXNG."""

    title: str
    url: str
    content: str = ""
    engine: str = ""
    score: float = 0.0
    category: str = ""
    # Preserve any extra fields from SearXNG
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SearchResult:
    """Structured response from a SearXNG search query."""

    query: str
    number_of_results: int
    results: List[SearchResultItem] = field(default_factory=list)
    answers: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    corrections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary.

        The output shape matches the raw SearXNG JSON response so that
        existing consumers (``_format_search_markdown``, MCP JSON output)
        continue to work unchanged.
        """
        return {
            "query": self.query,
            "number_of_results": self.number_of_results,
            "results": [
                {
                    "title": item.title,
                    "url": item.url,
                    "content": item.content,
                    "engine": item.engine,
                    "score": item.score,
                    "category": item.category,
                    **item.extra,
                }
                for item in self.results
            ],
            "answers": self.answers,
            "suggestions": self.suggestions,
            "corrections": self.corrections,
        }


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SearchError(Exception):
    """Raised when the SearXNG search fails."""

    def __init__(self, message: str, query: str = ""):
        self.query = query
        super().__init__(message)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Known fields that map directly to SearchResultItem attributes.
_KNOWN_ITEM_FIELDS = frozenset(
    {"title", "url", "content", "engine", "score", "category"}
)


def _get_searxng_client(
    base_url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> httpx.AsyncClient:
    """Create an httpx async client for SearXNG with optional basic auth.

    Parameters fall back to environment variables when *None*.
    """
    url = base_url or os.getenv("SEARXNG_URL", "http://localhost:8888")
    user = username or os.getenv("SEARXNG_USERNAME")
    pw = password or os.getenv("SEARXNG_PASSWORD")

    auth = None
    if user and pw:
        auth = httpx.BasicAuth(user, pw)

    return httpx.AsyncClient(
        base_url=url,
        auth=auth,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )


def _raw_to_item(raw: Dict[str, Any]) -> SearchResultItem:
    """Convert a raw SearXNG result dict into a ``SearchResultItem``."""
    known = {k: raw[k] for k in _KNOWN_ITEM_FIELDS if k in raw}
    extra = {k: v for k, v in raw.items() if k not in _KNOWN_ITEM_FIELDS}
    return SearchResultItem(**known, extra=extra)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def search_async(
    query: str,
    *,
    language: str = "en",
    time_range: Optional[str] = None,
    categories: Optional[List[str]] = None,
    engines: Optional[List[str]] = None,
    safesearch: int = 1,
    pageno: int = 1,
    max_results: int = 10,
    searxng_url: Optional[str] = None,
    searxng_username: Optional[str] = None,
    searxng_password: Optional[str] = None,
) -> SearchResult:
    """Search the web using SearXNG metasearch engine.

    Args:
        query: Search query string (required).
        language: Language code (default: ``'en'``).
        time_range: ``'day'``, ``'week'``, ``'month'``, or ``'year'``
            (default: *None*).
        categories: List of categories (default: *None* = all).
        engines: List of engines (default: *None* = all).
        safesearch: 0=off, 1=moderate, 2=strict (default: 1).
        pageno: Page number (minimum 1, default: 1).
        max_results: Maximum results 1–50 (default: 10).
        searxng_url: Override ``SEARXNG_URL`` env var.
        searxng_username: Override ``SEARXNG_USERNAME`` env var.
        searxng_password: Override ``SEARXNG_PASSWORD`` env var.

    Returns:
        :class:`SearchResult` with structured results.

    Raises:
        SearchError: On authentication failure, HTTP error, or network error.
    """
    # Build search parameters
    params: Dict[str, Any] = {
        "q": query,
        "format": "json",
        "language": language,
        "safesearch": safesearch,
        "pageno": max(1, pageno),
    }

    if time_range and time_range in ("day", "week", "month", "year"):
        params["time_range"] = time_range

    if categories:
        params["categories"] = ",".join(categories)

    if engines:
        params["engines"] = ",".join(engines)

    try:
        async with _get_searxng_client(
            base_url=searxng_url,
            username=searxng_username,
            password=searxng_password,
        ) as client:
            response = await client.get("/search", params=params)
            response.raise_for_status()
            data = response.json()

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            raise SearchError(
                "Authentication failed. Check SEARXNG_USERNAME and SEARXNG_PASSWORD.",
                query=query,
            ) from exc
        raise SearchError(
            f"SearXNG API error: {exc.response.status_code} - {exc.response.text}",
            query=query,
        ) from exc

    except httpx.RequestError as exc:
        raise SearchError(
            f"Request failed: {exc}",
            query=query,
        ) from exc

    # Limit results
    max_results = min(max(1, max_results), 50)
    raw_results = data.get("results", [])[:max_results]

    items = [_raw_to_item(r) for r in raw_results]

    return SearchResult(
        query=data.get("query", query),
        number_of_results=len(items),
        results=items,
        answers=data.get("answers", []),
        suggestions=data.get("suggestions", []),
        corrections=data.get("corrections", []),
    )


def search(
    query: str,
    *,
    language: str = "en",
    time_range: Optional[str] = None,
    categories: Optional[List[str]] = None,
    engines: Optional[List[str]] = None,
    safesearch: int = 1,
    pageno: int = 1,
    max_results: int = 10,
    searxng_url: Optional[str] = None,
    searxng_username: Optional[str] = None,
    searxng_password: Optional[str] = None,
) -> SearchResult:
    """Synchronous wrapper for :func:`search_async`."""
    return asyncio.run(
        search_async(
            query,
            language=language,
            time_range=time_range,
            categories=categories,
            engines=engines,
            safesearch=safesearch,
            pageno=pageno,
            max_results=max_results,
            searxng_url=searxng_url,
            searxng_username=searxng_username,
            searxng_password=searxng_password,
        )
    )
