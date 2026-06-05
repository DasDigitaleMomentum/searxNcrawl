"""Internal auth-core helpers for crawl runtime wiring."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, TypeAlias, Union

LOGGER = logging.getLogger(__name__)


class AuthConfigError(ValueError):
    """Raised when auth input cannot be resolved safely."""


@dataclass(frozen=True)
class AuthConfig:
    """User auth input model (MVP supports storage_state only)."""

    storage_state: Optional[str] = None


@dataclass(frozen=True)
class ResolvedAuth:
    """Validated auth values ready for runtime usage."""

    storage_state: Optional[str] = None


AuthInput: TypeAlias = Union[AuthConfig, ResolvedAuth, Mapping[str, Any]]


def resolve_auth(
    auth: Optional[AuthInput],
    *,
    restrict_paths: bool = False,
    storage_state_dir: Optional[str] = None,
) -> Optional[ResolvedAuth]:
    """Resolve and validate auth input into a deterministic runtime contract.

    Args:
        auth: Raw auth input (dict, AuthConfig, or ResolvedAuth).
        restrict_paths: When True, confine ``storage_state`` to
            *storage_state_dir*.  Should be enabled for untrusted callers
            (MCP tools) and left False for the trusted CLI.
        storage_state_dir: Directory that ``storage_state`` paths must
            reside in when *restrict_paths* is True.  Ignored when
            *restrict_paths* is False.
    """
    if auth is None:
        return None

    if isinstance(auth, ResolvedAuth):
        return auth

    config = _coerce_auth_config(auth)
    if config.storage_state is None:
        return None

    raw_storage_state = str(config.storage_state).strip()
    if not raw_storage_state:
        raise AuthConfigError("Auth storage_state must be a non-empty path")

    storage_state_path = _canonicalize_path(raw_storage_state)

    # ── Path confinement (CWE-22 mitigation) ────────────────────────
    if restrict_paths:
        _enforce_path_confinement(storage_state_path, storage_state_dir)

    if not storage_state_path.exists():
        raise AuthConfigError(
            f"Auth storage_state file not found: {storage_state_path}"
        )

    if not storage_state_path.is_file():
        raise AuthConfigError(
            f"Auth storage_state path is not a file: {storage_state_path}"
        )

    try:
        with storage_state_path.open("r", encoding="utf-8") as state_file:
            parsed = json.load(state_file)
    except PermissionError as exc:
        raise AuthConfigError(
            f"Auth storage_state file is not readable: {storage_state_path}"
        ) from exc
    except OSError as exc:
        raise AuthConfigError(
            f"Auth storage_state file is not readable: {storage_state_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise AuthConfigError(
            f"Auth storage_state is invalid JSON: {storage_state_path}"
        ) from exc

    if not isinstance(parsed, dict):
        raise AuthConfigError(
            f"Auth storage_state must contain a JSON object: {storage_state_path}"
        )

    return ResolvedAuth(storage_state=str(storage_state_path))


def _enforce_path_confinement(
    resolved_path: Path,
    allowed_dir: Optional[str],
) -> None:
    """Raise :class:`AuthConfigError` if *resolved_path* is outside *allowed_dir*.

    This blocks path-traversal attacks (``..``, symlink escapes, absolute
    paths pointing elsewhere) when the caller is untrusted (e.g. MCP
    tool invocations).
    """
    if allowed_dir is None:
        raise AuthConfigError(
            "storage_state is not allowed: no storage-state directory configured "
            "(set STORAGE_STATE_DIR or place files in ~/.config/searxncrawl/states/)"
        )

    allowed = Path(allowed_dir).resolve(strict=False)

    # Use resolve() on the candidate so symlinks are followed before the
    # prefix check — prevents symlink-based escapes.
    try:
        canonical = resolved_path.resolve(strict=False)
    except (OSError, ValueError) as exc:
        raise AuthConfigError(
            f"Auth storage_state path cannot be resolved: {resolved_path}"
        ) from exc

    # Path.is_relative_to was added in Python 3.9
    try:
        if not canonical.is_relative_to(allowed):
            raise AuthConfigError(
                f"Auth storage_state path is outside the allowed directory: "
                f"{canonical} is not inside {allowed}"
            )
    except AttributeError:
        # Fallback for older Python (< 3.9)
        if not str(canonical).startswith(str(allowed) + "/") and canonical != allowed:
            raise AuthConfigError(
                f"Auth storage_state path is outside the allowed directory: "
                f"{canonical} is not inside {allowed}"
            )


def _coerce_auth_config(auth: AuthInput) -> AuthConfig:
    if isinstance(auth, AuthConfig):
        return auth

    if isinstance(auth, Mapping):
        unsupported_keys = sorted(set(auth.keys()) - {"storage_state"})
        if unsupported_keys:
            keys = ", ".join(unsupported_keys)
            raise AuthConfigError(
                f"Unsupported auth fields: {keys} (only storage_state is supported)"
            )

        return AuthConfig(storage_state=auth.get("storage_state"))

    raise AuthConfigError(
        "Invalid auth input type; expected AuthConfig or mapping with storage_state"
    )


def _canonicalize_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve(strict=False)
