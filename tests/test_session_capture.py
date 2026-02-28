from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from crawler import cli
from crawler.session_capture import (
    SessionCaptureConfigError,
    capture_session_async,
)


@pytest.mark.asyncio
async def test_capture_session_success_writes_storage_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "state.json"

    async def fake_flow(**kwargs):
        return {
            "status": "success",
            "message": "ok",
            "final_url": "https://example.com/dashboard",
            "storage_state": {"cookies": [], "origins": []},
        }

    monkeypatch.setattr("crawler.session_capture._execute_capture_flow", fake_flow)

    result = await capture_session_async(
        str(output),
        completion_url_pattern=r"https://example.com/dashboard.*",
    )

    assert result.status == "success"
    assert result.storage_state_path == str(output.resolve())
    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8"))["cookies"] == []


@pytest.mark.asyncio
async def test_capture_session_timeout_returns_explicit_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "state.json"

    async def fake_flow(**kwargs):
        return {
            "status": "timeout",
            "message": "timed out",
            "final_url": "https://example.com/login",
        }

    monkeypatch.setattr("crawler.session_capture._execute_capture_flow", fake_flow)

    result = await capture_session_async(
        str(output),
        completion_url_pattern=r"https://example.com/dashboard.*",
        timeout_seconds=1,
    )

    assert result.status == "timeout"
    assert "timed out" in result.message
    assert result.storage_state_path is None
    assert not output.exists()


@pytest.mark.asyncio
async def test_capture_session_abort_returns_explicit_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "state.json"

    async def fake_flow(**kwargs):
        return {
            "status": "abort",
            "message": "user closed browser",
            "final_url": "https://example.com/login",
        }

    monkeypatch.setattr("crawler.session_capture._execute_capture_flow", fake_flow)

    result = await capture_session_async(
        str(output),
        completion_url_pattern=r"https://example.com/dashboard.*",
    )

    assert result.status == "abort"
    assert "closed" in result.message
    assert result.storage_state_path is None
    assert not output.exists()


@pytest.mark.asyncio
async def test_capture_session_requires_overwrite_for_existing_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "state.json"
    output.write_text("{}", encoding="utf-8")

    async def fake_flow(**kwargs):
        return {
            "status": "success",
            "message": "ok",
            "final_url": "https://example.com/dashboard",
            "storage_state": {"cookies": [], "origins": []},
        }

    monkeypatch.setattr("crawler.session_capture._execute_capture_flow", fake_flow)

    with pytest.raises(SessionCaptureConfigError, match="already exists"):
        await capture_session_async(
            str(output),
            completion_url_pattern=r"https://example.com/dashboard.*",
            overwrite=False,
        )


@pytest.mark.asyncio
async def test_run_capture_async_cli_exit_codes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_capture_success(*args, **kwargs):
        return argparse.Namespace(
            status="success",
            message="ok",
            storage_state_path="/tmp/state.json",
            final_url="https://example.com/dashboard",
        )

    async def fake_capture_timeout(*args, **kwargs):
        return argparse.Namespace(
            status="timeout",
            message="timed out",
            storage_state_path=None,
            final_url="https://example.com/login",
        )

    async def fake_capture_abort(*args, **kwargs):
        return argparse.Namespace(
            status="abort",
            message="aborted",
            storage_state_path=None,
            final_url="https://example.com/login",
        )

    args = argparse.Namespace(
        output="/tmp/state.json",
        completion_url="https://example.com/dashboard.*",
        start_url="https://example.com/login",
        timeout=10.0,
        overwrite=False,
        headless=False,
        verbose=False,
    )

    monkeypatch.setattr(cli, "capture_session_async", fake_capture_success)
    assert await cli._run_capture_async(args) == 0

    monkeypatch.setattr(cli, "capture_session_async", fake_capture_timeout)
    assert await cli._run_capture_async(args) == 2

    monkeypatch.setattr(cli, "capture_session_async", fake_capture_abort)
    assert await cli._run_capture_async(args) == 130


def test_parse_capture_args_includes_required_and_flags() -> None:
    args = cli._parse_capture_args(
        [
            "--start-url",
            "https://example.com/login",
            "--completion-url",
            "https://example.com/dashboard.*",
            "--output",
            "./state.json",
            "--timeout",
            "42",
            "--overwrite",
            "--headless",
        ]
    )

    assert args.start_url == "https://example.com/login"
    assert args.completion_url == "https://example.com/dashboard.*"
    assert args.output == "./state.json"
    assert args.timeout == 42
    assert args.overwrite is True
    assert args.headless is True
