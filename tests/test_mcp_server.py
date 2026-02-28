from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import crawler
from crawler import mcp_server


def _doc(metadata: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        request_url="https://example.com",
        final_url="https://example.com",
        status="success",
        markdown="# ok",
        error_message=None,
        metadata=metadata or {},
        references=[],
    )


@pytest.mark.asyncio
async def test_mcp_crawl_forwards_dedup_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    async def fake_crawl_page_async(url: str, *, dedup_mode: str = "exact", auth=None):
        captured["mode"] = dedup_mode
        captured["auth"] = auth
        return _doc()

    async def fake_crawl_pages_async(
        urls, *, concurrency=3, dedup_mode="exact", auth=None
    ):
        return [_doc() for _ in urls]

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)
    monkeypatch.setattr(crawler, "crawl_pages_async", fake_crawl_pages_async)

    await mcp_server.crawl(
        urls=["https://example.com"],
        output_format="json",
        dedup_mode="off",
        storage_state="/tmp/state.json",
    )

    assert captured["mode"] == "off"
    assert captured["auth"] == {"storage_state": "/tmp/state.json"}


@pytest.mark.asyncio
async def test_mcp_crawl_site_forwards_dedup_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    async def fake_site_crawl(url: str, **kwargs):
        captured["mode"] = kwargs.get("dedup_mode")
        captured["auth"] = kwargs.get("auth")
        return SimpleNamespace(
            documents=[_doc()],
            stats={"total_pages": 1, "successful_pages": 1, "failed_pages": 0},
        )

    monkeypatch.setattr(crawler, "crawl_site_async", fake_site_crawl)

    await mcp_server.crawl_site(
        url="https://example.com",
        output_format="json",
        dedup_mode="off",
        storage_state="/tmp/state.json",
    )

    assert captured["mode"] == "off"
    assert captured["auth"] == {"storage_state": "/tmp/state.json"}


@pytest.mark.asyncio
async def test_mcp_json_output_includes_builder_guardrail_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata = {
        "dedup_mode": "exact",
        "dedup_sections_total": 4,
        "dedup_sections_removed": 2,
        "dedup_guardrail_checked": True,
        "dedup_guardrail_triggered": True,
        "dedup_guardrail_reason": "high-removal-rate",
    }

    async def fake_crawl_page_async(url: str, *, dedup_mode: str = "exact", auth=None):
        return _doc(metadata=metadata)

    async def fake_crawl_pages_async(
        urls, *, concurrency=3, dedup_mode="exact", auth=None
    ):
        return [_doc(metadata=metadata) for _ in urls]

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)
    monkeypatch.setattr(crawler, "crawl_pages_async", fake_crawl_pages_async)

    out = await mcp_server.crawl(urls=["https://example.com"], output_format="json")
    payload = json.loads(out)

    doc_meta = payload["documents"][0]["metadata"]
    assert doc_meta["dedup_mode"] == "exact"
    assert doc_meta["dedup_guardrail_checked"] is True
    assert doc_meta["dedup_guardrail_triggered"] is True
    assert doc_meta["dedup_guardrail_reason"] == "high-removal-rate"


@pytest.mark.asyncio
async def test_mcp_crawl_auth_error_propagates_from_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_crawl_page_async(url: str, *, dedup_mode: str = "exact", auth=None):
        raise ValueError("Auth storage_state file not found: /tmp/missing.json")

    async def fake_crawl_pages_async(
        urls, *, concurrency=3, dedup_mode="exact", auth=None
    ):
        return [_doc() for _ in urls]

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)
    monkeypatch.setattr(crawler, "crawl_pages_async", fake_crawl_pages_async)

    out = await mcp_server.crawl(
        urls=["https://example.com"],
        output_format="json",
        storage_state="/tmp/missing.json",
    )
    payload = json.loads(out)
    assert payload["documents"][0]["status"] == "failed"
    assert (
        "Auth storage_state file not found" in payload["documents"][0]["error_message"]
    )
