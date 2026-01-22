"""Command-line interface for the standalone crawler."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

from .document import CrawledDocument


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="crawl",
        description="Crawl web pages and extract markdown content.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
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
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args(argv)


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
) -> None:
    """Write documents to output destination."""
    if len(docs) == 1 and output is None:
        # Single doc, no output specified -> stdout
        doc = docs[0]
        if json_output:
            print(json.dumps(_doc_to_dict(doc), indent=2))
        else:
            print(doc.markdown)
        return

    if len(docs) == 1 and output and not output.endswith("/"):
        # Single doc, output is a file
        doc = docs[0]
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        if json_output:
            path.write_text(json.dumps(_doc_to_dict(doc), indent=2))
        else:
            path.write_text(doc.markdown)
        logging.info("Wrote %s", path)
        return

    # Multiple docs -> output directory
    out_dir = Path(output) if output else Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)

    if json_output:
        # Write all docs as single JSON array
        all_docs = [_doc_to_dict(doc) for doc in docs]
        out_path = out_dir / "crawl_results.json"
        out_path.write_text(json.dumps(all_docs, indent=2))
        logging.info("Wrote %d documents to %s", len(docs), out_path)
    else:
        # Write each doc as separate .md file
        for doc in docs:
            filename = _url_to_filename(doc.final_url) + ".md"
            path = out_dir / filename
            path.write_text(doc.markdown)
            logging.info("Wrote %s", path)


async def _run_async(args: argparse.Namespace) -> int:
    """Main async entry point."""
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
        docs if args.json_output else successful, args.output, args.json_output
    )

    return 0 if successful else 1


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    args = _parse_args(argv)
    _setup_logging(args.verbose)

    try:
        return asyncio.run(_run_async(args))
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
