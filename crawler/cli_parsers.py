"""Argument parser construction for CLI commands."""

from __future__ import annotations

import argparse
from typing import Callable, List, Optional


def _add_crawl_args(
    parser: argparse.ArgumentParser,
    add_auth_args: Callable[[argparse.ArgumentParser], None],
) -> None:
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

    spa_group = parser.add_argument_group("SPA / JavaScript rendering")
    spa_group.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Seconds to wait after page load before extracting content. "
             "Essential for SPA/JS-rendered pages (e.g. --delay 3)",
    )
    spa_group.add_argument(
        "--wait-until",
        type=str,
        default=None,
        choices=["load", "domcontentloaded", "networkidle", "commit"],
        help="Page load event to wait for (default: load). "
             "Use 'networkidle' for SPA pages that fetch data via API calls",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    add_auth_args(parser)


def _add_capture_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Login page URL to navigate to",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="auth_state.json",
        help="Output path for storage state JSON (default: auth_state.json)",
    )
    parser.add_argument(
        "--wait-for-url",
        type=str,
        default=None,
        help="Regex pattern: auto-capture when browser URL matches",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds for login completion (default: 300)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Profile name or path for persistent browser session. "
             "Named profiles are stored under ~/.crawl4ai/profiles/<name>. "
             "Cookies and localStorage survive across sessions.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )


def _build_crawl_root_parser(
    add_auth_args: Callable[[argparse.ArgumentParser], None],
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crawl",
        description="Crawl web pages and extract markdown content.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    crawl_parser = subparsers.add_parser(
        "crawl",
        help=argparse.SUPPRESS,
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

  # SPA / JS-rendered pages (wait for content to load)
  crawl https://spa.example.com --delay 3 --wait-until networkidle

  # Authenticated crawl with storage state
  crawl --storage-state auth_state.json https://protected.example.com

  # Combined: authenticated SPA crawl
  crawl --storage-state auth.json --delay 3 --wait-until networkidle https://spa.example.com

  # Capture auth session interactively
  crawl capture-auth --url https://login.example.com --output auth_state.json
""",
    )
    _add_crawl_args(crawl_parser, add_auth_args)

    capture_parser = subparsers.add_parser(
        "capture-auth",
        description="Capture authentication session via interactive browser login.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  # Open browser for login, export storage state
  crawl capture-auth --url https://login.example.com

  # Export to specific file
  crawl capture-auth --url https://login.example.com --output my_auth.json

  # Use persistent browser profile (cookies survive restarts)
  crawl capture-auth --url https://login.example.com --profile my-site

  # Auto-capture when redirected to dashboard
  crawl capture-auth --url https://login.example.com --wait-for-url "/dashboard"

  # With custom timeout
  crawl capture-auth --url https://login.example.com --timeout 600
""",
    )
    _add_capture_auth_args(capture_parser)

    return parser


def _normalize_crawl_argv(argv: Optional[List[str]]) -> List[str]:
    effective_argv = list(argv) if argv is not None else []
    if not effective_argv:
        return ["crawl"]

    if effective_argv[0] in {"crawl", "capture-auth"}:
        return effective_argv

    return ["crawl", *effective_argv]


def parse_crawl_args(
    argv: Optional[List[str]],
    add_auth_args: Callable[[argparse.ArgumentParser], None],
) -> argparse.Namespace:
    parser = _build_crawl_root_parser(add_auth_args)
    args = parser.parse_args(_normalize_crawl_argv(argv))
    if not hasattr(args, "command"):
        args.command = "crawl"
    args.capture_auth = args.command == "capture-auth"
    return args


def parse_capture_auth_args(
    argv: Optional[List[str]],
    add_auth_args: Callable[[argparse.ArgumentParser], None],
) -> argparse.Namespace:
    parser = _build_crawl_root_parser(add_auth_args)
    effective_argv = list(argv) if argv is not None else []
    args = parser.parse_args(["capture-auth", *effective_argv])
    args.command = "capture-auth"
    args.capture_auth = True
    return args


def parse_search_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
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
