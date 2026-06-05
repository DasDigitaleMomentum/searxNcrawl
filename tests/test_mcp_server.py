from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
async def test_mcp_crawl_forwards_dedup_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    captured: dict = {}

    # Set up a valid storage_state inside the allowed directory
    states_dir = tmp_path / "states"
    states_dir.mkdir()
    state_file = states_dir / "state.json"
    state_file.write_text(json.dumps({"cookies": []}), encoding="utf-8")
    monkeypatch.setattr(mcp_server, "STORAGE_STATE_DIR", str(states_dir))

    async def fake_crawl_page_async(
        url: str, *, dedup_mode: str = "exact", auth=None, timeout=None
    ):
        captured["mode"] = dedup_mode
        captured["auth"] = auth
        return _doc()

    async def fake_crawl_pages_async(
        urls, *, concurrency=3, dedup_mode="exact", auth=None, timeout=None
    ):
        return [_doc() for _ in urls]

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)
    monkeypatch.setattr(crawler, "crawl_pages_async", fake_crawl_pages_async)

    await mcp_server.crawl(
        urls=["https://example.com"],
        output_format="json",
        dedup_mode="off",
        storage_state=str(state_file),
    )

    assert captured["mode"] == "off"
    assert captured["auth"] == {"storage_state": str(state_file)}


@pytest.mark.asyncio
async def test_mcp_crawl_site_forwards_dedup_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    captured: dict = {}

    # Set up a valid storage_state inside the allowed directory
    states_dir = tmp_path / "states"
    states_dir.mkdir()
    state_file = states_dir / "state.json"
    state_file.write_text(json.dumps({"cookies": []}), encoding="utf-8")
    monkeypatch.setattr(mcp_server, "STORAGE_STATE_DIR", str(states_dir))

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
        storage_state=str(state_file),
    )

    assert captured["mode"] == "off"
    assert captured["auth"] == {"storage_state": str(state_file)}


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

    async def fake_crawl_page_async(
        url: str, *, dedup_mode: str = "exact", auth=None, timeout=None
    ):
        return _doc(metadata=metadata)

    async def fake_crawl_pages_async(
        urls, *, concurrency=3, dedup_mode="exact", auth=None, timeout=None
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
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Auth errors from storage_state validation are surfaced as failed docs."""
    # Point STORAGE_STATE_DIR to a real dir so the path confinement check
    # passes, but the file itself is missing so resolve_auth raises.
    states_dir = tmp_path / "states"
    states_dir.mkdir()
    monkeypatch.setattr(mcp_server, "STORAGE_STATE_DIR", str(states_dir))

    missing_file = states_dir / "missing.json"

    async def fake_crawl_page_async(
        url: str, *, dedup_mode: str = "exact", auth=None, timeout=None
    ):
        raise ValueError(f"Auth storage_state file not found: {missing_file}")

    async def fake_crawl_pages_async(
        urls, *, concurrency=3, dedup_mode="exact", auth=None, timeout=None
    ):
        return [_doc() for _ in urls]

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)
    monkeypatch.setattr(crawler, "crawl_pages_async", fake_crawl_pages_async)

    # _validate_mcp_storage_state will raise because the file doesn't exist.
    # This should propagate as AuthConfigError (not swallowed silently).
    from crawler.auth import AuthConfigError

    with pytest.raises(AuthConfigError, match="file not found"):
        await mcp_server.crawl(
            urls=["https://example.com"],
            output_format="json",
            storage_state=str(missing_file),
        )


def test_configure_stdio_encoding_calls_reconfigure() -> None:
    """UTF-8 stdio config should call reconfigure on both streams."""
    mock_stdout = MagicMock()
    mock_stderr = MagicMock()

    with (
        patch.object(mcp_server.sys, "stdout", mock_stdout),
        patch.object(mcp_server.sys, "stderr", mock_stderr),
    ):
        mcp_server._configure_stdio_encoding()

    mock_stdout.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")
    mock_stderr.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")


def test_configure_stdio_encoding_skips_streams_without_reconfigure() -> None:
    """Missing reconfigure should be a safe no-op."""

    class StreamWithoutReconfigure:
        pass

    with (
        patch.object(mcp_server.sys, "stdout", StreamWithoutReconfigure()),
        patch.object(mcp_server.sys, "stderr", StreamWithoutReconfigure()),
    ):
        mcp_server._configure_stdio_encoding()
