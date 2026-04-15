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

import logging
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
                "Please edit it with your SEARXNG_URL.",
                CONFIG_ENV_FILE,
            )
            load_dotenv(CONFIG_ENV_FILE)
        except OSError:
            pass  # Silently continue without config
