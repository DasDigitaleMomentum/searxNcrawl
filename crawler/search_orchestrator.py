"""Fixed-provider search orchestrator for SearXNG and You.com.

Every configured provider is queried in parallel; results are merged with
conservative URL dedup and round-robin, multi-provider results first, each
attributed via ``providers``. A partial failure is tolerated; a total failure raises
``SearchProviderError`` with sanitized per-provider reasons.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Awaitable, Callable, Optional, Sequence
from urllib.parse import urlsplit, urlunsplit

import httpx

LOGGER = logging.getLogger(__name__)

SEARXNG = "searxng"
YOUCOM = "youcom"
PROVIDER_ORDER = (SEARXNG, YOUCOM)
_REQUEST_TIMEOUT_SECONDS = 30.0
_VALID_TIME_RANGES = {"day", "week", "month", "year"}
YOUCOM_URL = "https://ydc-index.io/v1/search"
YOUCOM_USER_AGENT = "youdotcom-integration/dasdigitalemomentum-searxncrawl"


class SearchProviderError(RuntimeError):
    """A sanitized provider configuration or execution failure."""


@dataclass
class SearchResult:
    title: str
    url: str
    content: str
    publishedDate: str = ""
    providers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    base_url: str
    api_key: str = ""
    username: str = ""
    password: str = ""


def _absolute_http_url(value: Optional[str]) -> Optional[str]:
    raw = value.strip() if isinstance(value, str) else ""
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        parsed.port
    except ValueError:
        return None
    return raw.rstrip("/")


def _resolve_provider_config() -> dict[str, ProviderConfig]:
    """Resolve valid operator configuration at search-call time."""
    configured: dict[str, ProviderConfig] = {}

    raw_url = os.getenv("SEARXNG_URL", "").strip()
    searxng_url = _absolute_http_url(raw_url)
    username = os.getenv("SEARXNG_USERNAME", "").strip()
    password = os.getenv("SEARXNG_PASSWORD", "").strip()
    credentials_valid = bool(username) == bool(password)
    # Name the variable and rule only; values may contain credentials.
    if raw_url and not searxng_url:
        LOGGER.warning(
            "SEARXNG_URL is set but invalid (must be an http(s) URL without "
            "embedded credentials); SearXNG is disabled"
        )
    if not credentials_valid:
        LOGGER.warning(
            "Only one of SEARXNG_USERNAME/SEARXNG_PASSWORD is set (set both or "
            "neither); SearXNG is disabled"
        )
    if searxng_url and credentials_valid:
        configured[SEARXNG] = ProviderConfig(
            provider=SEARXNG,
            base_url=searxng_url,
            username=username,
            password=password,
        )

    api_key = os.getenv("YDC_API_KEY", "").strip()
    if api_key:
        configured[YOUCOM] = ProviderConfig(
            provider=YOUCOM, base_url=YOUCOM_URL, api_key=api_key
        )

    return configured


def configured_providers() -> list[str]:
    configured = _resolve_provider_config()
    return [provider for provider in PROVIDER_ORDER if provider in configured]


def _normalize_provider_selection(
    providers: Optional[Sequence[str] | str],
) -> Optional[list[str]]:
    if providers is None:
        return None
    values = providers.split(",") if isinstance(providers, str) else providers
    normalized: list[str] = []
    for value in values:
        name = str(value).strip().lower()
        if name and name not in normalized:
            normalized.append(name)
    if not normalized:
        raise SearchProviderError("Provider selection must not be empty")
    unknown = [name for name in normalized if name not in PROVIDER_ORDER]
    if unknown:
        raise SearchProviderError(f"Unknown search provider: {unknown[0]}")
    return normalized


def _select_providers(
    configured: dict[str, ProviderConfig],
    providers: Optional[Sequence[str] | str] = None,
) -> list[str]:
    requested = _normalize_provider_selection(providers)
    if requested is None:
        selected = [name for name in PROVIDER_ORDER if name in configured]
    else:
        unavailable = [name for name in requested if name not in configured]
        if unavailable:
            raise SearchProviderError(
                f"Search provider is not configured: {unavailable[0]}"
            )
        requested_set = set(requested)
        selected = [name for name in PROVIDER_ORDER if name in requested_set]
    if not selected:
        raise SearchProviderError(
            "No valid search provider is configured; "
            "set a valid http(s) SEARXNG_URL and/or YDC_API_KEY"
        )
    return selected


async def _get_json(
    url: str,
    *,
    params: dict[str, Any],
    headers: dict[str, str],
    auth: Optional[httpx.Auth],
    max_retries: int,
    status_reason: Callable[[int], str],
) -> object:
    """GET JSON with per-attempt timeout; retry request errors, not status errors."""
    attempts = max(1, max_retries)
    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
        for attempt in range(attempts):
            try:
                response = await client.get(
                    url, params=params, headers=headers, auth=auth
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise SearchProviderError(
                    status_reason(exc.response.status_code)
                ) from None
            except httpx.RequestError:
                if attempt + 1 >= attempts:
                    raise SearchProviderError("request failed") from None
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            try:
                return response.json()
            except (ValueError, TypeError):
                raise SearchProviderError("invalid response") from None
    raise SearchProviderError("request failed")


def _map_searxng_results(payload: object) -> list[SearchResult]:
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise SearchProviderError("invalid response")
    results: list[SearchResult] = []
    for item in payload["results"]:
        if not isinstance(item, dict):
            continue
        published_date = item.get("publishedDate")
        results.append(
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                content=str(item.get("content", "")),
                publishedDate=(
                    str(published_date) if published_date is not None else ""
                ),
                providers=[SEARXNG],
            )
        )
    return results


def _searxng_status_reason(status: int) -> str:
    if status == 401:
        return "authentication failed, check SEARXNG_USERNAME/SEARXNG_PASSWORD"
    return "request failed"


async def _search_searxng(
    query: str,
    *,
    config: ProviderConfig,
    language: str,
    time_range: Optional[str],
    categories: Optional[list[str]],
    engines: Optional[list[str]],
    safesearch: int,
    pageno: int,
    max_retries: int,
) -> list[SearchResult]:
    params: dict[str, Any] = {
        "q": query,
        "format": "json",
        "language": language,
        "safesearch": safesearch,
        "pageno": max(1, pageno),
    }
    if time_range and time_range.lower() in _VALID_TIME_RANGES:
        params["time_range"] = time_range.lower()
    if categories:
        params["categories"] = ",".join(categories)
    if engines:
        params["engines"] = ",".join(engines)
    auth = (
        httpx.BasicAuth(config.username, config.password)
        if config.username and config.password
        else None
    )
    payload = await _get_json(
        f"{config.base_url}/search",
        params=params,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        auth=auth,
        max_retries=max_retries,
        status_reason=_searxng_status_reason,
    )
    return _map_searxng_results(payload)


def _youcom_status_reason(status: int) -> str:
    if status in (401, 403):
        return "API key rejected, check YDC_API_KEY"
    if status == 402:
        return "API credits exhausted"
    if status == 429:
        return "rate limit exceeded, try again later"
    return f"HTTP {status}"


async def _search_youcom(
    query: str,
    *,
    config: ProviderConfig,
    language: Optional[str],
    time_range: Optional[str],
    pageno: int,
    max_results: int,
    max_retries: int,
) -> list[SearchResult]:
    params: dict[str, Any] = {"query": query, "count": max_results}
    # SearXNG's "all"/"auto" mean no language filter; You.com applies language strictly.
    if language and language.lower() not in ("all", "auto"):
        params["language"] = language.upper()
    if time_range and time_range.lower() in _VALID_TIME_RANGES:
        params["freshness"] = time_range.lower()
    if pageno > 1:
        params["offset"] = pageno - 1
    payload = await _get_json(
        config.base_url,
        params=params,
        headers={
            "User-Agent": YOUCOM_USER_AGENT,
            "Accept": "application/json",
            "X-API-Key": config.api_key,
        },
        auth=None,
        max_retries=max_retries,
        status_reason=_youcom_status_reason,
    )
    if not isinstance(payload, dict):
        raise SearchProviderError("invalid response")
    # A query without hits returns "results": {}
    web = (payload.get("results") or {}).get("web") or []
    results: list[SearchResult] = []
    for item in web:
        if not isinstance(item, dict):
            continue
        page_age = item.get("page_age")
        results.append(
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                content=str(item.get("description", "")),
                publishedDate=str(page_age) if page_age is not None else "",
                providers=[YOUCOM],
            )
        )
    return results


def _url_dedup_key(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        port = parsed.port
    except ValueError:
        return None
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    default_port = 80 if scheme == "http" else 443
    netloc = host if port is None or port == default_port else f"{host}:{port}"
    return urlunsplit((scheme, netloc, parsed.path, parsed.query, ""))


def _merge_results(
    provider_results: Sequence[tuple[str, Sequence[SearchResult]]], max_results: int
) -> list[SearchResult]:
    limit = max(max_results, 0)
    merged: list[SearchResult] = []
    seen: dict[str, SearchResult] = {}
    ordered_results = [
        (provider, results)
        for ordered_provider in PROVIDER_ORDER
        for provider, results in provider_results
        if provider == ordered_provider
    ]
    index = 0
    while True:
        added_or_present = False
        for provider, results in ordered_results:
            if index >= len(results):
                continue
            added_or_present = True
            result = results[index]
            key = _url_dedup_key(result.url)
            if key is not None and key in seen:
                retained = seen[key]
                if provider not in retained.providers:
                    retained.providers.append(provider)
                    retained.providers.sort(key=PROVIDER_ORDER.index)
                continue
            result.providers = [provider]
            if key is not None:
                seen[key] = result
            merged.append(result)
        if not added_or_present:
            break
        index += 1
    consensus = [result for result in merged if len(result.providers) > 1]
    single_source = [result for result in merged if len(result.providers) == 1]
    return (consensus + single_source)[:limit]


async def search(
    query: str,
    *,
    language: str = "en",
    time_range: Optional[str] = None,
    categories: Optional[list[str]] = None,
    engines: Optional[list[str]] = None,
    safesearch: int = 1,
    pageno: int = 1,
    max_results: int = 10,
    max_retries: int = 3,
    providers: Optional[Sequence[str] | str] = None,
) -> list[SearchResult]:
    """Query the selected providers in parallel and return merged results."""
    configured = _resolve_provider_config()
    selected = _select_providers(configured, providers)
    max_results = min(max(1, max_results), 50)

    calls: list[Awaitable[list[SearchResult]]] = []
    for provider in selected:
        if provider == SEARXNG:
            calls.append(
                _search_searxng(
                    query,
                    config=configured[provider],
                    language=language,
                    time_range=time_range,
                    categories=categories,
                    engines=engines,
                    safesearch=safesearch,
                    pageno=pageno,
                    max_retries=max_retries,
                )
            )
        else:
            calls.append(
                _search_youcom(
                    query,
                    config=configured[provider],
                    language=language,
                    time_range=time_range,
                    pageno=pageno,
                    max_results=max_results,
                    max_retries=max_retries,
                )
            )

    # gather cancels the provider calls when this coroutine is cancelled.
    outcomes = await asyncio.gather(*calls, return_exceptions=True)

    successful: list[tuple[str, list[SearchResult]]] = []
    failures: list[str] = []
    for provider, outcome in zip(selected, outcomes):
        if isinstance(outcome, BaseException):
            if isinstance(outcome, SearchProviderError):
                reason = str(outcome)
                LOGGER.warning("Search provider %s failed: %s", provider, reason)
            else:
                reason = "unexpected error"
                # Class name only: exception messages (e.g. httpx) can echo header values.
                LOGGER.warning(
                    "Search provider %s failed: %s (%s)",
                    provider,
                    reason,
                    type(outcome).__name__,
                )
            failures.append(f"{provider}: {reason}")
            continue
        successful.append((provider, outcome))

    if not successful:
        raise SearchProviderError(
            "All selected search providers failed: " + "; ".join(failures)
        )

    return _merge_results(successful, max_results)


def _parse_search_result_fields() -> Optional[list[str]]:
    """Parse SEARCH_RESULT_FIELDS env var; empty/unset means all-fields mode."""
    raw_fields = os.getenv("SEARCH_RESULT_FIELDS")
    if raw_fields is None:
        return None

    fields = [name.strip() for name in raw_fields.split(",") if name.strip()]
    if not fields:
        return None

    return fields


def serialize_search_results(
    query: str, results: Sequence[SearchResult]
) -> dict[str, Any]:
    """Build the search envelope, applying SEARCH_RESULT_FIELDS to each result."""
    fields = _parse_search_result_fields()
    items = [asdict(result) for result in results]
    if fields is not None:
        field_set = set(fields)
        items = [{k: v for k, v in item.items() if k in field_set} for item in items]
    return {"query": query, "number_of_results": len(items), "results": items}
