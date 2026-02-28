from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import crawler
import crawler.site as site_module
from crawler.auth import AuthConfigError, ResolvedAuth, resolve_auth


def test_resolve_auth_accepts_valid_storage_state(tmp_path) -> None:
    storage_state = tmp_path / "state.json"
    storage_state.write_text(
        json.dumps({"cookies": [], "origins": []}), encoding="utf-8"
    )

    resolved = resolve_auth({"storage_state": str(storage_state)})

    assert resolved is not None
    assert resolved.storage_state == str(storage_state.resolve())


def test_resolve_auth_missing_storage_state_file_raises(tmp_path) -> None:
    missing = tmp_path / "missing-state.json"

    with pytest.raises(AuthConfigError, match="file not found"):
        resolve_auth({"storage_state": str(missing)})


def test_resolve_auth_invalid_json_raises(tmp_path) -> None:
    storage_state = tmp_path / "state.json"
    storage_state.write_text("{not-json", encoding="utf-8")

    with pytest.raises(AuthConfigError, match="invalid JSON"):
        resolve_auth({"storage_state": str(storage_state)})


def test_resolve_auth_rejects_unsupported_auth_fields(tmp_path) -> None:
    storage_state = tmp_path / "state.json"
    storage_state.write_text(json.dumps({}), encoding="utf-8")

    with pytest.raises(AuthConfigError, match="Unsupported auth fields"):
        resolve_auth({"storage_state": str(storage_state), "profile": "default"})


@pytest.mark.asyncio
async def test_crawl_page_async_no_auth_keeps_existing_runtime_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {"crawler_config": "unset"}

    class DummyCrawler:
        def __init__(self, config=None):
            captured["crawler_config"] = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def arun(self, url, config):
            return [SimpleNamespace(url=url)]

    monkeypatch.setattr(crawler, "AsyncWebCrawler", DummyCrawler)
    monkeypatch.setattr(
        crawler,
        "build_document_from_result",
        lambda result, *, dedup_mode="exact": SimpleNamespace(
            status="success", request_url=result.url, dedup_mode=dedup_mode
        ),
    )

    doc = await crawler.crawl_page_async("https://example.com")

    assert doc.status == "success"
    assert captured["crawler_config"] is None


@pytest.mark.asyncio
async def test_crawl_page_async_threads_storage_state_to_browser_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    storage_state = tmp_path / "state.json"
    storage_state.write_text(json.dumps({}), encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_browser_config(**kwargs):
        captured["browser_kwargs"] = kwargs
        return SimpleNamespace(**kwargs)

    class DummyCrawler:
        def __init__(self, config=None):
            captured["crawler_config"] = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def arun(self, url, config):
            return [SimpleNamespace(url=url)]

    monkeypatch.setattr(crawler, "BrowserConfig", fake_browser_config)
    monkeypatch.setattr(crawler, "AsyncWebCrawler", DummyCrawler)
    monkeypatch.setattr(
        crawler,
        "build_document_from_result",
        lambda result, *, dedup_mode="exact": SimpleNamespace(
            status="success", request_url=result.url, dedup_mode=dedup_mode
        ),
    )

    await crawler.crawl_page_async(
        "https://example.com", auth={"storage_state": str(storage_state)}
    )

    assert captured["browser_kwargs"] == {"storage_state": str(storage_state.resolve())}
    assert getattr(captured["crawler_config"], "storage_state") == str(
        storage_state.resolve()
    )


@pytest.mark.asyncio
async def test_crawl_site_async_threads_resolved_storage_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        site_module,
        "resolve_auth",
        lambda auth: ResolvedAuth(storage_state="/tmp/fake-state.json"),
    )

    def fake_browser_config(**kwargs):
        captured["browser_kwargs"] = kwargs
        return SimpleNamespace(**kwargs)

    class DummyCrawler:
        def __init__(self, config=None):
            captured["crawler_config"] = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def arun(self, url, config):
            return []

    monkeypatch.setattr(site_module, "BrowserConfig", fake_browser_config)
    monkeypatch.setattr(site_module, "AsyncWebCrawler", DummyCrawler)

    result = await site_module.crawl_site_async("https://example.com", auth={})

    assert result.stats["total_pages"] == 0
    assert captured["browser_kwargs"] == {
        "use_persistent_context": False,
        "storage_state": "/tmp/fake-state.json",
    }
