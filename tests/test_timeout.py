from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

import crawler
import crawler.site as site_module
from crawler import mcp_server


def _doc(url: str, status: str = "success", error_message: str | None = None):
    return SimpleNamespace(
        request_url=url,
        final_url=url,
        status=status,
        markdown="# ok" if status == "success" else "",
        error_message=error_message,
        metadata={},
        references=[],
    )


async def _hanging_arun(*args, **kwargs):
    await asyncio.sleep(999)


@pytest.mark.asyncio
async def test_crawl_page_async_hanging_arun_raises_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyCrawler:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def arun(self, url, config):
            await _hanging_arun(url, config)

    monkeypatch.setattr(crawler, "AsyncWebCrawler", DummyCrawler)

    with pytest.raises(TimeoutError):
        await crawler.crawl_page_async("https://example.com", timeout=0.01)


@pytest.mark.asyncio
async def test_crawl_pages_async_per_url_timeout_returns_failed_doc_and_batch_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_crawl_page_async(
        url,
        *,
        config=None,
        dedup_mode="exact",
        auth=None,
        timeout=None,
    ):
        if url == "https://timeout.example.com":
            raise TimeoutError("simulated timeout")
        return _doc(url)

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)

    docs = await crawler.crawl_pages_async(
        [
            "https://ok-1.example.com",
            "https://timeout.example.com",
            "https://ok-2.example.com",
        ],
        timeout=0.1,
    )

    assert len(docs) == 3
    assert docs[0].status == "success"
    assert docs[2].status == "success"
    assert docs[1].status == "failed"
    assert "timeout" in (docs[1].error_message or "").lower()


@pytest.mark.asyncio
async def test_crawl_site_async_timeout_returns_graceful_error_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyCrawler:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def arun(self, url, config):
            await _hanging_arun(url, config)

    monkeypatch.setattr(site_module, "AsyncWebCrawler", DummyCrawler)

    result = await site_module.crawl_site_async("https://example.com", timeout=0.01)

    assert result.documents == []
    assert result.errors
    assert result.errors[0]["url"] == "https://example.com"
    assert "timeout" in result.errors[0]["error"].lower()
    assert result.stats["error_count"] >= 1


@pytest.mark.asyncio
async def test_mcp_crawl_site_timeout_error_returns_structured_failed_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_crawl_site_async(*args, **kwargs):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(crawler, "crawl_site_async", fake_crawl_site_async)

    out = await mcp_server.crawl_site(
        url="https://example.com",
        output_format="json",
        timeout=1,
    )
    payload = json.loads(out)

    assert payload["documents"][0]["status"] == "failed"
    assert "timed out" in payload["documents"][0]["error_message"].lower()
    assert payload["stats"]["failed_pages"] == 1
    assert payload["stats"]["error_count"] == 1


@pytest.mark.asyncio
async def test_search_retries_on_request_error_with_exponential_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"calls": 0, "sleeps": []}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": [{"title": "ok", "url": "https://example.com"}],
                "number_of_results": 1,
            }

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, path, params=None):
            state["calls"] += 1
            if state["calls"] == 1:
                req = httpx.Request("GET", "https://searx.test/search")
                raise httpx.RequestError("temporary network issue", request=req)
            return DummyResponse()

    async def fake_sleep(seconds: float):
        state["sleeps"].append(seconds)

    monkeypatch.setattr(mcp_server, "_get_searxng_client", lambda: DummyClient())
    monkeypatch.setattr(mcp_server.asyncio, "sleep", fake_sleep)

    out = await mcp_server.search(query="retry-me", max_retries=3)
    payload = json.loads(out)

    assert state["calls"] == 2
    assert state["sleeps"] == [0.5]
    assert payload["number_of_results"] == 1
    assert payload["results"][0]["title"] == "ok"


@pytest.mark.asyncio
async def test_search_does_not_retry_on_http_status_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {"calls": 0, "sleeps": 0}

    class DummyResponse:
        status_code = 500
        text = "server error"

        def raise_for_status(self):
            req = httpx.Request("GET", "https://searx.test/search")
            raise httpx.HTTPStatusError("boom", request=req, response=self)

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, path, params=None):
            state["calls"] += 1
            return DummyResponse()

    async def fake_sleep(seconds: float):
        state["sleeps"] += 1

    monkeypatch.setattr(mcp_server, "_get_searxng_client", lambda: DummyClient())
    monkeypatch.setattr(mcp_server.asyncio, "sleep", fake_sleep)

    out = await mcp_server.search(query="status-error", max_retries=3)
    payload = json.loads(out)

    assert state["calls"] == 1
    assert state["sleeps"] == 0
    assert "error" in payload
    assert payload["query"] == "status-error"
