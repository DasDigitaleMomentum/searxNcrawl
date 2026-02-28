"""Internal auth-core helpers for crawl runtime wiring."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, TypeAlias, Union


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


def resolve_auth(auth: Optional[AuthInput]) -> Optional[ResolvedAuth]:
    """Resolve and validate auth input into a deterministic runtime contract."""
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
