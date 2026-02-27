"""Command-line interface for the standalone crawler and search."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Configuration directory for global CLI usage
CONFIG_DIR = Path.home() / ".config" / "searxncrawl"
CONFIG_ENV_FILE = CONFIG_DIR / ".env"


def _load_config() -> None:
    """Load .env configuration with fallback to user config directory."""
    from .cli_config import load_config

    load_config(
        config_dir=CONFIG_DIR,
        config_env_file=CONFIG_ENV_FILE,
        cwd=Path.cwd(),
        load_env=load_dotenv,
        copy_file=shutil.copy,
    )


_load_config()

from .auth import AuthConfig, load_auth_from_env  # noqa: E402
from .cli_auth import add_auth_args as _add_auth_args_impl  # noqa: E402
from .cli_auth import build_cli_auth as _build_cli_auth_impl  # noqa: E402
from .cli_output import doc_to_dict as _doc_to_dict  # noqa: E402
from .cli_output import format_search_markdown as _format_search_markdown  # noqa: E402
from .cli_output import strip_markdown_links as _strip_markdown_links  # noqa: E402
from .cli_output import url_to_filename as _url_to_filename  # noqa: E402
from .cli_output import write_output as _write_output  # noqa: E402
from .cli_parsers import parse_capture_auth_args as _parse_capture_auth_args_impl  # noqa: E402
from .cli_parsers import parse_crawl_args as _parse_crawl_args_impl  # noqa: E402
from .cli_parsers import parse_search_args as _parse_search_args_impl  # noqa: E402
from .document import CrawledDocument  # noqa: E402


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def _build_cli_auth(args: argparse.Namespace) -> Optional[AuthConfig]:
    """Build AuthConfig from CLI arguments, falling back to env vars."""
    return _build_cli_auth_impl(args, auth_loader=load_auth_from_env)


def _add_auth_args(parser: argparse.ArgumentParser) -> None:
    """Add authentication arguments to an argparse parser."""
    _add_auth_args_impl(parser)


def _parse_crawl_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    return _parse_crawl_args_impl(argv, _add_auth_args)


def _parse_capture_auth_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    return _parse_capture_auth_args_impl(argv, _add_auth_args)


def _parse_search_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    return _parse_search_args_impl(argv)


async def _run_crawl_async(args: argparse.Namespace) -> int:
    """Main async entry point for crawl."""
    from . import crawl_page_async, crawl_pages_async, crawl_site_async
    from .config import build_markdown_run_config

    auth = _build_cli_auth(args)
    if auth:
        logging.info("Authentication enabled")

    run_config = None
    delay = getattr(args, "delay", None)
    wait_until = getattr(args, "wait_until", None)
    if delay is not None or wait_until is not None:
        run_config = build_markdown_run_config()
        if delay is not None:
            run_config.delay_before_return_html = delay
            logging.info("SPA delay: %.1fs after page load", delay)
        if wait_until is not None:
            run_config.wait_until = wait_until
            logging.info("Page wait strategy: %s", wait_until)

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
            auth=auth,
            run_config=run_config,
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
        doc = await crawl_page_async(args.urls[0], config=run_config, auth=auth)
        docs = [doc]

    else:
        logging.info("Crawling %d URLs...", len(args.urls))
        docs = await crawl_pages_async(
            args.urls,
            config=run_config,
            concurrency=args.concurrency,
            auth=auth,
        )

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


async def _run_capture_auth_async(args: argparse.Namespace) -> int:
    """Run the capture-auth subcommand."""
    from .capture import capture_auth_state

    try:
        await capture_auth_state(
            url=args.url,
            output_path=args.output,
            wait_for_url=args.wait_for_url,
            timeout=args.timeout,
            profile=getattr(args, "profile", None),
        )
        return 0
    except Exception as exc:
        logging.error("Capture failed: %s", exc)
        if args.verbose:
            logging.exception("Full traceback:")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for crawl command."""
    args = _parse_crawl_args(argv)
    _setup_logging(args.verbose)

    is_capture_auth = getattr(args, "command", None) == "capture-auth" or getattr(
        args, "capture_auth", False
    )
    runner = _run_capture_auth_async if is_capture_auth else _run_crawl_async

    try:
        return asyncio.run(runner(args))
    except KeyboardInterrupt:
        logging.info("Interrupted")
        return 130
    except Exception as exc:
        logging.error("Error: %s", exc)
        if args.verbose and not is_capture_auth:
            logging.exception("Full traceback:")
        return 1


async def _run_search_async(args: argparse.Namespace) -> int:
    """Main async entry point for search."""
    from .search import SearchError, search_async

    logging.info("Searching for: %s", args.query)

    try:
        result = await search_async(
            args.query,
            language=args.language,
            time_range=args.time_range,
            categories=args.categories,
            engines=args.engines,
            safesearch=args.safesearch,
            pageno=args.pageno,
            max_results=args.max_results,
        )
    except SearchError as exc:
        logging.error(str(exc))
        return 1
    except Exception as exc:
        logging.error("Unexpected error: %s", exc)
        if args.verbose:
            logging.exception("Full traceback:")
        return 1

    logging.info("Found %d results", result.number_of_results)

    data = result.to_dict()
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
