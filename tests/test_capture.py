"""Tests for crawler.capture module."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from crawler.capture import capture_auth_state, capture_auth_state_sync


def _build_playwright_mocks(
    storage_state=None,
    page_url="https://example.com/dashboard",
    page_url_raises=False,
):
    """Build a full set of Playwright mocks."""
    mock_page = MagicMock()
    if page_url_raises:
        type(mock_page).url = PropertyMock(side_effect=Exception("closed"))
    else:
        type(mock_page).url = PropertyMock(return_value=page_url)
    mock_page.goto = AsyncMock()

    if storage_state is None:
        storage_state = {"cookies": [{"name": "a"}], "origins": []}

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.storage_state = AsyncMock(return_value=storage_state)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_pw = MagicMock()
    mock_pw.chromium = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw_cm = AsyncMock()
    mock_pw_cm.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw_cm.__aexit__ = AsyncMock(return_value=None)

    return mock_pw_cm, mock_page, mock_context, mock_browser


class TestCaptureAuthState:
    @pytest.mark.asyncio
    async def test_playwright_not_installed(self):
        """Should raise RuntimeError if playwright is missing."""
        with patch.dict(
            "sys.modules", {"playwright": None, "playwright.async_api": None}
        ):
            with pytest.raises((RuntimeError, ImportError)):
                await capture_auth_state(url="https://example.com")

    @pytest.mark.asyncio
    async def test_capture_with_wait_for_url(self):
        """Mock the Playwright flow with URL match."""
        mock_pw_cm, _, mock_context, _ = _build_playwright_mocks(
            page_url="https://example.com/dashboard"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "state.json")

            with patch(
                "playwright.async_api.async_playwright",
                return_value=mock_pw_cm,
            ):
                await capture_auth_state(
                    url="https://login.example.com",
                    output_path=output_path,
                    wait_for_url="/dashboard",
                    timeout=5,
                )

            assert os.path.exists(output_path)
            with open(output_path) as f:
                state = json.load(f)
            assert len(state["cookies"]) == 1

    @pytest.mark.asyncio
    async def test_capture_browser_closed(self):
        """Test when user closes the browser window."""
        mock_pw_cm, _, _, _ = _build_playwright_mocks(page_url_raises=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "state.json")

            with patch(
                "playwright.async_api.async_playwright",
                return_value=mock_pw_cm,
            ):
                await capture_auth_state(
                    url="https://login.example.com",
                    output_path=output_path,
                    timeout=1,
                )

            assert os.path.exists(output_path)

    @pytest.mark.asyncio
    async def test_capture_export_failure(self):
        """Test when storage state export fails."""
        mock_pw_cm, _, mock_context, _ = _build_playwright_mocks(
            page_url_raises=True
        )
        mock_context.storage_state = AsyncMock(
            side_effect=Exception("export failed")
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "state.json")

            with patch(
                "playwright.async_api.async_playwright",
                return_value=mock_pw_cm,
            ):
                with pytest.raises(Exception, match="export failed"):
                    await capture_auth_state(
                        url="https://login.example.com",
                        output_path=output_path,
                        timeout=1,
                    )

    @pytest.mark.asyncio
    async def test_capture_without_wait_for_url_timeout(self):
        """Test timeout without wait_for_url (no browser close)."""
        mock_pw_cm, _, _, _ = _build_playwright_mocks(
            page_url="https://login.example.com"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "state.json")

            with patch(
                "playwright.async_api.async_playwright",
                return_value=mock_pw_cm,
            ):
                await capture_auth_state(
                    url="https://login.example.com",
                    output_path=output_path,
                    timeout=1,
                )

            assert os.path.exists(output_path)

    @pytest.mark.asyncio
    async def test_capture_with_wait_for_url_browser_closed(self):
        """Test wait_for_url mode when browser is closed before match."""
        mock_pw_cm, _, _, _ = _build_playwright_mocks(page_url_raises=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "state.json")

            with patch(
                "playwright.async_api.async_playwright",
                return_value=mock_pw_cm,
            ):
                await capture_auth_state(
                    url="https://login.example.com",
                    output_path=output_path,
                    wait_for_url="/never_matches",
                    timeout=1,
                )

            assert os.path.exists(output_path)


class TestCaptureAuthStateSync:
    def test_sync_wrapper_exists(self):
        """Test that sync wrapper is callable."""
        assert callable(capture_auth_state_sync)
