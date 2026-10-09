"""Tests for the single-page ``wait_for`` condition.

The browser tests run the generated JavaScript in headless Chromium against
local HTML (no network). They are skipped when Chromium is not installed,
unless SEARXNCRAWL_REQUIRE_BROWSER_TESTS is set (as in CI).
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest

from crawler.config import (
    CONTENT_WAIT_GRACE_MS,
    MAIN_SELECTORS,
    MIN_CONTENT_CHARS,
    build_content_wait_condition,
    build_markdown_run_config,
)

LONG_TEXT = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 3


def test_condition_is_js_and_covers_all_main_selectors() -> None:
    condition = build_content_wait_condition()

    assert condition.startswith("js:")
    for selector in MAIN_SELECTORS:
        assert selector in condition
    assert str(MIN_CONTENT_CHARS) in condition
    assert str(CONTENT_WAIT_GRACE_MS) in condition


def test_markdown_run_config_uses_content_wait_condition() -> None:
    assert build_markdown_run_config().wait_for == build_content_wait_condition()


def test_condition_no_longer_requires_a_main_element() -> None:
    condition = build_content_wait_condition()

    assert "document.querySelector('main')" not in condition
    assert "document.body.innerText" in condition


async def _time_until_ready(html: str, timeout_s: float) -> float | None:
    """Poll the condition like Crawl4AI does; return seconds until true."""
    playwright_api = pytest.importorskip("playwright.async_api")
    function = build_content_wait_condition()[len("js:") :]
    async with playwright_api.async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch()
        except Exception as exc:  # pragma: no cover - depends on local setup
            if os.getenv("SEARXNCRAWL_REQUIRE_BROWSER_TESTS"):
                raise
            pytest.skip(f"Chromium not available: {exc}")
        try:
            page = await browser.new_page()
            await page.set_content(html)
            start = time.monotonic()
            while time.monotonic() - start < timeout_s:
                if await page.evaluate(f"({function})()"):
                    return time.monotonic() - start
                await asyncio.sleep(0.1)
            return None
        finally:
            await browser.close()


GRACE_S = CONTENT_WAIT_GRACE_MS / 1000


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "html",
    [
        f"<html><body><main>{LONG_TEXT}</main></body></html>",
        f"<html><body><article>{LONG_TEXT}</article></body></html>",
        f"<html><body><div role='main'>{LONG_TEXT}</div></body></html>",
        f"<html><body><div class='markdown-body'>{LONG_TEXT}</div></body></html>",
    ],
    ids=["main", "article", "role-main", "markdown-body"],
)
async def test_ready_immediately_when_a_content_area_has_text(html: str) -> None:
    elapsed = await _time_until_ready(html, timeout_s=GRACE_S + 2)

    assert elapsed is not None
    assert elapsed < 1.0


@pytest.mark.asyncio
async def test_falls_back_to_body_after_grace_period() -> None:
    """example.com-style page: no content area, only body text."""
    html = (
        "<html><body><div><h1>Example Domain</h1><p>Short page.</p></div></body></html>"
    )

    elapsed = await _time_until_ready(html, timeout_s=GRACE_S + 3)

    assert elapsed is not None
    assert GRACE_S - 0.2 <= elapsed < GRACE_S + 2


@pytest.mark.asyncio
async def test_short_main_falls_back_to_body_instead_of_timing_out() -> None:
    html = "<html><body><main>Hi</main><p>Some more body text.</p></body></html>"

    elapsed = await _time_until_ready(html, timeout_s=GRACE_S + 3)

    assert elapsed is not None


@pytest.mark.asyncio
async def test_empty_page_never_becomes_ready() -> None:
    elapsed = await _time_until_ready(
        "<html><body></body></html>", timeout_s=GRACE_S + 1.5
    )

    assert elapsed is None
