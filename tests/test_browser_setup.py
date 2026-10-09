from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

import pytest

import crawler
from crawler import browser_setup


class FakeProcess:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode

    async def wait(self) -> int:
        await asyncio.sleep(0)
        return self.returncode


@pytest.fixture
def fake_exec(monkeypatch: pytest.MonkeyPatch):
    """Enable auto-install, reset module state and record subprocess calls."""
    monkeypatch.setenv("PLAYWRIGHT_AUTO_INSTALL", "true")
    monkeypatch.setattr(browser_setup, "_ensured", False)
    monkeypatch.setattr(browser_setup, "_lock", None)
    monkeypatch.setattr(browser_setup, "_lock_loop", None)
    calls: list[dict] = []
    state = {"returncode": 0, "error": None}

    async def create_subprocess_exec(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        if state["error"] is not None:
            raise state["error"]
        return FakeProcess(state["returncode"])

    monkeypatch.setattr(
        browser_setup.asyncio, "create_subprocess_exec", create_subprocess_exec
    )
    return SimpleNamespace(calls=calls, state=state)


@pytest.mark.parametrize("value", ["false", "0", "no", "off", " FALSE "])
def test_auto_install_disabled_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("PLAYWRIGHT_AUTO_INSTALL", value)
    assert browser_setup.auto_install_enabled() is False


@pytest.mark.parametrize("value", [None, "true", "1", "yes", ""])
def test_auto_install_enabled_by_default(
    monkeypatch: pytest.MonkeyPatch, value
) -> None:
    if value is None:
        monkeypatch.delenv("PLAYWRIGHT_AUTO_INSTALL", raising=False)
    else:
        monkeypatch.setenv("PLAYWRIGHT_AUTO_INSTALL", value)
    assert browser_setup.auto_install_enabled() is True


@pytest.mark.asyncio
async def test_runs_playwright_install_with_current_interpreter(fake_exec) -> None:
    await browser_setup.ensure_chromium()

    assert len(fake_exec.calls) == 1
    call = fake_exec.calls[0]
    assert call["args"] == (sys.executable, "-m", "playwright", "install", "chromium")
    # stdout must never be used: it carries the MCP stdio protocol.
    assert call["kwargs"]["stdout"] is sys.stderr
    assert call["kwargs"]["stderr"] is sys.stderr


@pytest.mark.asyncio
async def test_installs_only_once_per_process(fake_exec) -> None:
    await browser_setup.ensure_chromium()
    await browser_setup.ensure_chromium()

    assert len(fake_exec.calls) == 1


@pytest.mark.asyncio
async def test_concurrent_callers_share_one_install(fake_exec) -> None:
    await asyncio.gather(*(browser_setup.ensure_chromium() for _ in range(5)))

    assert len(fake_exec.calls) == 1


@pytest.mark.asyncio
async def test_disabled_does_not_start_subprocess(fake_exec, monkeypatch) -> None:
    monkeypatch.setenv("PLAYWRIGHT_AUTO_INSTALL", "false")

    await browser_setup.ensure_chromium()

    assert fake_exec.calls == []


@pytest.mark.asyncio
async def test_failed_install_raises_with_manual_hint_and_retries(fake_exec) -> None:
    fake_exec.state["returncode"] = 1

    with pytest.raises(browser_setup.BrowserSetupError) as excinfo:
        await browser_setup.ensure_chromium()
    assert "exit code 1" in str(excinfo.value)
    assert "playwright install chromium" in str(excinfo.value)

    # A failed attempt is not cached: the next call tries again.
    fake_exec.state["returncode"] = 0
    await browser_setup.ensure_chromium()
    assert len(fake_exec.calls) == 2


@pytest.mark.asyncio
async def test_missing_interpreter_raises_browser_setup_error(fake_exec) -> None:
    fake_exec.state["error"] = FileNotFoundError("python not found")

    with pytest.raises(browser_setup.BrowserSetupError, match="Could not start"):
        await browser_setup.ensure_chromium()


def test_retry_works_in_a_new_event_loop(fake_exec) -> None:
    """Sync wrappers use asyncio.run() per call; the lock must not leak loops."""
    fake_exec.state["returncode"] = 1
    with pytest.raises(browser_setup.BrowserSetupError):
        asyncio.run(browser_setup.ensure_chromium())

    fake_exec.state["returncode"] = 0
    asyncio.run(browser_setup.ensure_chromium())
    assert len(fake_exec.calls) == 2


@pytest.mark.asyncio
async def test_crawl_page_async_ensures_chromium_before_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []

    async def fake_ensure() -> None:
        order.append("ensure")

    class DummyCrawler:
        async def __aenter__(self):
            order.append("launch")
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def arun(self, url, config):
            return [SimpleNamespace(url=url)]

    monkeypatch.setattr(crawler, "ensure_chromium", fake_ensure)
    monkeypatch.setattr(crawler, "AsyncWebCrawler", DummyCrawler)
    monkeypatch.setattr(
        crawler,
        "build_document_from_result",
        lambda result, *, dedup_mode="exact": SimpleNamespace(
            status="success", request_url=result.url
        ),
    )

    await crawler.crawl_page_async("https://example.com")

    assert order == ["ensure", "launch"]
