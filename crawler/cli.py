"""Command-line interface for the standalone crawler and search."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

# Configuration directory for global CLI usage
CONFIG_DIR = Path.home() / ".config" / "searxncrawl"
CONFIG_ENV_FILE = CONFIG_DIR / ".env"


def _load_config() -> None:
    """Load .env configuration with fallback to user config directory.

    Search order:
    1. .env in current working directory
    2. ~/.config/searxncrawl/.env

    If neither exists and .env.example is found in the package directory,
    it will be copied to ~/.config/searxncrawl/.env as a starting point.
    """
    # First, try current directory
    local_env = Path.cwd() / ".env"
    if local_env.is_file():
        load_dotenv(local_env)
        return

    # Second, try user config directory
    if CONFIG_ENV_FILE.is_file():
        load_dotenv(CONFIG_ENV_FILE)
        return

    # No .env found - try to create config from .env.example
    package_dir = Path(__file__).parent.parent
    example_file = package_dir / ".env.example"

    if example_file.is_file():
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy(example_file, CONFIG_ENV_FILE)
            logging.info(
                "Created config file at %s from .env.example. "
                "Please edit it with your SEARXNG_URL.",
                CONFIG_ENV_FILE,
            )
            load_dotenv(CONFIG_ENV_FILE)
        except OSError:
            pass  # Silently continue without config


_load_config()

from .document import CrawledDocument
from .session_capture import (
    CdpSessionEntry,
    capture_session_async,
    export_cdp_storage_state_async,
    list_cdp_sessions_async,
)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def _strip_markdown_links(text: str) -> str:
    """Remove markdown links from text, keeping only the link text."""
    # Replace [text](url) with just text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove standalone URLs (http/https)
    text = re.sub(r"https?://\S+", "", text)
    # Clean up any double spaces left behind
    text = re.sub(r"  +", " ", text)
    return text


def _format_search_markdown(data: Dict[str, Any]) -> str:
    """Format search results as markdown.

    Example output:
    # Search: python tutorials

    ## 1. Python Tutorial - W3Schools
    https://www.w3schools.com/python/

    Well organized tutorials with examples...

    ---
    """
    lines = []
    query = data.get("query", "")
    results = data.get("results", [])

    lines.append(f"# Search: {query}")
    lines.append(f"_Found {len(results)} results_")
    lines.append("")

    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = result.get("content", "")

        lines.append(f"## {i}. {title}")
        lines.append(url)
        lines.append("")
        if content:
            lines.append(content)
            lines.append("")
        lines.append("---")
        lines.append("")

    # Add suggestions if available
    suggestions = data.get("suggestions", [])
    if suggestions:
        lines.append("**Related searches:** " + ", ".join(suggestions[:5]))
        lines.append("")

    return "\n".join(lines)


def _doc_to_dict(doc: CrawledDocument) -> dict:
    """Convert document to JSON-serializable dict."""
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


def _url_to_filename(url: str) -> str:
    """Convert URL to a safe filename."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_") or "index"
    host = parsed.netloc.replace(":", "_").replace(".", "_")
    return f"{host}_{path}"[:100]


