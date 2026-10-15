from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

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


def _ref(index: int, href: str, label: str) -> SimpleNamespace:
    return SimpleNamespace(index=index, href=href, label=label)


def _doc_with(url: str, references: list[SimpleNamespace]) -> SimpleNamespace:
    return SimpleNamespace(
        request_url=url,
        final_url=url,
        status="success",
        markdown="# markdown",
        error_message=None,
        metadata={},
        references=references,
    )


def _write_links_output(
    docs: list[SimpleNamespace],
    *,
    output: str | None,
    json_output: bool,
) -> None:
    cli._write_output(
        cast(list, docs),
        output=output,
        json_output=json_output,
        links_only=True,
    )


def test_parse_crawl_args_defaults_dedup_mode_exact() -> None:
    args = cli._parse_crawl_args(["https://example.com"])
    assert args.dedup_mode == "exact"


def test_parse_crawl_args_accepts_dedup_mode_off() -> None:
    args = cli._parse_crawl_args(["https://example.com", "--dedup-mode", "off"])
    assert args.dedup_mode == "off"


def test_parse_crawl_args_accepts_storage_state() -> None:
    args = cli._parse_crawl_args(
        ["https://example.com", "--storage-state", "./state.json"]
    )
    assert args.storage_state == "./state.json"


def test_parse_crawl_args_accepts_links_only() -> None:
    args = cli._parse_crawl_args(["https://example.com", "--links-only"])
    assert args.links_only is True


def test_parse_crawl_args_rejects_links_only_with_remove_links() -> None:
    with pytest.raises(SystemExit):
        cli._parse_crawl_args(["https://example.com", "--links-only", "--remove-links"])


def test_parse_crawl_args_help_includes_links_only(
    capsys: pytest.CaptureFixture,
) -> None:
    with pytest.raises(SystemExit):
        cli._parse_crawl_args(["--help"])
    out = capsys.readouterr().out
    assert "--links-only" in out


@pytest.mark.asyncio
async def test_run_crawl_async_forwards_dedup_mode_single(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    async def fake_crawl_page_async(url: str, *, dedup_mode: str = "exact", auth=None):
        captured["mode"] = dedup_mode
        captured["auth"] = auth
        return _doc()

    async def fake_crawl_pages_async(
        urls, *, concurrency=3, dedup_mode="exact", auth=None
    ):
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
        storage_state="/tmp/state.json",
        json_output=False,
        output=None,
        remove_links=False,
        links_only=False,
    )

    code = await cli._run_crawl_async(args)
    assert code == 0
    assert captured["mode"] == "off"
    assert captured["auth"] == {"storage_state": "/tmp/state.json"}


@pytest.mark.asyncio
async def test_run_crawl_async_forwards_dedup_mode_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    async def fake_crawl_page_async(url: str, *, dedup_mode: str = "exact", auth=None):
        return _doc()

    async def fake_crawl_pages_async(
        urls, *, concurrency=3, dedup_mode="exact", auth=None
    ):
        return [_doc() for _ in urls]

    async def fake_crawl_site_async(url, **kwargs):
        captured["mode"] = kwargs.get("dedup_mode")
        captured["auth"] = kwargs.get("auth")
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
        storage_state="/tmp/state.json",
        json_output=False,
        output=None,
        remove_links=False,
        links_only=False,
    )

    code = await cli._run_crawl_async(args)
    assert code == 0
    assert captured["mode"] == "off"
    assert captured["auth"] == {"storage_state": "/tmp/state.json"}


@pytest.mark.asyncio
async def test_run_crawl_async_auth_error_propagates_from_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_crawl_page_async(url: str, *, dedup_mode: str = "exact", auth=None):
        raise ValueError("Auth storage_state file not found: /tmp/missing.json")

    async def fake_crawl_pages_async(
        urls, *, concurrency=3, dedup_mode="exact", auth=None
    ):
        return [_doc() for _ in urls]

    async def fake_crawl_site_async(url, **kwargs):
        return SimpleNamespace(documents=[_doc()], stats={})

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
        dedup_mode="exact",
        storage_state="/tmp/missing.json",
        json_output=False,
        output=None,
        remove_links=False,
        links_only=False,
    )

    with pytest.raises(ValueError, match="Auth storage_state file not found"):
        await cli._run_crawl_async(args)


def test_write_output_links_only_single_doc_markdown_stdout(
    capsys: pytest.CaptureFixture,
) -> None:
    doc = _doc_with(
        "https://example.com",
        [_ref(1, "https://a.com", "A"), _ref(2, "https://b.com", "B")],
    )

    _write_links_output([doc], output=None, json_output=False)

    out = capsys.readouterr().out.strip()
    assert out == "[1] A - https://a.com\n[2] B - https://b.com"


