"""Isolated session-capture runtime for authenticated crawling setup."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any, Awaitable, Callable, Literal, Optional

CaptureStatus = Literal["success", "timeout", "abort"]


class SessionCaptureError(ValueError):
    """Raised when capture execution fails due to invalid usage/runtime."""


class SessionCaptureConfigError(SessionCaptureError):
    """Raised when capture configuration is invalid."""


@dataclass(frozen=True)
class CaptureResult:
    """Result contract for isolated session capture."""

    status: CaptureStatus
    message: str
    storage_state_path: Optional[str] = None
    final_url: Optional[str] = None


@dataclass(frozen=True)
class CdpSessionEntry:
    """A selectable CDP session candidate discovered in a running browser."""

    context_index: int
    page_index: Optional[int]
    url: str
    title: Optional[str] = None


ConfirmCallback = Callable[[str], bool | Awaitable[bool]]


def _canonicalize_output_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve(strict=False)


def _validate_output_target(path: Path, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise SessionCaptureConfigError(
            f"storage_state output already exists: {path} (use overwrite=True to replace)"
        )

    if path.exists() and path.is_dir():
        raise SessionCaptureConfigError(
            f"storage_state output path is a directory: {path}"
        )


def _write_storage_state(path: Path, payload: Any) -> None:
    if not isinstance(payload, dict):
        raise SessionCaptureError("Captured storage_state must be a JSON object")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Deterministic post-write validation
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise SessionCaptureError("Written storage_state is not a JSON object")


def _normalize_cdp_url(cdp_url: str) -> str:
    if not cdp_url or not cdp_url.strip():
        raise SessionCaptureConfigError("cdp_url must be a non-empty URL")
    return cdp_url.strip()


async def list_cdp_sessions_async(cdp_url: str) -> list[CdpSessionEntry]:
    """List selectable sessions from a running browser via CDP."""
    target_url = _normalize_cdp_url(cdp_url)

    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        raise SessionCaptureError(
            "Playwright is required for CDP session listing. Install browsers with 'playwright install chromium'."
        ) from exc

    sessions: list[CdpSessionEntry] = []

    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.connect_over_cdp(target_url)
        except Exception as exc:  # pragma: no cover - runtime/network dependent
            raise SessionCaptureError(
                f"Failed to connect to CDP endpoint: {target_url}"
            ) from exc

        try:
            for context_index, context in enumerate(browser.contexts):
                pages = list(context.pages)
                if not pages:
                    sessions.append(
                        CdpSessionEntry(
                            context_index=context_index,
                            page_index=None,
                            url="",
                            title=None,
                        )
                    )
                    continue

                for page_index, page in enumerate(pages):
                    title: Optional[str] = None
                    try:
                        title = await page.title()
                    except Exception:
                        title = None

                    sessions.append(
                        CdpSessionEntry(
                            context_index=context_index,
                            page_index=page_index,
                            url=page.url or "",
                            title=title,
                        )
                    )
        finally:
            await browser.close()

    return sessions


async def export_cdp_storage_state_async(
    output_path: str,
    *,
    cdp_url: str,
    context_index: int,
    overwrite: bool = False,
) -> CaptureResult:
    """Export storage_state from an existing CDP browser context."""
    if not output_path or not str(output_path).strip():
        raise SessionCaptureConfigError("output_path must be a non-empty path")

    if context_index < 0:
        raise SessionCaptureConfigError(
            "context_index must be greater than or equal to 0"
        )

    target_url = _normalize_cdp_url(cdp_url)
    output = _canonicalize_output_path(output_path)
    _validate_output_target(output, overwrite=overwrite)

    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        raise SessionCaptureError(
            "Playwright is required for CDP export. Install browsers with 'playwright install chromium'."
        ) from exc

    final_url: Optional[str] = None

    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.connect_over_cdp(target_url)
        except Exception as exc:  # pragma: no cover - runtime/network dependent
            raise SessionCaptureError(
                f"Failed to connect to CDP endpoint: {target_url}"
            ) from exc

        try:
            contexts = list(browser.contexts)
            if not contexts:
                raise SessionCaptureError(
                    f"No browser contexts available at CDP endpoint: {target_url}"
                )

            if context_index >= len(contexts):
                raise SessionCaptureConfigError(
                    "context_index out of range: "
                    f"{context_index} (available: 0..{len(contexts) - 1})"
                )

            context = contexts[context_index]
            if context.pages:
                final_url = context.pages[0].url or None

            _write_storage_state(output, await context.storage_state())
        finally:
            await browser.close()

    return CaptureResult(
        status="success",
        message=(
            "Exported storage_state from running CDP browser "
            f"(context={context_index})."
        ),
        storage_state_path=str(output),
        final_url=final_url,
    )


async def _execute_capture_flow(
    *,
    start_url: Optional[str],
    completion_url_pattern: str,
    timeout_seconds: float,
    poll_interval: float,
    headless: bool,
    confirm_callback: Optional[ConfirmCallback],
) -> dict[str, Any]:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        raise SessionCaptureError(
            "Playwright is required for session capture. Install browsers with 'playwright install chromium'."
        ) from exc

    pattern = re.compile(completion_url_pattern)
    started = monotonic()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            if start_url:
                await page.goto(start_url)

            while True:
                if page.is_closed():
                    return {
                        "status": "abort",
                        "message": "Capture aborted: browser page was closed before completion.",
                        "final_url": None,
                    }

                current_url = page.url or ""
                if pattern.search(current_url):
                    confirmed = True
                    if confirm_callback is not None:
                        decision = confirm_callback(current_url)
                        confirmed = (
                            await decision
                            if asyncio.iscoroutine(decision)
                            else bool(decision)
                        )

                    if confirmed:
                        storage_state = await context.storage_state()
                        return {
                            "status": "success",
                            "message": "Capture completed and storage_state collected.",
                            "final_url": current_url,
                            "storage_state": storage_state,
                        }

                if (monotonic() - started) >= timeout_seconds:
                    return {
                        "status": "timeout",
                        "message": (
                            "Capture timed out before completion URL was observed "
                            f"(timeout={timeout_seconds}s)."
                        ),
                        "final_url": current_url,
                    }

                await asyncio.sleep(poll_interval)
        finally:
            await browser.close()


async def capture_session_async(
    output_path: str,
    *,
    completion_url_pattern: str,
    start_url: Optional[str] = None,
    timeout_seconds: float = 300.0,
    poll_interval: float = 0.25,
    overwrite: bool = False,
    headless: bool = False,
    confirm_callback: Optional[ConfirmCallback] = None,
) -> CaptureResult:
    """Capture authenticated browser storage_state in an isolated flow."""
    if not output_path or not str(output_path).strip():
        raise SessionCaptureConfigError("output_path must be a non-empty path")

    if not completion_url_pattern or not completion_url_pattern.strip():
        raise SessionCaptureConfigError("completion_url_pattern must be provided")

    if timeout_seconds <= 0:
        raise SessionCaptureConfigError("timeout_seconds must be greater than 0")

    if poll_interval <= 0:
        raise SessionCaptureConfigError("poll_interval must be greater than 0")

    output = _canonicalize_output_path(output_path)
    _validate_output_target(output, overwrite=overwrite)

    flow = await _execute_capture_flow(
        start_url=start_url,
        completion_url_pattern=completion_url_pattern,
        timeout_seconds=timeout_seconds,
        poll_interval=poll_interval,
        headless=headless,
        confirm_callback=confirm_callback,
    )

    status = flow.get("status")
    message = str(flow.get("message", ""))
    final_url = flow.get("final_url")

    if status == "success":
        _write_storage_state(output, flow.get("storage_state"))
        return CaptureResult(
            status="success",
            message=message,
            storage_state_path=str(output),
            final_url=final_url,
        )

    if status == "timeout":
        return CaptureResult(status="timeout", message=message, final_url=final_url)

    if status == "abort":
        return CaptureResult(status="abort", message=message, final_url=final_url)

    raise SessionCaptureError(f"Unknown capture status: {status}")


def capture_session(
    output_path: str,
    *,
    completion_url_pattern: str,
    start_url: Optional[str] = None,
    timeout_seconds: float = 300.0,
    poll_interval: float = 0.25,
    overwrite: bool = False,
    headless: bool = False,
) -> CaptureResult:
    """Synchronous wrapper for capture_session_async."""
    return asyncio.run(
        capture_session_async(
            output_path,
            completion_url_pattern=completion_url_pattern,
            start_url=start_url,
            timeout_seconds=timeout_seconds,
            poll_interval=poll_interval,
            overwrite=overwrite,
            headless=headless,
        )
    )
