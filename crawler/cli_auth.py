"""Authentication-related CLI argument helpers."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Callable, Optional

from .auth import AuthConfig, load_auth_from_env


def build_cli_auth(
    args: argparse.Namespace,
    auth_loader: Callable[[], Optional[AuthConfig]] = load_auth_from_env,
) -> Optional[AuthConfig]:
    """Build AuthConfig from CLI arguments, falling back to env vars."""
    cookies = None
    headers_dict = None

    if hasattr(args, "cookies") and args.cookies:
        cookies_val = args.cookies
        if cookies_val.startswith("[") or cookies_val.startswith("{"):
            parsed = json.loads(cookies_val)
            cookies = parsed if isinstance(parsed, list) else [parsed]
        elif Path(cookies_val).is_file():
            with open(cookies_val, "r") as fh:
                cookies = json.load(fh)
        else:
            logging.error("Invalid --cookies value: %s", cookies_val)

    if hasattr(args, "header") and args.header:
        headers_dict = {}
        for h in args.header:
            if ":" in h:
                key, value = h.split(":", 1)
                headers_dict[key.strip()] = value.strip()
            else:
                logging.warning("Invalid header format (expected 'Key: Value'): %s", h)

    storage_state = getattr(args, "storage_state", None)
    auth_profile = getattr(args, "auth_profile", None)

    if any([cookies, headers_dict, storage_state, auth_profile]):
        resolved_storage = storage_state
        if auth_profile and not storage_state:
            profile_ss = Path(auth_profile) / "storage_state.json"
            if profile_ss.is_file():
                resolved_storage = str(profile_ss)
                logging.info("Resolved storage state from profile: %s", resolved_storage)
        return AuthConfig(
            cookies=cookies,
            headers=headers_dict,
            storage_state=resolved_storage,
            user_data_dir=auth_profile,
        )

    return auth_loader()


def add_auth_args(parser: argparse.ArgumentParser) -> None:
    """Add authentication arguments to an argparse parser."""
    auth_group = parser.add_argument_group("authentication")
    auth_group.add_argument(
        "--cookies",
        type=str,
        default=None,
        help='Cookies as JSON string or path to cookies JSON file. '
             'Example: \'[{"name":"sid","value":"abc","domain":".example.com"}]\'',
    )
    auth_group.add_argument(
        "--header",
        action="append",
        default=None,
        help='Custom HTTP header (can be repeated). '
             'Example: --header "Authorization: Bearer xyz"',
    )
    auth_group.add_argument(
        "--storage-state",
        type=str,
        default=None,
        help="Path to Playwright storage state JSON file (from capture-auth)",
    )
    auth_group.add_argument(
        "--auth-profile",
        type=str,
        default=None,
        help="Path to persistent browser profile directory",
    )
