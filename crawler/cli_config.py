"""Configuration loading helpers for CLI entrypoints."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable


def load_config(
    *,
    config_dir: Path,
    config_env_file: Path,
    cwd: Path,
    load_env: Callable[[Path], bool],
    copy_file: Callable[[Path, Path], str],
) -> None:
    """Load .env configuration with fallback to user config directory."""
    local_env = cwd / ".env"
    if local_env.is_file():
        load_env(local_env)
        return

    if config_env_file.is_file():
        load_env(config_env_file)
        return

    package_dir = Path(__file__).parent.parent
    example_file = package_dir / ".env.example"

    if example_file.is_file():
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            copy_file(example_file, config_env_file)
            logging.info(
                "Created config file at %s from .env.example. "
                "Please edit it with your SEARXNG_URL.",
                config_env_file,
            )
            load_env(config_env_file)
        except OSError:
            pass
