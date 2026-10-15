"""Shared environment / .env configuration loading.

Provides a single ``load_config`` function used by both the CLI
(``crawler.cli``) and the MCP server (``crawler.mcp_server``) so that
``~/.config/searxncrawl/.env`` is respected everywhere.

Search order:
1. ``.env`` in the current working directory
2. ``~/.config/searxncrawl/.env``

If neither exists and ``.env.example`` is found in the package root,
it is copied to ``~/.config/searxncrawl/.env`` as a starting template.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

# Configuration directory for global CLI / MCP usage
CONFIG_DIR = Path.home() / ".config" / "searxncrawl"
CONFIG_ENV_FILE = CONFIG_DIR / ".env"


def load_config() -> None:
    """Load ``.env`` configuration with fallback to user config directory.

    Search order:
    1. ``.env`` in current working directory
    2. ``~/.config/searxncrawl/.env``

    If neither exists and ``.env.example`` is found in the package
    directory, it will be copied to ``~/.config/searxncrawl/.env`` as a
    starting point.
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

    # No .env found — try to create config from .env.example
    package_dir = Path(__file__).parent.parent
    example_file = package_dir / ".env.example"

    if example_file.is_file():
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy(example_file, CONFIG_ENV_FILE)
            logging.info(
                "Created config file at %s from .env.example. "
                "Please edit it and set SEARXNG_URL and/or YDC_API_KEY.",
                CONFIG_ENV_FILE,
            )
            load_dotenv(CONFIG_ENV_FILE)
        except OSError:
            pass  # Silently continue without config


def _resolve_header_value(value: str) -> str:
    """Resolve a header value, supporting ``@/path`` file references.

    A value starting with ``@`` is treated as a file path (``~`` and
    relative paths are resolved against the home/cwd); the file content
    is used as the header value with surrounding whitespace stripped.
    Can be used to keep centralized secrets out of the ``.env`` file.
    """
    if not value.startswith("@"):
        return value
    path = Path(value[1:]).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.is_file():
        raise FileNotFoundError(
            f"SEARXNG_EXTRA_HEADERS value file not found: {path}"
        )
    return path.read_text(encoding="utf-8").strip()


def searxng_extra_headers() -> dict[str, str]:
    """Parse ``SEARXNG_EXTRA_HEADERS`` as a JSON object of extra HTTP headers.

    Example value::

        SEARXNG_EXTRA_HEADERS={"CF-Access-Client-Id": "@/some/file/path/cloudflare_id", "CF-Access-Client-Secret": "@/some/file/path/cloudflare_secret"}

    Unset or empty means no extra headers. Values of the form ``@/path``
    are loaded from a file. Invalid JSON is logged and ignored so a
    broken value cannot take a search run down.
    """
    raw = os.getenv("SEARXNG_EXTRA_HEADERS")
    if not raw or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw.strip())
    except json.JSONDecodeError:
        logging.getLogger(__name__).warning(
            "SEARXNG_EXTRA_HEADERS is not valid JSON; ignoring it"
        )
        return {}
    if not isinstance(parsed, dict):
        logging.getLogger(__name__).warning(
            "SEARXNG_EXTRA_HEADERS must be a JSON object; ignoring it"
        )
        return {}
    try:
        return {
            str(key): _resolve_header_value(str(val))
            for key, val in parsed.items()
        }
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "SEARXNG_EXTRA_HEADERS value file unreadable: %s", exc
        )
        return {}
