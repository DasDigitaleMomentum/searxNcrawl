"""Authentication configuration for crawling protected pages.

This module provides the AuthConfig dataclass and helpers to build
crawl4ai BrowserConfig instances with cookies, headers, storage state,
and persistent browser profiles.

Example usage:

    from crawler.auth import AuthConfig, build_browser_config

    # With cookies
    auth = AuthConfig(
        cookies=[{"name": "sid", "value": "abc123", "domain": ".example.com"}]
    )
    browser_cfg = build_browser_config(auth)

    # With storage state file (from capture-auth)
    auth = AuthConfig(storage_state="./auth_state.json")
    browser_cfg = build_browser_config(auth)

    # With bearer token header
    auth = AuthConfig(headers={"Authorization": "Bearer xyz"})
    browser_cfg = build_browser_config(auth)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from crawl4ai import BrowserConfig

LOGGER = logging.getLogger(__name__)

# Default directory for auth profiles
DEFAULT_PROFILES_DIR = Path.home() / ".crawl4ai" / "profiles"


@dataclass
class AuthConfig:
    """Authentication configuration for crawling protected pages.

    All fields are optional and composable -- you can combine cookies
    with headers, or use a storage state file alone.

    Attributes:
        cookies: List of cookie dicts with 'name', 'value', 'domain' keys.
            Optionally include 'path', 'secure', 'httpOnly', 'sameSite'.
        headers: Dict of custom HTTP headers (e.g. Authorization).
        storage_state: Path to a Playwright storage state JSON file.
        storage_state_data: Inline storage state as a dict (alternative
            to file path).
        user_data_dir: Path to a persistent browser profile directory.
        use_persistent_context: Whether to use a persistent browser context.
            Automatically set to True if user_data_dir is provided.
    """

    cookies: Optional[List[Dict[str, Any]]] = None
    headers: Optional[Dict[str, str]] = None
    storage_state: Optional[str] = None
    storage_state_data: Optional[Dict[str, Any]] = None
    user_data_dir: Optional[str] = None
    use_persistent_context: bool = False

    def __post_init__(self) -> None:
        """Auto-enable persistent context when user_data_dir is set."""
        if self.user_data_dir and not self.use_persistent_context:
            self.use_persistent_context = True

    @property
    def is_empty(self) -> bool:
        """Return True if no auth configuration is set."""
        return (
            not self.cookies
            and not self.headers
            and not self.storage_state
            and not self.storage_state_data
            and not self.user_data_dir
        )

    def resolved_storage_state(self) -> Optional[Dict[str, Any]]:
        """Resolve storage state from file path or inline data."""
        if self.storage_state_data:
            return self.storage_state_data
        if self.storage_state:
            path = Path(self.storage_state).expanduser()
            if not path.is_file():
                raise FileNotFoundError(
                    f"Storage state file not found: {path}"
                )
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            LOGGER.info("Loaded storage state from %s", path)
            return data
        return None


def build_browser_config(auth: Optional[AuthConfig] = None) -> BrowserConfig:
    """Build a crawl4ai BrowserConfig with auth parameters.

    Args:
        auth: Optional AuthConfig. If None or empty, returns a default
            non-authenticated BrowserConfig.

    Returns:
        BrowserConfig ready to pass to AsyncWebCrawler.
    """
    if auth is None or auth.is_empty:
        return BrowserConfig(use_persistent_context=False)

    kwargs: Dict[str, Any] = {}

    # Cookies
    if auth.cookies:
        kwargs["cookies"] = auth.cookies
        LOGGER.info("Auth: injecting %d cookie(s)", len(auth.cookies))

    # Headers
    if auth.headers:
        kwargs["headers"] = auth.headers
        LOGGER.info(
            "Auth: injecting %d custom header(s)",
            len(auth.headers),
        )

    # Storage state
    resolved_state = auth.resolved_storage_state()
    if resolved_state:
        kwargs["storage_state"] = resolved_state
        LOGGER.info("Auth: using storage state")

    # Persistent browser profile
    if auth.user_data_dir:
        kwargs["user_data_dir"] = auth.user_data_dir
        kwargs["use_persistent_context"] = True
        LOGGER.info("Auth: using persistent profile at %s", auth.user_data_dir)
    else:
        kwargs["use_persistent_context"] = auth.use_persistent_context

    return BrowserConfig(**kwargs)


def load_auth_from_env() -> Optional[AuthConfig]:
    """Load auth configuration from environment variables.

    Supported variables:
        CRAWL_AUTH_STORAGE_STATE: Path to storage state JSON file.
        CRAWL_AUTH_COOKIES_FILE: Path to cookies JSON file (list of dicts).
        CRAWL_AUTH_PROFILE: Path to persistent browser profile directory.

    Returns:
        AuthConfig if any env vars are set, None otherwise.
    """
    storage_state = os.environ.get("CRAWL_AUTH_STORAGE_STATE")
    cookies_file = os.environ.get("CRAWL_AUTH_COOKIES_FILE")
    profile = os.environ.get("CRAWL_AUTH_PROFILE")

    if not any([storage_state, cookies_file, profile]):
        return None

    cookies = None
    if cookies_file:
        path = Path(cookies_file).expanduser()
        if path.is_file():
            with open(path, "r", encoding="utf-8") as fh:
                cookies = json.load(fh)
            LOGGER.info("Loaded %d cookie(s) from %s", len(cookies), path)
        else:
            LOGGER.warning("Cookies file not found: %s", path)

    return AuthConfig(
        storage_state=storage_state,
        cookies=cookies,
        user_data_dir=profile,
    )


def load_auth_from_file(path: str) -> AuthConfig:
    """Load auth configuration from a JSON config file.

    The file should contain a JSON object with optional keys:
    'cookies', 'headers', 'storage_state', 'user_data_dir'.

    Args:
        path: Path to the auth config JSON file.

    Returns:
        AuthConfig populated from the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    config_path = Path(path).expanduser()
    if not config_path.is_file():
        raise FileNotFoundError(f"Auth config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    return AuthConfig(
        cookies=data.get("cookies"),
        headers=data.get("headers"),
        storage_state=data.get("storage_state"),
        user_data_dir=data.get("user_data_dir"),
    )


def list_auth_profiles() -> List[Dict[str, Any]]:
    """List available auth profiles in the default profiles directory.

    Returns:
        List of dicts with 'name', 'path', and 'modified' keys.
    """
    profiles_dir = DEFAULT_PROFILES_DIR
    if not profiles_dir.is_dir():
        return []

    profiles = []
    for item in sorted(profiles_dir.iterdir()):
        if item.is_dir():
            profiles.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "modified": item.stat().st_mtime,
                }
            )
    return profiles
