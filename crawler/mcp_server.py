"""MCP Server for the standalone crawler + multi-provider web search.

Provides tools for:
- Crawling web pages and extracting markdown content
- Searching the web via the configured providers (SearXNG, You.com),
  queried in parallel and merged into one attributed result list

Supports both STDIO and HTTP transports.

Usage:
    # STDIO (for Claude Desktop, etc.)
    python -m crawler.mcp_server

    # HTTP (for remote access)
    python -m crawler.mcp_server --transport http --port 8000

    # HTTP with CORS enabled for specific origins
    python -m crawler.mcp_server --transport http --cors-origins "http://localhost:3000"

    # Or via FastMCP CLI
    fastmcp run crawler/mcp_server.py:mcp --transport http --port 8000

Environment Variables:
    SEARXNG_URL: SearXNG instance URL; enables SearXNG (no default)
    SEARXNG_USERNAME: Optional basic auth username (set both or neither)
    SEARXNG_PASSWORD: Optional basic auth password (set both or neither)
    YDC_API_KEY: You.com API key; enables You.com (queries go to You.com, US)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

from fastmcp import FastMCP

from . import search_orchestrator
from .document import CrawledDocument
from .env import load_config
from .search_orchestrator import (
    SearchProviderError,
    configured_providers,
    serialize_search_results,
)

# Load .env with config-dir fallback before reading environment variables
load_config()


def _resolve_log_level() -> tuple[str, int]:
    """Resolve LOG_LEVEL env var to a validated (label, int) pair."""
    raw_level = os.getenv("LOG_LEVEL", "INFO")
    if not raw_level:
        return "info", logging.INFO

    label = raw_level.strip().lower()
    level_int = getattr(logging, label.upper(), None)
    if isinstance(level_int, int):
        return label, level_int

    # Unknown value — fall back to INFO for both label and int
    return "info", logging.INFO


LOG_LEVEL_STR, LOG_LEVEL_INT = _resolve_log_level()

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL_INT,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
LOGGER = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP(
    name="Web Crawler & Search",
    instructions="""
    A web crawler and search server that provides:

    1. Web Crawling Tools:
       - crawl: Crawl one or more URLs and get markdown content
       - crawl_site: Crawl an entire website with depth/page limits

    2. Web Search Tool:
       - search: Search the web via the configured providers (SearXNG, You.com),
         queried in parallel; results are merged and attributed per provider

    Output formats for crawl tools:
    - markdown: Clean concatenated markdown (default)
    - json: Full details including metadata and references
    """,
)


class OutputFormat(str, Enum):
    """Output format for crawl results."""

    markdown = "markdown"
    json = "json"


def _configure_stdio_encoding() -> None:
    """Best-effort UTF-8 encoding for stdio transport streams."""
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        # Best-effort only: do not block MCP startup if unsupported.
        pass


def _parse_csv_allowlist(value: Optional[str]) -> Optional[List[str]]:
    """Normalize a comma-separated HTTP allowlist without adding defaults."""
    if value is None:
        return None

    entries = [entry.strip() for entry in value.split(",") if entry.strip()]
    return entries or None


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
    timeout: int = 15,
    remove_links: bool = False,
    dedup_mode: str = "exact",
    storage_state: Optional[str] = None,
):
    """
    Crawl one or more URLs and extract content as markdown or JSON.

    Args:
        urls: List of URLs to crawl (required). Accepts a single URL or multiple URLs.
        output_format: 'markdown' (default) or 'json'
            - markdown: Clean concatenated markdown with URL headers and timestamps
            - json: Full JSON with metadata, references, and statistics
        concurrency: Maximum concurrent crawls (default: 3)
        timeout: Per-URL timeout in seconds (default: 15, must be >= 1)
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

    if timeout < 1:
        raise ValueError("timeout must be >= 1")

    # Validate output format
    try:
        fmt = OutputFormat(output_format.lower())
    except ValueError:
        fmt = OutputFormat.markdown

    LOGGER.info("Crawling %d URL(s)...", len(urls))
    auth = {"storage_state": storage_state} if storage_state else None

    if len(urls) == 1:
        try:
            doc = await crawl_page_async(
                urls[0], dedup_mode=dedup_mode, auth=auth, timeout=timeout
            )
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
            timeout=timeout,
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
    timeout: int = 120,
    remove_links: bool = False,
    dedup_mode: str = "exact",
    storage_state: Optional[str] = None,
):
    """
    Crawl an entire website starting from a seed URL using DFS strategy.

    Args:
        url: The seed URL to start crawling from
        max_depth: Maximum depth to crawl (default: 2, 0 = seed page only)
        max_pages: Maximum number of pages to crawl (default: 25)
        include_subdomains: Whether to include subdomains in the crawl (default: false)
        output_format: Output format - "markdown" (default) or "json"
            - markdown: Clean concatenated markdown with URL headers and timestamps
            - json: Full JSON with metadata, references, and crawl statistics
        timeout: Overall site crawl timeout in seconds (default: 120, must be >= 1)
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

    if timeout < 1:
        raise ValueError("timeout must be >= 1")

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

    try:
        result = await crawl_site_async(
            url,
            max_depth=max_depth,
            max_pages=max_pages,
            include_subdomains=include_subdomains,
            dedup_mode=dedup_mode,
            auth={"storage_state": storage_state} if storage_state else None,
            timeout=timeout,
        )
    except TimeoutError:
        timeout_doc = CrawledDocument(
            request_url=url,
            final_url=url,
            status="failed",
            markdown="",
            error_message="Site crawl timed out",
        )
        timeout_stats = {
            "total_pages": 1,
            "successful_pages": 0,
            "failed_pages": 1,
            "error_count": 1,
        }
        return _format_output(
            [timeout_doc], fmt, stats=timeout_stats, remove_links=remove_links
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
# SEARCH TOOL
# =============================================================================


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
    max_retries: int = 3,
    providers: Optional[List[str]] = None,
):
    """
    Search the web via the configured search providers (SearXNG, You.com).

    All configured providers are queried in parallel. Their results are merged
    (URL dedup, round-robin, results found by several providers first) and each
    result lists the providers that returned it.

    Args:
        query: Search query string (required)
        language: Language code for results (e.g., 'en', 'de', 'fr'). Default: 'en'
        time_range: Time range filter - 'day', 'week', 'month', or 'year'. Default: None (no filter)
        categories: SearXNG only. Categories to search (e.g., ['general', 'images', 'news']). Default: None (all)
        engines: SearXNG only. Specific search engines to use. Default: None (all available)
        safesearch: Safe search level - 0 (off), 1 (moderate), 2 (strict). Default: 1
        pageno: Page number for results (minimum 1). Default: 1
        max_results: Maximum results to return (1-50). Default: 10
        max_retries: Maximum attempts per provider for transient request errors (default: 3)
        providers: Subset of configured providers to query ('searxng', 'youcom').
            Default: None (all configured providers)

    Returns:
        JSON string {query, number_of_results, results}. Each result has
        title, url, content, publishedDate and providers.
        SEARCH_RESULT_FIELDS (comma-separated) limits the fields per result;
        unset/empty returns all of them.
        If some providers fail, the results of the others are returned. If all
        selected providers fail (or none is configured), the JSON contains
        "error" with a short reason per provider, and "query".

    Examples:
        # Basic search
        search(query="python tutorials")

        # Search with time filter
        search(query="latest AI news", time_range="week")

        # Only one provider
        search(query="python tutorials", providers=["searxng"])

        # Search in German
        search(query="Rezepte", language="de")
    """
    LOGGER.info("Searching for: %s", query)
    start = time.monotonic()

    try:
        results = await search_orchestrator.search(
            query,
            language=language,
            time_range=time_range,
            categories=categories,
            engines=engines,
            safesearch=safesearch,
            pageno=pageno,
            max_results=max_results,
            max_retries=max_retries,
            providers=providers,
        )
        data = serialize_search_results(query, results)

        elapsed = time.monotonic() - start
        LOGGER.info(
            "Search returned %d results in %.1fs",
            data["number_of_results"],
            elapsed,
        )

        return json.dumps(data, indent=2, ensure_ascii=False)

    except SearchProviderError as exc:
        elapsed = time.monotonic() - start
        LOGGER.error("Search failed in %.1fs: %s", elapsed, exc)
        return json.dumps({"error": str(exc), "query": query}, ensure_ascii=False)

    except Exception as exc:
        elapsed = time.monotonic() - start
        error_msg = f"Unexpected error: {str(exc)}"
        LOGGER.error("Search failed in %.1fs: %s", elapsed, error_msg)
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
    SEARXNG_URL       SearXNG instance URL; enables SearXNG (no default)
    SEARXNG_USERNAME  Optional basic auth username (set both or neither)
    SEARXNG_PASSWORD  Optional basic auth password (set both or neither)
    YDC_API_KEY       You.com API key; enables You.com (queries go to You.com, US)

Examples:
    # STDIO transport (default, for Claude Desktop)
    python -m crawler.mcp_server

    # HTTP transport (for remote access)
    python -m crawler.mcp_server --transport http --port 8000

    # Custom host/port
    python -m crawler.mcp_server --transport http --host 0.0.0.0 --port 9000

    # Enable CORS for specific origins (required for browser-based MCP clients)
    python -m crawler.mcp_server --transport http --cors-origins "http://localhost:3000,https://myapp.com"

    # Enable CORS for all origins (use with caution)
    python -m crawler.mcp_server --transport http --cors-origins "*"

    # With a SearXNG instance as search provider
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
    parser.add_argument(
        "--allowed-hosts",
        default=None,
        help=(
            "Comma-separated Host headers allowed for HTTP transport. "
            "This is separate from the bind address. "
            'Use "*" only to explicitly allow every Host.'
        ),
    )
    parser.add_argument(
        "--cors-origins",
        default=None,
        help=(
            "Comma-separated list of allowed CORS origins for HTTP transport. "
            'Use "*" to allow all origins. '
            "If not set, no CORS headers are sent. "
            'Example: --cors-origins "http://localhost:3000,https://myapp.com"'
        ),
    )

    args = parser.parse_args()

    # Log configuration
    try:
        from importlib.metadata import version as _pkg_version

        LOGGER.info("searxNcrawl v%s starting", _pkg_version("searxNcrawl"))
    except Exception:
        LOGGER.info("searxNcrawl starting")
    LOGGER.info(
        "Search providers: %s",
        ", ".join(configured_providers())
        or "none (set a valid http(s) SEARXNG_URL and/or YDC_API_KEY)",
    )

    if args.transport == "http":
        LOGGER.info("Starting MCP server on http://%s:%d/mcp", args.host, args.port)

        run_kwargs: dict[str, Any] = {
            "transport": "http",
            "host": args.host,
            "port": args.port,
        }

        allowed_hosts = _parse_csv_allowlist(args.allowed_hosts)
        if allowed_hosts is not None:
            LOGGER.info("Allowing HTTP Host headers: %s", allowed_hosts)
            run_kwargs["allowed_hosts"] = allowed_hosts

        origins = _parse_csv_allowlist(args.cors_origins)
        if origins is not None:
            from starlette.middleware import Middleware
            from starlette.middleware.cors import CORSMiddleware

            LOGGER.info("CORS enabled for origins: %s", origins)
            run_kwargs["allowed_origins"] = origins
            run_kwargs["middleware"] = [
                Middleware(
                    CORSMiddleware,
                    allow_origins=origins,
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                ),
            ]

        run_kwargs["log_level"] = LOG_LEVEL_STR
        mcp.run(**run_kwargs)
    else:
        _configure_stdio_encoding()
        LOGGER.info("Starting MCP server with STDIO transport")
        mcp.run(transport="stdio", log_level=LOG_LEVEL_STR)


if __name__ == "__main__":
    main()
