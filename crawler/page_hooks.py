"""Playwright page hooks for the default crawl configuration.

The default single-page and site crawls load every page twice: the second
load carries cookies and storage set by the first, which gets past simple
bot challenges and lazy-loading placeholders.

The reload used to run as ``window.location.reload()`` inside ``js_code``.
Crawl4AI executes ``js_code`` after ``wait_for`` and does not wait for a
navigation it triggers, so the HTML was sometimes captured while the reloaded
document was still loading (e.g. only ``<head>`` on docs.python.org, reported
as "Blocked by anti-bot protection: no <body> tag"). Running the reload as an
``after_goto`` hook with ``page.reload()`` waits for the new document, and
``wait_for`` then checks the reloaded page.
"""

from __future__ import annotations

import logging
from typing import Any

LOGGER = logging.getLogger(__name__)

RELOADABLE_SCHEMES = ("http://", "https://")


async def reload_after_goto(
    page: Any,
    context: Any = None,
    url: str | None = None,
    response: Any = None,
    config: Any = None,
    **kwargs: Any,
) -> Any:
    """Reload an http(s) page once and wait for the reloaded document.

    A failed reload is logged and the crawl continues with the first load.
    """
    if not url or not url.startswith(RELOADABLE_SCHEMES):
        return page
    timeout = getattr(config, "page_timeout", None) or 30000
    try:
        # "load" (not the goto default "domcontentloaded"): scripts and
        # subresources of the reloaded document have run, so client-side
        # rendered parts such as code examples are present before capture.
        await page.reload(wait_until="load", timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - keep the first load on any reload error
        LOGGER.warning("Reload of %s failed, using the first load: %s", url, exc)
    return page


def install_reload_hook(crawler: Any) -> None:
    """Register :func:`reload_after_goto` on a Crawl4AI crawler, if supported."""
    strategy = getattr(crawler, "crawler_strategy", None)
    set_hook = getattr(strategy, "set_hook", None)
    if set_hook is not None:
        set_hook("after_goto", reload_after_goto)