def test_write_output_links_only_single_doc_markdown_file(tmp_path: Path) -> None:
    doc = _doc_with("https://example.com", [_ref(1, "https://a.com", "A")])
    output = tmp_path / "links.md"

    _write_links_output([doc], output=str(output), json_output=False)

    assert output.read_text() == "[1] A - https://a.com"


def test_write_output_links_only_single_doc_json_stdout(
    capsys: pytest.CaptureFixture,
) -> None:
    doc = _doc_with("https://example.com", [_ref(1, "https://a.com", "A")])

    _write_links_output([doc], output=None, json_output=True)

    payload = json.loads(capsys.readouterr().out)
    assert payload == [{"index": 1, "href": "https://a.com", "label": "A"}]


def test_write_output_links_only_multi_doc_markdown_stdout_with_headers(
    capsys: pytest.CaptureFixture,
) -> None:
    docs = [
        _doc_with("https://a.com", [_ref(1, "https://a.com/1", "A1")]),
        _doc_with("https://b.com", [_ref(2, "https://b.com/2", "B2")]),
    ]

    _write_links_output(docs, output=None, json_output=False)

    out = capsys.readouterr().out
    assert "--- https://a.com ---" in out
    assert "--- https://b.com ---" in out
    assert "[1] A1 - https://a.com/1" in out
    assert "[2] B2 - https://b.com/2" in out


def test_write_output_links_only_multi_doc_markdown_to_single_file(
    tmp_path: Path,
) -> None:
    docs = [
        _doc_with("https://a.com", [_ref(1, "https://a.com/1", "A1")]),
        _doc_with("https://b.com", [_ref(2, "https://b.com/2", "B2")]),
    ]
    output = tmp_path / "combined.md"

    _write_links_output(docs, output=str(output), json_output=False)

    text = output.read_text()
    assert "--- https://a.com ---" in text
    assert "--- https://b.com ---" in text


def test_write_output_links_only_multi_doc_markdown_to_directory(
    tmp_path: Path,
) -> None:
    docs = [
        _doc_with("https://a.com", [_ref(1, "https://a.com/1", "A1")]),
        _doc_with("https://b.com/path", [_ref(2, "https://b.com/2", "B2")]),
    ]
    output_dir = tmp_path / "out"

    _write_links_output(docs, output=str(output_dir), json_output=False)

    file_a = output_dir / f"{cli._url_to_filename('https://a.com')}.md"
    file_b = output_dir / f"{cli._url_to_filename('https://b.com/path')}.md"
    assert file_a.is_file()
    assert file_b.is_file()
    assert file_a.read_text() == "[1] A1 - https://a.com/1"


@pytest.mark.asyncio
async def test_run_crawl_async_site_links_only_mode_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    async def fake_crawl_page_async(url: str, *, dedup_mode: str = "exact", auth=None):
        return _doc()

    async def fake_crawl_pages_async(
        urls, *, concurrency=3, dedup_mode="exact", auth=None
    ):
        return [_doc() for _ in urls]

    async def fake_crawl_site_async(url, **kwargs):
        return SimpleNamespace(
            documents=[
                _doc_with("https://example.com/a", [_ref(1, "https://x.com", "X")]),
                _doc_with("https://example.com/b", [_ref(2, "https://y.com", "Y")]),
            ],
            stats={"total_pages": 2, "successful_pages": 2, "failed_pages": 0},
        )

    def fake_write_output(*args, **kwargs):
        captured["links_only"] = kwargs.get("links_only")
        captured["doc_count"] = len(args[0])

    monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)
    monkeypatch.setattr(crawler, "crawl_pages_async", fake_crawl_pages_async)
    monkeypatch.setattr(crawler, "crawl_site_async", fake_crawl_site_async)
    monkeypatch.setattr(cli, "_write_output", fake_write_output)

    args = argparse.Namespace(
        urls=["https://example.com"],
        site=True,
        max_depth=1,
        max_pages=5,
        include_subdomains=False,
        concurrency=3,
        dedup_mode="exact",
        storage_state=None,
        json_output=False,
        output=None,
        remove_links=False,
        links_only=True,
    )

    code = await cli._run_crawl_async(args)
    assert code == 0
    assert captured["links_only"] is True
    assert captured["doc_count"] == 2


def test_write_output_links_only_zero_references_markdown_message(
    capsys: pytest.CaptureFixture,
) -> None:
    doc = _doc_with("https://example.com/empty", [])

    _write_links_output([doc], output=None, json_output=False)

    assert (
        capsys.readouterr().out.strip()
        == "No references found for https://example.com/empty"
    )


def test_write_output_links_only_zero_references_json_empty_array(
    capsys: pytest.CaptureFixture,
) -> None:
    doc = _doc_with("https://example.com/empty", [])

    _write_links_output([doc], output=None, json_output=True)

    payload = json.loads(capsys.readouterr().out)
    assert payload == []
