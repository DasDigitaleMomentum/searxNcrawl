from __future__ import annotations

from types import SimpleNamespace

import pytest

import crawler
from crawler.auth import ResolvedAuth


@pytest.mark.asyncio
async def test_crawl_page_async_forwards_dedup_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyCrawler:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def arun(self, url, config):
            return [SimpleNamespace(url=url)]

    captured: dict = {}

    def fake_builder(result, *, dedup_mode="exact"):
        captured["mode"] = dedup_mode
        return SimpleNamespace(status="success", request_url=result.url)

    monkeypatch.setattr(crawler, "AsyncWebCrawler", DummyCrawler)
    monkeypatch.setattr(crawler, "build_document_from_result", fake_builder)

    await crawler.crawl_page_async("https://example.com", dedup_mode="off")
    assert captured["mode"] == "off"


@pytest.mark.asyncio
async def test_crawl_pages_async_defaults_to_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    async def fake_crawl_page_async(
        url,
        *,
        config=None,
        dedup_mode="exact",
        auth=None,
    ):
        captured.append(dedup_mode)
        return SimpleNamespace(status="success", request_url=url)

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)

    docs = await crawler.crawl_pages_async(["https://a", "https://b"])

    assert len(docs) == 2
    assert captured == ["exact", "exact"]


def test_crawl_site_wrapper_forwards_dedup_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    async def fake_site_crawl(url, **kwargs):
        captured["mode"] = kwargs.get("dedup_mode")
        return SimpleNamespace(documents=[], errors=[], stats={})

    monkeypatch.setattr(crawler, "crawl_site_async", fake_site_crawl)

    result = crawler.crawl_site("https://example.com", dedup_mode="off")

    assert captured["mode"] == "off"
    assert result.documents == []


@pytest.mark.asyncio
async def test_crawl_pages_async_forwards_auth_to_crawl_page(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    captured: list[ResolvedAuth | None] = []

    storage_state = tmp_path / "state.json"
    storage_state.write_text("{}", encoding="utf-8")

    async def fake_crawl_page_async(url, *, config=None, dedup_mode="exact", auth=None):
        captured.append(auth)
        return SimpleNamespace(status="success", request_url=url)

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)

    docs = await crawler.crawl_pages_async(
        ["https://a", "https://b"],
        auth={"storage_state": str(storage_state)},
    )

    assert len(docs) == 2
    resolved_items = [item for item in captured if isinstance(item, ResolvedAuth)]
    assert len(resolved_items) == 2
    assert [item.storage_state for item in resolved_items] == [
        str(storage_state),
        str(storage_state),
    ]
