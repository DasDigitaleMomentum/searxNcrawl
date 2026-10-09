from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from crawl4ai import CrawlerRunConfig

import crawler
from crawler import page_hooks
from crawler.config import (
    RunConfigOverrides,
    build_markdown_run_config,
    wants_page_reload,
)


class FakePage:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self.error = error

    async def reload(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error


class RecordingStrategy:
    def __init__(self) -> None:
        self.hooks: dict = {}

    def set_hook(self, name, hook) -> None:
        self.hooks[name] = hook


# --- config ---------------------------------------------------------------


def test_default_config_no_longer_reloads_via_js_code() -> None:
    config = build_markdown_run_config()

    assert "reload" not in str(config.js_code)
    assert config.flatten_shadow_dom is True


def test_default_config_wants_reload() -> None:
    assert wants_page_reload(build_markdown_run_config()) is True
    assert wants_page_reload(build_markdown_run_config(RunConfigOverrides())) is True


def test_custom_js_code_override_disables_reload() -> None:
    """Matches the old behaviour: a js_code override replaced the reload."""
    config = build_markdown_run_config(RunConfigOverrides(js_code="console.log(1)"))

    assert wants_page_reload(config) is False


def test_foreign_config_does_not_reload() -> None:
    assert wants_page_reload(CrawlerRunConfig()) is False


# --- hook -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_reload_waits_for_load_with_page_timeout() -> None:
    page = FakePage()

    result = await page_hooks.reload_after_goto(
        page, url="https://example.com", config=SimpleNamespace(page_timeout=1234)
    )

    assert result is page
    assert page.calls == [{"wait_until": "load", "timeout": 1234}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url", [None, "", "raw:<html></html>", "file:///tmp/a.html", "about:blank"]
)
async def test_non_http_urls_are_not_reloaded(url) -> None:
    page = FakePage()

    assert await page_hooks.reload_after_goto(page, url=url) is page
    assert page.calls == []


@pytest.mark.asyncio
async def test_failed_reload_keeps_first_load(caplog: pytest.LogCaptureFixture) -> None:
    page = FakePage(error=TimeoutError("reload timed out"))

    result = await page_hooks.reload_after_goto(page, url="https://example.com")

    assert result is page
    assert "Reload of https://example.com failed" in caplog.text


def test_install_reload_hook_registers_after_goto() -> None:
    strategy = RecordingStrategy()

    page_hooks.install_reload_hook(SimpleNamespace(crawler_strategy=strategy))

    assert strategy.hooks == {"after_goto": page_hooks.reload_after_goto}


def test_install_reload_hook_ignores_crawlers_without_strategy() -> None:
    page_hooks.install_reload_hook(SimpleNamespace())  # must not raise


# --- integration with crawl_page_async ------------------------------------


def _dummy_crawler_class(strategies: list):
    class DummyCrawler:
        def __init__(self, *args, **kwargs) -> None:
            self.crawler_strategy = RecordingStrategy()
            strategies.append(self.crawler_strategy)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def arun(self, url, config):
            return [SimpleNamespace(url=url)]

    return DummyCrawler


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("config", "expect_hook"),
    [(None, True), (CrawlerRunConfig(), False)],
    ids=["default-config", "custom-config"],
)
async def test_crawl_page_async_installs_hook_only_for_default_config(
    monkeypatch: pytest.MonkeyPatch, config, expect_hook: bool
) -> None:
    strategies: list = []
    monkeypatch.setattr(crawler, "AsyncWebCrawler", _dummy_crawler_class(strategies))
    monkeypatch.setattr(
        crawler,
        "build_document_from_result",
        lambda result, *, dedup_mode="exact": SimpleNamespace(
            status="success", request_url=result.url
        ),
    )

    await crawler.crawl_page_async("https://example.com", config=config)

    assert ("after_goto" in strategies[0].hooks) is expect_hook


# --- real browser ---------------------------------------------------------


@pytest.mark.asyncio
async def test_reload_hook_reloads_once_in_chromium() -> None:
    """Serve a fake http page via request routing (no network)."""
    playwright_api = pytest.importorskip("playwright.async_api")
    requests: list[str] = []

    async def handle(route) -> None:
        requests.append(route.request.url)
        await route.fulfill(
            content_type="text/html",
            body=f"<html><body><main>load {len(requests)}</main></body></html>",
        )

    async with playwright_api.async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch()
        except Exception as exc:  # pragma: no cover - depends on local setup
            if os.getenv("SEARXNCRAWL_REQUIRE_BROWSER_TESTS"):
                raise
            pytest.skip(f"Chromium not available: {exc}")
        try:
            page = await browser.new_page()
            await page.route("http://searxncrawl.test/**", handle)
            url = "http://searxncrawl.test/page"
            await page.goto(url)

            await page_hooks.reload_after_goto(page, url=url)

            assert requests == [url, url]
            assert await page.inner_text("main") == "load 2"
        finally:
            await browser.close()