def _write_output(
    docs: List[CrawledDocument],
    output: Optional[str],
    json_output: bool,
    remove_links: bool = False,
) -> None:
    """Write documents to output destination."""
    # Apply link removal if requested
    if remove_links and not json_output:
        for doc in docs:
            doc.markdown = _strip_markdown_links(doc.markdown)

    if len(docs) == 1 and output is None:
        # Single doc, no output specified -> stdout
        doc = docs[0]
        if json_output:
            doc_dict = _doc_to_dict(doc)
            if remove_links and doc_dict.get("markdown"):
                doc_dict["markdown"] = _strip_markdown_links(doc_dict["markdown"])
            print(json.dumps(doc_dict, indent=2, ensure_ascii=False))
        else:
            print(doc.markdown)
        return

    if len(docs) == 1 and output and not output.endswith("/"):
        # Single doc, output is a file
        doc = docs[0]
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        if json_output:
            doc_dict = _doc_to_dict(doc)
            if remove_links and doc_dict.get("markdown"):
                doc_dict["markdown"] = _strip_markdown_links(doc_dict["markdown"])
            path.write_text(json.dumps(doc_dict, indent=2, ensure_ascii=False))
        else:
            path.write_text(doc.markdown)
        logging.info("Wrote %s", path)
        return

    # Multiple docs -> output directory
    out_dir = Path(output) if output else Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)

    if json_output:
        # Write all docs as single JSON array
        all_docs = []
        for doc in docs:
            doc_dict = _doc_to_dict(doc)
            if remove_links and doc_dict.get("markdown"):
                doc_dict["markdown"] = _strip_markdown_links(doc_dict["markdown"])
            all_docs.append(doc_dict)
        out_path = out_dir / "crawl_results.json"
        out_path.write_text(json.dumps(all_docs, indent=2, ensure_ascii=False))
        logging.info("Wrote %d documents to %s", len(docs), out_path)
    else:
        # Write each doc as separate .md file
        for doc in docs:
            filename = _url_to_filename(doc.final_url) + ".md"
            path = out_dir / filename
            path.write_text(doc.markdown)
            logging.info("Wrote %s", path)


# =============================================================================
# CRAWL COMMAND
# =============================================================================


def _parse_crawl_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="crawl",
        description="Crawl web pages and extract markdown content.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Single page to stdout
  crawl https://example.com

  # Single page to file
  crawl https://example.com -o page.md

  # Multiple pages
  crawl https://example.com/page1 https://example.com/page2 -o output/

  # Site crawl with depth/page limits
  crawl https://docs.example.com --site --max-depth 2 --max-pages 10 -o docs/

  # Output as JSON (includes metadata)
  crawl https://example.com --json

  # Clean output without links
  crawl https://example.com --remove-links

  # Crawl with authenticated browser state
  crawl https://example.com --storage-state ./state.json
""",
    )

    parser.add_argument(
        "urls",
        nargs="+",
        help="URL(s) to crawl",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output file (single URL) or directory (multiple URLs/site crawl)",
    )
    parser.add_argument(
        "--site",
        action="store_true",
        help="Crawl entire site starting from URL (BFS strategy)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Maximum crawl depth for site crawling (default: 2)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=25,
        help="Maximum pages to crawl for site crawling (default: 25)",
    )
    parser.add_argument(
        "--include-subdomains",
        action="store_true",
        help="Include subdomains in site crawl",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Concurrent crawls for multiple URLs (default: 3)",
    )
    parser.add_argument(
        "--storage-state",
        type=str,
        default=None,
        help="Path to Playwright storage_state JSON for authenticated crawling",
    )
    parser.add_argument(
        "--dedup-mode",
        type=str,
        choices=["exact", "off"],
        default="exact",
        help="Markdown dedup mode (default: exact)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON (includes metadata and references)",
    )
    parser.add_argument(
        "--remove-links",
        action="store_true",
        help="Remove all links from markdown output",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args(argv)


async def _run_crawl_async(args: argparse.Namespace) -> int:
    """Main async entry point for crawl."""
    from . import crawl_page_async, crawl_pages_async, crawl_site_async

    docs: List[CrawledDocument] = []
    auth = (
        {"storage_state": args.storage_state}
        if getattr(args, "storage_state", None)
        else None
    )

    if args.site:
        if len(args.urls) > 1:
            logging.error("Site crawl only supports a single seed URL")
            return 1

        logging.info(
            "Starting site crawl: %s (max_depth=%d, max_pages=%d)",
            args.urls[0],
            args.max_depth,
            args.max_pages,
        )
        result = await crawl_site_async(
            args.urls[0],
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            include_subdomains=args.include_subdomains,
            dedup_mode=args.dedup_mode,
            auth=auth,
        )
        docs = result.documents
        logging.info(
            "Site crawl complete: %d pages (%d successful, %d failed)",
            result.stats.get("total_pages", 0),
            result.stats.get("successful_pages", 0),
            result.stats.get("failed_pages", 0),
        )

    elif len(args.urls) == 1:
        logging.info("Crawling: %s", args.urls[0])
        doc = await crawl_page_async(
            args.urls[0],
            dedup_mode=args.dedup_mode,
            auth=auth,
        )
        docs = [doc]

    else:
        logging.info("Crawling %d URLs...", len(args.urls))
        docs = await crawl_pages_async(
            args.urls,
            concurrency=args.concurrency,
            dedup_mode=args.dedup_mode,
            auth=auth,
        )

    # Filter out failed docs for reporting
    successful = [d for d in docs if d.status == "success"]
    failed = [d for d in docs if d.status == "failed"]

    if failed:
        for doc in failed:
            logging.warning("Failed: %s - %s", doc.request_url, doc.error_message)

    if not successful and not args.json_output:
        logging.error("All crawls failed")
        return 1

    _write_output(
        docs if args.json_output else successful,
        args.output,
        args.json_output,
        remove_links=args.remove_links,
    )

    return 0 if successful else 1


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for crawl command."""
    args = _parse_crawl_args(argv)
    _setup_logging(args.verbose)

    try:
        return asyncio.run(_run_crawl_async(args))
    except KeyboardInterrupt:
        logging.info("Interrupted")
        return 130
    except Exception as exc:
        logging.error("Error: %s", exc)
        if args.verbose:
            logging.exception("Full traceback:")
        return 1


