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
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove standalone URLs (http/https)
    text = re.sub(r'https?://\S+', '', text)
    # Clean up any double spaces left behind
    text = re.sub(r'  +', ' ', text)
    return text


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
        doc = await crawl_page_async(args.urls[0])
        docs = [doc]

    else:
        logging.info("Crawling %d URLs...", len(args.urls))
        docs = await crawl_pages_async(
            args.urls,
            concurrency=args.concurrency,
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
# SEARCH COMMAND
# =============================================================================


def _parse_search_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="search",
        description="Search the web using SearXNG metasearch engine.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Basic search
  search "python tutorials"

  # Search with language
  search "Rezepte" --language de

  # Search with time filter
  search "latest AI news" --time-range week

  # Limit results
  search "python" --max-results 5

  # Output to file
  search "docker compose" -o results.json
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

        # Output
        output_json = json.dumps(data, indent=2, ensure_ascii=False)

        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(output_json)
            logging.info("Wrote results to %s", path)
        else:
            print(output_json)

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
