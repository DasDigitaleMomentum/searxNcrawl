"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_browser_auto_install(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests offline: never download Chromium during a test run."""
    monkeypatch.setenv("PLAYWRIGHT_AUTO_INSTALL", "false")


@pytest.fixture(autouse=True)
def _clear_search_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests offline: a local .env must not activate search providers."""
    for name in (
        "YDC_API_KEY", "SEARXNG_URL", "SEARXNG_USERNAME", "SEARXNG_PASSWORD",
        "SEARXNG_EXTRA_HEADERS",
    ):
        monkeypatch.delenv(name, raising=False)
