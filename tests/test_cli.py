from __future__ import annotations

import argparse
from types import SimpleNamespace

import pytest

import crawler
from crawler import cli


def _doc() -> SimpleNamespace:
    return SimpleNamespace(
        request_url="https://example.com",
        final_url="https://example.com",
        status="success",
        markdown="# ok",
        error_message=None,
        metadata={},
        references=[],
    )


def test_parse_crawl_args_defaults_dedup_mode_exact() -> None:
    args = cli._parse_crawl_args(["https://example.com"])
    assert args.dedup_mode == "exact"


def test_parse_crawl_args_accepts_dedup_mode_off() -> None:
    args = cli._parse_crawl_args(["https://example.com", "--dedup-mode", "off"])
    assert args.dedup_mode == "off"


@pytest.mark.asyncio
async def test_run_crawl_async_forwards_dedup_mode_single(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    async def fake_crawl_page_async(url: str, *, dedup_mode: str = "exact"):
        captured["mode"] = dedup_mode
        return _doc()

    async def fake_crawl_pages_async(urls, *, concurrency=3, dedup_mode="exact"):
        return [_doc() for _ in urls]

    async def fake_crawl_site_async(url, **kwargs):
        return SimpleNamespace(
            documents=[_doc()],
            stats={"total_pages": 1, "successful_pages": 1, "failed_pages": 0},
        )

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)
    monkeypatch.setattr(crawler, "crawl_pages_async", fake_crawl_pages_async)
    monkeypatch.setattr(crawler, "crawl_site_async", fake_crawl_site_async)
    monkeypatch.setattr(cli, "_write_output", lambda *args, **kwargs: None)

    args = argparse.Namespace(
        urls=["https://example.com"],
        site=False,
        max_depth=2,
        max_pages=25,
        include_subdomains=False,
        concurrency=3,
        dedup_mode="off",
        json_output=False,
        output=None,
        remove_links=False,
    )

    code = await cli._run_crawl_async(args)
    assert code == 0
    assert captured["mode"] == "off"


@pytest.mark.asyncio
async def test_run_crawl_async_forwards_dedup_mode_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    async def fake_crawl_page_async(url: str, *, dedup_mode: str = "exact"):
        return _doc()

    async def fake_crawl_pages_async(urls, *, concurrency=3, dedup_mode="exact"):
        return [_doc() for _ in urls]

    async def fake_crawl_site_async(url, **kwargs):
        captured["mode"] = kwargs.get("dedup_mode")
        return SimpleNamespace(
            documents=[_doc()],
            stats={"total_pages": 1, "successful_pages": 1, "failed_pages": 0},
        )

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)
    monkeypatch.setattr(crawler, "crawl_pages_async", fake_crawl_pages_async)
    monkeypatch.setattr(crawler, "crawl_site_async", fake_crawl_site_async)
    monkeypatch.setattr(cli, "_write_output", lambda *args, **kwargs: None)

    args = argparse.Namespace(
        urls=["https://example.com"],
        site=True,
        max_depth=1,
        max_pages=5,
        include_subdomains=False,
        concurrency=3,
        dedup_mode="off",
        json_output=False,
        output=None,
        remove_links=False,
    )

    code = await cli._run_crawl_async(args)
    assert code == 0
    assert captured["mode"] == "off"
