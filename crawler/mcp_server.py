"""MCP Server for the standalone crawler + SearXNG search.

Provides tools for:
- Crawling web pages and extracting markdown content
- Searching the web via SearXNG metasearch engine

Supports both STDIO and HTTP transports.

Usage:
    # STDIO (for Claude Desktop, etc.)
    python -m crawler.mcp_server

    # HTTP (for remote access)
    python -m crawler.mcp_server --transport http --port 8000

    # Or via FastMCP CLI
    fastmcp run crawler/mcp_server.py:mcp --transport http --port 8000

Environment Variables:
    SEARXNG_URL: SearXNG instance URL (default: http://localhost:8888)
    SEARXNG_USERNAME: Optional basic auth username
    SEARXNG_PASSWORD: Optional basic auth password
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

from .document import CrawledDocument

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger(__name__)

# Load .env before reading environment variables
load_dotenv()

# SearXNG configuration from environment
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8888")
SEARXNG_USERNAME = os.getenv("SEARXNG_USERNAME")
SEARXNG_PASSWORD = os.getenv("SEARXNG_PASSWORD")

# Create the MCP server
mcp = FastMCP(
    name="Web Crawler & Search",
    instructions="""
    A web crawler and search server that provides:

    1. Web Crawling Tools:
       - crawl: Crawl one or more URLs and get markdown content
       - crawl_site: Crawl an entire website with depth/page limits

    2. Web Search Tool:
       - search: Search the web using SearXNG metasearch engine

    Output formats for crawl tools:
    - markdown: Clean concatenated markdown (default)
    - json: Full details including metadata and references
    """,
)


class OutputFormat(str, Enum):
    """Output format for crawl results."""

    markdown = "markdown"
    json = "json"


def _format_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _strip_markdown_links(text: str) -> str:
    """Remove markdown links from text, keeping only the link text.

    Converts [text](url) to text and removes standalone URLs.
    """
    import re

    # Replace [text](url) with just text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove standalone URLs (http/https)
    text = re.sub(r"https?://\S+", "", text)
    # Clean up any double spaces left behind
    text = re.sub(r"  +", " ", text)
    return text


def _doc_to_dict(doc: CrawledDocument) -> dict:
    """Convert CrawledDocument to JSON-serializable dict."""
    return {
        "request_url": doc.request_url,
        "final_url": doc.final_url,
        "status": doc.status,
        "markdown": doc.markdown,
        "error_message": doc.error_message,
        "metadata": doc.metadata,
        "references": [
            {"index": ref.index, "href": ref.href, "label": ref.label}
            for ref in doc.references
        ],
    }


def _format_single_doc_markdown(doc: CrawledDocument) -> str:
    """Format a single document as markdown with header."""
    lines = [
        f"# {doc.final_url}",
        f"_Crawled: {_format_timestamp()}_",
        "",
    ]

    if doc.status == "failed":
        lines.append(f"**Error:** {doc.error_message}")
    else:
        lines.append(doc.markdown)

    return "\n".join(lines)


def _format_multiple_docs_markdown(docs: List[CrawledDocument]) -> str:
    """Format multiple documents as concatenated markdown."""
    sections = []

    for i, doc in enumerate(docs):
        if i > 0:
            sections.append("\n---\n")
        sections.append(_format_single_doc_markdown(doc))

    return "\n".join(sections)


def _format_output(
    docs: List[CrawledDocument],
    output_format: OutputFormat,
    stats: Optional[dict] = None,
    remove_links: bool = False,
) -> str:
    """Format crawl results based on output format."""
    if output_format == OutputFormat.json:
        doc_dicts = [_doc_to_dict(doc) for doc in docs]
        if remove_links:
            for d in doc_dicts:
                if d.get("markdown"):
                    d["markdown"] = _strip_markdown_links(d["markdown"])
        result = {
            "crawled_at": _format_timestamp(),
            "documents": doc_dicts,
            "summary": {
                "total": len(docs),
                "successful": sum(1 for d in docs if d.status == "success"),
                "failed": sum(1 for d in docs if d.status == "failed"),
            },
        }
        if stats:
            result["stats"] = stats
        return json.dumps(result, indent=2, ensure_ascii=False)
    else:
        # Markdown format
        output = _format_multiple_docs_markdown(docs)
        if remove_links:
            output = _strip_markdown_links(output)
        return output


# =============================================================================
# CRAWL TOOLS
# =============================================================================


@mcp.tool
async def crawl(
    urls: List[str],
    output_format: str = "markdown",
    concurrency: int = 3,
    remove_links: bool = False,
    dedup_mode: str = "exact",
    storage_state: Optional[str] = None,
):
    """
    Crawl one or more web pages and extract their content as markdown.

    Args:
        urls: List of URLs to crawl (can be a single URL)
        output_format: Output format - "markdown" (default) or "json"
            - markdown: Clean concatenated markdown with URL headers and timestamps
            - json: Full JSON with metadata, references, and statistics
        concurrency: Maximum concurrent crawls (default: 3)
        remove_links: Remove all links from the markdown output (default: false)
        dedup_mode: Markdown dedup mode - "exact" (default) or "off"
        storage_state: Path to Playwright storage_state JSON for authenticated crawling

    Returns:
        Crawled content in the specified format.

    Examples:
        # Single page
        crawl(urls=["https://docs.example.com"])

        # Multiple pages
        crawl(urls=["https://example.com/page1", "https://example.com/page2"])

        # With JSON output
        crawl(urls=["https://example.com"], output_format="json")

        # Clean output without links
        crawl(urls=["https://example.com"], remove_links=True)
    """
    from . import crawl_page_async, crawl_pages_async

    # Validate output format
    try:
        fmt = OutputFormat(output_format.lower())
    except ValueError:
        fmt = OutputFormat.markdown

    LOGGER.info("Crawling %d URL(s)...", len(urls))
    auth = {"storage_state": storage_state} if storage_state else None

    if len(urls) == 1:
        try:
            doc = await crawl_page_async(urls[0], dedup_mode=dedup_mode, auth=auth)
            docs = [doc]
        except Exception as exc:
            docs = [
                CrawledDocument(
                    request_url=urls[0],
                    final_url=urls[0],
                    status="failed",
                    markdown="",
                    error_message=str(exc),
                )
            ]
    else:
        docs = await crawl_pages_async(
            urls,
            concurrency=concurrency,
            dedup_mode=dedup_mode,
            auth=auth,
        )

    successful = sum(1 for d in docs if d.status == "success")
    LOGGER.info("Completed: %d/%d successful", successful, len(docs))

    return _format_output(docs, fmt, remove_links=remove_links)


@mcp.tool
async def crawl_site(
    url: str,
    max_depth: int = 2,
    max_pages: int = 25,
    include_subdomains: bool = False,
    output_format: str = "markdown",
    remove_links: bool = False,
    dedup_mode: str = "exact",
    storage_state: Optional[str] = None,
):
    """
    Crawl an entire website starting from a seed URL using BFS strategy.

    Args:
        url: The seed URL to start crawling from
        max_depth: Maximum depth to crawl (default: 2, 0 = seed page only)
        max_pages: Maximum number of pages to crawl (default: 25)
        include_subdomains: Whether to include subdomains in the crawl (default: false)
        output_format: Output format - "markdown" (default) or "json"
            - markdown: Clean concatenated markdown with URL headers and timestamps
            - json: Full JSON with metadata, references, and crawl statistics
        remove_links: Remove all links from the markdown output (default: false)
        dedup_mode: Markdown dedup mode - "exact" (default) or "off"
        storage_state: Path to Playwright storage_state JSON for authenticated crawling

    Returns:
        Crawled content from all pages in the specified format.

    Examples:
        # Basic site crawl
        crawl_site(url="https://docs.example.com")

        # Deep crawl with more pages
        crawl_site(url="https://docs.example.com", max_depth=3, max_pages=50)

        # Include subdomains
        crawl_site(url="https://example.com", include_subdomains=True)

        # JSON output with stats
        crawl_site(url="https://docs.example.com", output_format="json")

        # Clean output without links
        crawl_site(url="https://docs.example.com", remove_links=True)
    """
    from . import crawl_site_async

    # Validate output format
    try:
        fmt = OutputFormat(output_format.lower())
    except ValueError:
        fmt = OutputFormat.markdown

    LOGGER.info(
        "Starting site crawl: %s (max_depth=%d, max_pages=%d)",
        url,
        max_depth,
        max_pages,
    )

    result = await crawl_site_async(
        url,
        max_depth=max_depth,
        max_pages=max_pages,
        include_subdomains=include_subdomains,
        dedup_mode=dedup_mode,
        auth={"storage_state": storage_state} if storage_state else None,
    )

    LOGGER.info(
        "Site crawl complete: %d pages (%d successful, %d failed)",
        result.stats.get("total_pages", 0),
        result.stats.get("successful_pages", 0),
        result.stats.get("failed_pages", 0),
    )

    return _format_output(
        result.documents, fmt, stats=result.stats, remove_links=remove_links
    )


# =============================================================================
# SEARXNG SEARCH TOOL
# =============================================================================


def _get_searxng_client() -> httpx.AsyncClient:
    """Create an httpx client for SearXNG with optional basic auth."""
    auth = None
    if SEARXNG_USERNAME and SEARXNG_PASSWORD:
        auth = httpx.BasicAuth(SEARXNG_USERNAME, SEARXNG_PASSWORD)

    return httpx.AsyncClient(
        base_url=SEARXNG_URL,
        auth=auth,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )


@mcp.tool
async def search(
    query: str,
    language: str = "en",
    time_range: Optional[str] = None,
    categories: Optional[List[str]] = None,
    engines: Optional[List[str]] = None,
    safesearch: int = 1,
    pageno: int = 1,
    max_results: int = 10,
):
    """
    Search the web using SearXNG metasearch engine.

    Args:
        query: Search query string (required)
        language: Language code for results (e.g., 'en', 'de', 'fr'). Default: 'en'
        time_range: Time range filter - 'day', 'week', 'month', or 'year'. Default: None (no filter)
        categories: Categories to search (e.g., ['general', 'images', 'news']). Default: None (all)
        engines: Specific search engines to use. Default: None (all available)
        safesearch: Safe search level - 0 (off), 1 (moderate), 2 (strict). Default: 1
        pageno: Page number for results (minimum 1). Default: 1
        max_results: Maximum results to return (1-50). Default: 10

    Returns:
        JSON string with search results including:
        - query: The search query
        - number_of_results: Count of results returned
        - results: Array of result objects with title, url, content, engine, etc.
        - answers: Direct answers if available
        - suggestions: Related search suggestions
        - corrections: Spelling corrections if any

    Examples:
        # Basic search
        search(query="python tutorials")

        # Search with time filter
        search(query="latest AI news", time_range="week")

        # Search specific category
        search(query="cute cats", categories=["images"])

        # Search in German
        search(query="Rezepte", language="de")
    """
    LOGGER.info("Searching SearXNG for: %s", query)

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
        async with _get_searxng_client() as client:
            response = await client.get("/search", params=params)
            response.raise_for_status()
            data = response.json()

        # Limit results
        max_results = min(max(1, max_results), 50)
        if "results" in data:
            data["results"] = data["results"][:max_results]
            data["number_of_results"] = len(data["results"])

        LOGGER.info("Search returned %d results", data.get("number_of_results", 0))

        return json.dumps(data, indent=2, ensure_ascii=False)

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            error_msg = (
                "Authentication failed. Check SEARXNG_USERNAME and SEARXNG_PASSWORD."
            )
        else:
            error_msg = (
                f"SearXNG API error: {exc.response.status_code} - {exc.response.text}"
            )
        LOGGER.error(error_msg)
        return json.dumps({"error": error_msg, "query": query}, ensure_ascii=False)

    except httpx.RequestError as exc:
        error_msg = f"Request failed: {str(exc)}"
        LOGGER.error(error_msg)
        return json.dumps({"error": error_msg, "query": query}, ensure_ascii=False)

    except Exception as exc:
        error_msg = f"Unexpected error: {str(exc)}"
        LOGGER.error(error_msg)
        return json.dumps({"error": error_msg, "query": query}, ensure_ascii=False)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


def main():
    """CLI entry point for running the MCP server."""
    parser = argparse.ArgumentParser(
        description="Run the web crawler & search MCP server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
    SEARXNG_URL       SearXNG instance URL (default: http://localhost:8888)
    SEARXNG_USERNAME  Optional basic auth username
    SEARXNG_PASSWORD  Optional basic auth password

Examples:
    # STDIO transport (default, for Claude Desktop)
    python -m crawler.mcp_server

    # HTTP transport (for remote access)
    python -m crawler.mcp_server --transport http --port 8000

    # Custom host/port
    python -m crawler.mcp_server --transport http --host 0.0.0.0 --port 9000

    # With custom SearXNG instance
    SEARXNG_URL=https://search.example.com python -m crawler.mcp_server
""",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to for HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to for HTTP transport (default: 8000)",
    )

    args = parser.parse_args()

    # Log configuration
    LOGGER.info("SearXNG URL: %s", SEARXNG_URL)
    LOGGER.info("SearXNG Auth: %s", "Enabled" if SEARXNG_USERNAME else "Disabled")

    if args.transport == "http":
        LOGGER.info("Starting MCP server on http://%s:%d/mcp", args.host, args.port)
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        LOGGER.info("Starting MCP server with STDIO transport")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
