"""Make sure Playwright's Chromium is available before a browser is launched.

``pip install`` / ``uvx`` only install the Playwright Python package, not the
browser binaries. Without them every crawl fails with Playwright's
"please run playwright install" message. To make zero-setup runs such as
``uvx --from searxncrawl crawl-mcp`` work, :func:`ensure_chromium` runs
``python -m playwright install chromium`` once per process before the first
browser launch. The command is idempotent: if the matching Chromium build is
already present (Docker image, earlier run) it returns in about a second.

Set ``PLAYWRIGHT_AUTO_INSTALL=false`` to disable the automatic download, e.g.
on machines without internet access where browsers are provisioned separately.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

LOGGER = logging.getLogger(__name__)

AUTO_INSTALL_ENV = "PLAYWRIGHT_AUTO_INSTALL"
_FALSY = {"0", "false", "no", "off"}

MANUAL_INSTALL_HINT = (
    "Install it manually with 'python -m playwright install chromium' in the "
    "environment that runs searxNcrawl (with uvx: "
    "'uvx --from searxncrawl playwright install chromium'). "
    "On Linux, add '--with-deps' to also install the required system libraries."
)

_lock: asyncio.Lock | None = None
_lock_loop: asyncio.AbstractEventLoop | None = None
_ensured = False


class BrowserSetupError(RuntimeError):
    """Raised when Chromium cannot be installed automatically."""


def auto_install_enabled() -> bool:
    """Return whether the automatic Chromium install is enabled."""
    return os.getenv(AUTO_INSTALL_ENV, "true").strip().lower() not in _FALSY


async def _run_install() -> None:
    # stdout is redirected to stderr: in MCP stdio mode, stdout carries the
    # JSON-RPC stream and must not receive download progress output.
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "playwright",
        "install",
        "chromium",
        stdout=sys.stderr,
        stderr=sys.stderr,
    )
    returncode = await process.wait()
    if returncode != 0:
        raise BrowserSetupError(
            f"Automatic Chromium install failed (exit code {returncode}). "
            + MANUAL_INSTALL_HINT
        )


async def ensure_chromium() -> None:
    """Install Playwright's Chromium once per process if it is missing.

    Concurrent callers share one install run. Does nothing when disabled via
    ``PLAYWRIGHT_AUTO_INSTALL``.

    Raises:
        BrowserSetupError: If the install command fails or cannot be started.
    """
    global _ensured, _lock, _lock_loop
    if _ensured or not auto_install_enabled():
        return
    # Sync wrappers call asyncio.run() repeatedly; a lock is bound to the loop
    # it was first used in, so create one per running loop.
    loop = asyncio.get_running_loop()
    if _lock is None or _lock_loop is not loop:
        _lock = asyncio.Lock()
        _lock_loop = loop
    async with _lock:
        if _ensured:
            return
        LOGGER.info("Checking Playwright Chromium (downloads once if missing)")
        try:
            await _run_install()
        except OSError as exc:
            raise BrowserSetupError(
                f"Could not start the Chromium install: {exc}. " + MANUAL_INSTALL_HINT
            ) from exc
        _ensured = True