# =============================================================================
# CAPTURE COMMAND
# =============================================================================


def _parse_capture_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="crawl-capture",
        description=(
            "Capture Playwright storage_state either via manual login flow "
            "or by exporting from a running CDP browser session."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Open login page and capture when redirected to dashboard
  crawl-capture --start-url https://example.com/login --completion-url 'https://example.com/dashboard.*' --output ./state.json

  # List selectable sessions from a running browser started with --remote-debugging-port
  crawl-capture --cdp-url http://127.0.0.1:9222 --list-sessions

  # Export selected CDP session storage state
  crawl-capture --cdp-url http://127.0.0.1:9222 --cdp-session 2 --output ./state.json

  # Overwrite existing state file
  crawl-capture --start-url https://example.com/login --completion-url 'https://example.com/app.*' --output ./state.json --overwrite
""",
    )

    parser.add_argument(
        "--start-url",
        type=str,
        default=None,
        help="Optional URL to open before manual login",
    )
    parser.add_argument(
        "--completion-url",
        type=str,
        default=None,
        help="Regex pattern that marks successful capture when current URL matches",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Target path for captured storage_state JSON",
    )
    parser.add_argument(
        "--cdp-url",
        type=str,
        default=None,
        help="CDP endpoint for existing browser (e.g. http://127.0.0.1:9222)",
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List selectable CDP sessions and exit (or combine with --output to continue)",
    )
    parser.add_argument(
        "--cdp-session",
        type=int,
        default=None,
        help="Session index from --list-sessions output to export",
    )
    parser.add_argument(
        "--select",
        action="store_true",
        help="Interactively select session index from listed CDP sessions",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Capture timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing storage_state file",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless (default: headed for manual login)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args(argv)


def _format_cdp_session(entry: CdpSessionEntry, session_index: int) -> str:
    url = entry.url or "(no active page URL)"
    title = f" | title={entry.title}" if entry.title else ""
    if entry.page_index is None:
        return (
            f"[{session_index}] context={entry.context_index}, page=<none>"
            f" | url={url}{title}"
        )
    return (
        f"[{session_index}] context={entry.context_index}, page={entry.page_index}"
        f" | url={url}{title}"
    )


def _print_cdp_sessions(sessions: List[CdpSessionEntry]) -> None:
    if not sessions:
        print("No selectable CDP sessions found.")
        return

    print("Selectable CDP sessions:")
    for idx, session in enumerate(sessions):
        print(f"  {_format_cdp_session(session, idx)}")


def _select_cdp_session_interactive(sessions: List[CdpSessionEntry]) -> int:
    if not sessions:
        raise ValueError("No selectable CDP sessions available")

    while True:
        raw = input("Select session index: ").strip()
        if not raw:
            print("Please enter a numeric index.")
            continue
        try:
            idx = int(raw)
        except ValueError:
            print("Invalid index. Enter a number from the list.")
            continue

        if 0 <= idx < len(sessions):
            return idx
        print(f"Index out of range. Valid range: 0..{len(sessions) - 1}")


def _resolve_cdp_session_index(
    args: argparse.Namespace, sessions: List[CdpSessionEntry]
) -> int:
    if args.cdp_session is not None:
        if 0 <= args.cdp_session < len(sessions):
            return int(args.cdp_session)
        raise ValueError(
            f"--cdp-session out of range: {args.cdp_session} "
            f"(valid: 0..{len(sessions) - 1})"
        )

    if args.select:
        return _select_cdp_session_interactive(sessions)

    if len(sessions) == 1:
        return 0

    raise ValueError(
        "Multiple CDP sessions found. Use --cdp-session <index> "
        "or --select (optionally with --list-sessions)."
    )


async def _run_capture_async(args: argparse.Namespace) -> int:
    cdp_url = getattr(args, "cdp_url", None)
    completion_url = getattr(args, "completion_url", None)
    output = getattr(args, "output", None)
    start_url = getattr(args, "start_url", None)
    timeout = float(getattr(args, "timeout", 300.0))
    overwrite = bool(getattr(args, "overwrite", False))
    headless = bool(getattr(args, "headless", False))
    list_sessions = bool(getattr(args, "list_sessions", False))
    cdp_session = getattr(args, "cdp_session", None)
    select = bool(getattr(args, "select", False))

    if cdp_url:
        if completion_url:
            raise ValueError(
                "--completion-url cannot be combined with --cdp-url; "
                "CDP export reads an existing browser session."
            )

        sessions = await list_cdp_sessions_async(cdp_url)

        if list_sessions:
            _print_cdp_sessions(sessions)
            if not output:
                return 0

        if not output:
            raise ValueError("--output is required when exporting from CDP")

        if not sessions:
            raise ValueError(
                "No selectable CDP sessions found. Open at least one tab in the browser first."
            )

        cdp_args = argparse.Namespace(cdp_session=cdp_session, select=select)
        selected_index = _resolve_cdp_session_index(cdp_args, sessions)
        selected = sessions[selected_index]
        result = await export_cdp_storage_state_async(
            output,
            cdp_url=cdp_url,
            context_index=selected.context_index,
            overwrite=overwrite,
        )
        logging.info(
            "CDP export success: %s (session=%d, context=%d)",
            result.storage_state_path,
            selected_index,
            selected.context_index,
        )
        return 0

    if list_sessions or cdp_session is not None or select:
        raise ValueError("--list-sessions/--cdp-session/--select require --cdp-url")

    if not completion_url:
        raise ValueError("--completion-url is required for manual login capture")

    if not output:
        raise ValueError("--output is required for manual login capture")

    result = await capture_session_async(
        output,
        completion_url_pattern=completion_url,
        start_url=start_url,
        timeout_seconds=timeout,
        overwrite=overwrite,
        headless=headless,
    )

    if result.status == "success":
        logging.info("Capture success: %s", result.storage_state_path)
        return 0

    if result.status == "timeout":
        logging.error("Capture timeout: %s", result.message)
        return 2

    logging.warning("Capture aborted: %s", result.message)
    return 130


def capture_main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for isolated session capture."""
    args = _parse_capture_args(argv)
    _setup_logging(args.verbose)

    try:
        return asyncio.run(_run_capture_async(args))
    except KeyboardInterrupt:
        logging.info("Interrupted")
        return 130
    except Exception as exc:
        logging.error("Error: %s", exc)
        if args.verbose:
            logging.exception("Full traceback:")
        return 1


# =============================================================================
# SEARCH COMMAND
# =============================================================================


def _parse_search_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="search",
        description="Search the web using SearXNG metasearch engine.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Basic search (markdown output)
  search "python tutorials"

  # Search with language
  search "Rezepte" --language de

  # Search with time filter
  search "latest AI news" --time-range week

  # JSON output
  search "python" --json

  # Output to file
  search "docker compose" --json -o results.json
""",
    )

    parser.add_argument(
        "query",
        help="Search query string",
    )
    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language code for results (default: en)",
    )
    parser.add_argument(
        "--time-range",
        type=str,
        choices=["day", "week", "month", "year"],
        default=None,
        help="Time range filter",
    )
    parser.add_argument(
        "--categories",
        type=str,
        nargs="+",
        default=None,
        help="Categories to search (e.g., general, images, news)",
    )
    parser.add_argument(
        "--engines",
        type=str,
        nargs="+",
        default=None,
        help="Specific search engines to use",
    )
    parser.add_argument(
        "--safesearch",
        type=int,
        choices=[0, 1, 2],
        default=1,
        help="Safe search level: 0 (off), 1 (moderate), 2 (strict)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum results to return (default: 10)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output file for JSON results",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON instead of markdown",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args(argv)


async def _run_search_async(args: argparse.Namespace) -> int:
    """Main async entry point for search."""
    searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8888")
    searxng_username = os.getenv("SEARXNG_USERNAME")
    searxng_password = os.getenv("SEARXNG_PASSWORD")

    logging.info("Searching for: %s", args.query)

    # Build search parameters
    params: Dict[str, Any] = {
        "q": args.query,
        "format": "json",
        "language": args.language,
        "safesearch": args.safesearch,
    }

    if args.time_range:
        params["time_range"] = args.time_range

    if args.categories:
        params["categories"] = ",".join(args.categories)

    if args.engines:
        params["engines"] = ",".join(args.engines)

    # Create HTTP client
    auth = None
    if searxng_username and searxng_password:
        auth = httpx.BasicAuth(searxng_username, searxng_password)

    try:
        async with httpx.AsyncClient(
            base_url=searxng_url,
            auth=auth,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        ) as client:
            response = await client.get("/search", params=params)
            response.raise_for_status()
            data = response.json()

        # Limit results
        max_results = min(max(1, args.max_results), 50)
        if "results" in data:
            data["results"] = data["results"][:max_results]
            data["number_of_results"] = len(data["results"])

        logging.info("Found %d results", data.get("number_of_results", 0))

        # Format output
        if args.json_output:
            output = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            output = _format_search_markdown(data)

        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output)
            logging.info("Wrote results to %s", path)
        else:
            print(output)

        return 0

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            logging.error(
                "Authentication failed. Check SEARXNG_USERNAME and SEARXNG_PASSWORD."
            )
        else:
            logging.error(
                "SearXNG API error: %d - %s",
                exc.response.status_code,
                exc.response.text,
            )
        return 1

    except httpx.RequestError as exc:
        logging.error("Request failed: %s", exc)
        return 1

    except Exception as exc:
        logging.error("Unexpected error: %s", exc)
        if args.verbose:
            logging.exception("Full traceback:")
        return 1


def search_main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for search command."""
    args = _parse_search_args(argv)
    _setup_logging(args.verbose)

    try:
        return asyncio.run(_run_search_async(args))
    except KeyboardInterrupt:
        logging.info("Interrupted")
        return 130
    except Exception as exc:
        logging.error("Error: %s", exc)
        if args.verbose:
            logging.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
