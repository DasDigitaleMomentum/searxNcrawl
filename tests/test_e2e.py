"""End-to-end tests for crawler, search, and CLI.

These tests hit real network services (httpbin.org, example.com, SearXNG)
and require Playwright + Chromium to be installed. Every test is decorated
with ``@pytest.mark.e2e`` and uses skip guards so the suite degrades
gracefully when external dependencies are unavailable.

Run only E2E tests::

    pytest tests/test_e2e.py -m e2e -v

Exclude E2E tests (deterministic baseline)::

    pytest tests/ -m "not e2e" -q
"""

from __future__ import annotations

import functools
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Skip-condition helpers (evaluated once at import time via lru_cache)
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _has_network() -> bool:
    """Return True if httpbin.org is reachable."""
    try:
        import httpx

        resp = httpx.get("https://httpbin.org/get", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


@functools.lru_cache(maxsize=1)
def _has_searxng() -> bool:
    """Return True if SEARXNG_URL is set and the instance responds."""
    try:
        # Try loading .env the same way the CLI does
        try:
            from dotenv import load_dotenv

            local_env = Path.cwd() / ".env"
            if local_env.is_file():
                load_dotenv(local_env)
        except ImportError:
            pass

        url = os.getenv("SEARXNG_URL")
        if not url:
            return False

        import httpx

        resp = httpx.get(
            f"{url.rstrip('/')}/search",
            params={"q": "test", "format": "json"},
            timeout=5,
        )
        return resp.status_code == 200
    except Exception:
        return False


@functools.lru_cache(maxsize=1)
def _has_playwright() -> bool:
    """Return True if Playwright + Chromium are installed and usable."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Reusable skip decorators
# ---------------------------------------------------------------------------

requires_network = pytest.mark.skipif(
    not _has_network(), reason="No network access (httpbin.org unreachable)"
)
requires_searxng = pytest.mark.skipif(
    not _has_searxng(), reason="SearXNG not available"
)
requires_playwright = pytest.mark.skipif(
    not _has_playwright(), reason="Playwright/Chromium not available"
)


# ===================================================================
# E2E Tests
# ===================================================================


@pytest.mark.e2e
@requires_network
@requires_playwright
async def test_crawl_basic():
    """Baseline: crawl example.com with no auth or SPA config."""
    from crawler import crawl_page_async

    doc = await crawl_page_async("https://example.com")
    assert doc.status == "success"
    assert "Example Domain" in doc.markdown
    assert doc.final_url.startswith("https://example.com")


@pytest.mark.e2e
@requires_network
@requires_playwright
async def test_crawl_with_cookies():
    """Auth crawl with cookie injection, validated via httpbin echo."""
    from crawler import crawl_page_async
    from crawler.auth import AuthConfig

    auth = AuthConfig(
        cookies=[
            {
                "name": "test_session",
                "value": "abc123",
                "domain": "httpbin.org",
                "path": "/",
            }
        ]
    )
    doc = await crawl_page_async("https://httpbin.org/cookies", auth=auth)
    assert doc.status == "success"
    assert "test_session" in doc.markdown


@pytest.mark.e2e
@requires_network
@requires_playwright
async def test_crawl_with_storage_state(tmp_path: Path):
    """Auth crawl with storage-state file injection."""
    from crawler import crawl_page_async
    from crawler.auth import AuthConfig

    storage_state = {
        "cookies": [
            {
                "name": "ss_token",
                "value": "xyz789",
                "domain": "httpbin.org",
                "path": "/",
                "secure": False,
                "httpOnly": False,
                "sameSite": "Lax",
                "expires": -1,
            }
        ],
        "origins": [],
    }
    ss_file = tmp_path / "storage_state.json"
    ss_file.write_text(json.dumps(storage_state))

    auth = AuthConfig(storage_state=str(ss_file))
    doc = await crawl_page_async("https://httpbin.org/cookies", auth=auth)
    assert doc.status == "success"
    assert "ss_token" in doc.markdown


@pytest.mark.e2e
@requires_network
@requires_playwright
async def test_crawl_spa_with_delay():
    """SPA parameter threading: delay + wait_until don't break the crawl."""
    from crawler import crawl_page_async
    from crawler.config import build_markdown_run_config

    run_config = build_markdown_run_config()
    run_config.delay_before_return_html = 1.0
    run_config.wait_until = "load"

    doc = await crawl_page_async("https://example.com", config=run_config)
    assert doc.status == "success"
    assert "Example Domain" in doc.markdown


@pytest.mark.e2e
@requires_network
@requires_playwright
def test_cli_crawl_direct():
    """CLI subprocess: crawl example.com, markdown to stdout."""
    result = subprocess.run(
        [sys.executable, "-m", "crawler.cli", "https://example.com"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr[:500]}"
    assert "Example Domain" in result.stdout


@pytest.mark.e2e
@requires_network
@requires_playwright
def test_cli_crawl_json_output():
    """CLI subprocess: crawl --json, validate JSON structure."""
    result = subprocess.run(
        [sys.executable, "-m", "crawler.cli", "https://example.com", "--json"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr[:500]}"
    # crawl4ai may write progress lines to stdout before the JSON blob;
    # extract the JSON object by finding the first '{' character.
    stdout = result.stdout
    json_start = stdout.find("{")
    assert json_start != -1, f"No JSON object found in stdout: {stdout[:300]}"
    data = json.loads(stdout[json_start:])
    assert data["status"] == "success"
    assert data["markdown"]


@pytest.mark.e2e
@requires_searxng
def test_cli_search():
    """CLI subprocess: search via search_main against real SearXNG."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from crawler.cli import search_main; "
                "import sys; "
                "sys.exit(search_main(['python', '--max-results', '3']))"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ},
    )
    assert result.returncode == 0, f"stderr: {result.stderr[:500]}"
    assert result.stdout.strip(), "Expected non-empty search output"
    assert "Search:" in result.stdout


@pytest.mark.e2e
@requires_playwright
def test_cli_capture_auth_smoke():
    """CLI subprocess: capture-auth smoke test (expect graceful failure)."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "crawler.cli",
            "capture-auth",
            "--url",
            "https://example.com",
            "--timeout",
            "2",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    # In a headless environment, capture-auth should fail gracefully (exit 1).
    # It should NOT hang or crash with an unhandled exception.
    assert result.returncode == 1, (
        f"Expected exit code 1 but got {result.returncode}. "
        f"stdout: {result.stdout[:200]}, stderr: {result.stderr[:200]}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert any(
        term in combined for term in ["capture", "error", "playwright", "timeout"]
    ), f"Expected failure indication in output, got: {combined[:300]}"


@pytest.mark.e2e
@requires_searxng
def test_search_python_api_sync():
    """Python API: search() sync wrapper against real SearXNG."""
    from crawler import SearchResult, search

    result = search("test query", max_results=3)
    assert isinstance(result, SearchResult)
    assert result.query  # SearXNG may normalise the query string
    assert len(result.results) > 0
    assert len(result.results) <= 3
    for item in result.results:
        assert item.title
        assert item.url


@pytest.mark.e2e
@requires_searxng
@pytest.mark.asyncio
async def test_search_python_api_async():
    """Python API: search_async() against real SearXNG."""
    from crawler import SearchResult, search_async

    result = await search_async("test query", max_results=3)
    assert isinstance(result, SearchResult)
    assert result.query
    assert len(result.results) > 0
    assert len(result.results) <= 3
    for item in result.results:
        assert item.title
        assert item.url
