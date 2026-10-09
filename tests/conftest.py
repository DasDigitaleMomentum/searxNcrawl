"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_browser_auto_install(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests offline: never download Chromium during a test run."""
    monkeypatch.setenv("PLAYWRIGHT_AUTO_INSTALL", "false")
