"""End-to-end tests for crawler, search, and CLI.

These tests run against a local HTTP test server to keep the suite deterministic
and to avoid external availability dependencies.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator
from urllib.parse import parse_qs, urlparse

import pytest


class _IntegrationHandler(BaseHTTPRequestHandler):
    """Local deterministic test server for crawl + search flows."""

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/search":
            query = parse_qs(parsed.query).get("q", [""])[0]
            payload = {
                "query": query,
                "results": [
                    {
                        "title": "Local Result 1",
                        "url": "https://example.test/1",
                        "content": "Local test result content 1",
                        "engine": "local",
                    },
                    {
                        "title": "Local Result 2",
                        "url": "https://example.test/2",
                        "content": "Local test result content 2",
                        "engine": "local",
                    },
                ],
                "answers": [],
                "suggestions": ["local suggestion"],
                "corrections": [],
            }
            self._send_json(payload)
            return

        if path == "/cookies":
            cookies = self.headers.get("Cookie", "")
            self._send_html(
                (
                    "<html><body><main>"
                    "<h1>Cookies</h1>"
                    f"<p>{cookies}</p>"
                    "</main></body></html>"
                )
            )
            return

        if path == "/spa":
            self._send_html(
                """
                <html>
                  <body>
                    <main id="content">Loading...</main>
                    <script>
                      setTimeout(() => {
                        document.getElementById("content").innerText =
                          "SPA Ready Content";
                      }, 250);
                    </script>
                  </body>
                </html>
                """
            )
            return

        if path in {"", "/"}:
            self._send_html(
                (
                    "<html><body><main>"
                    "<h1>Example Domain</h1>"
                    "<p>Local integration page</p>"
                    "</main></body></html>"
                )
            )
            return

        self._send_html(
            "<html><body><main><h1>Not Found</h1></main></body></html>", status=404
        )


@pytest.fixture(scope="session")
def local_test_server() -> Iterator[str]:
    """Start one local HTTP server for all E2E tests."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _IntegrationHandler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_crawl_basic(local_test_server: str):
    """Baseline: crawl local page with no auth or SPA config."""
    from crawler import crawl_page_async

    doc = await crawl_page_async(f"{local_test_server}/")
    assert doc.status == "success"
    assert "Example Domain" in doc.markdown
    assert doc.final_url.startswith(local_test_server)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_crawl_with_cookies(local_test_server: str):
    """Auth crawl with cookie injection validated via local cookie echo."""
    from crawler import crawl_page_async
    from crawler.auth import AuthConfig

    auth = AuthConfig(
        cookies=[
            {
                "name": "test_session",
                "value": "abc123",
                "domain": "127.0.0.1",
                "path": "/",
            }
        ]
    )
    doc = await crawl_page_async(f"{local_test_server}/cookies", auth=auth)
    assert doc.status == "success"
    assert "test_session" in doc.markdown


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_crawl_with_storage_state(tmp_path: Path, local_test_server: str):
    """Auth crawl with storage-state file injection."""
    from crawler import crawl_page_async
    from crawler.auth import AuthConfig

    storage_state = {
        "cookies": [
            {
                "name": "ss_token",
                "value": "xyz789",
                "domain": "127.0.0.1",
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
    doc = await crawl_page_async(f"{local_test_server}/cookies", auth=auth)
    assert doc.status == "success"
    assert "ss_token" in doc.markdown


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_crawl_spa_with_delay(local_test_server: str):
    """SPA parameter threading: delay + wait_until preserve content readiness."""
    from crawler import crawl_page_async
    from crawler.config import build_markdown_run_config

    run_config = build_markdown_run_config()
    run_config.delay_before_return_html = 1.0
    run_config.wait_until = "load"

    doc = await crawl_page_async(f"{local_test_server}/spa", config=run_config)
    assert doc.status == "success"
    assert "SPA Ready Content" in doc.markdown


@pytest.mark.e2e
def test_cli_crawl_direct(local_test_server: str):
    """CLI subprocess: crawl local page, markdown to stdout."""
    result = subprocess.run(
        [sys.executable, "-m", "crawler.cli", f"{local_test_server}/"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr[:500]}"
    assert "Example Domain" in result.stdout


@pytest.mark.e2e
def test_cli_crawl_json_output(local_test_server: str):
    """CLI subprocess: crawl --json, validate JSON structure."""
    result = subprocess.run(
        [sys.executable, "-m", "crawler.cli", f"{local_test_server}/", "--json"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stderr: {result.stderr[:500]}"
    stdout = result.stdout
    json_start = stdout.find("{")
    assert json_start != -1, f"No JSON object found in stdout: {stdout[:300]}"
    data = json.loads(stdout[json_start:])
    assert data["status"] == "success"
    assert data["markdown"]


@pytest.mark.e2e
def test_cli_search(local_test_server: str):
    """CLI subprocess: search via search_main against local SearXNG stub."""
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
        env={**os.environ, "SEARXNG_URL": local_test_server},
    )
    assert result.returncode == 0, f"stderr: {result.stderr[:500]}"
    assert result.stdout.strip(), "Expected non-empty search output"
    assert "Search:" in result.stdout


@pytest.mark.e2e
def test_cli_capture_auth_smoke(local_test_server: str):
    """CLI subprocess: capture-auth smoke test (expect graceful failure)."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "crawler.cli",
            "capture-auth",
            "--url",
            f"{local_test_server}/",
            "--timeout",
            "2",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1, (
        f"Expected exit code 1 but got {result.returncode}. "
        f"stdout: {result.stdout[:200]}, stderr: {result.stderr[:200]}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert any(
        term in combined for term in ["capture", "error", "playwright", "timeout"]
    ), f"Expected failure indication in output, got: {combined[:300]}"


@pytest.mark.e2e
def test_search_python_api_sync(local_test_server: str):
    """Python API: search() sync wrapper against local SearXNG stub."""
    from crawler import SearchResult, search

    result = search("test query", max_results=3, searxng_url=local_test_server)
    assert isinstance(result, SearchResult)
    assert result.query
    assert len(result.results) > 0
    assert len(result.results) <= 3
    for item in result.results:
        assert item.title
        assert item.url


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_search_python_api_async(local_test_server: str):
    """Python API: search_async() against local SearXNG stub."""
    from crawler import SearchResult, search_async

    result = await search_async("test query", max_results=3, searxng_url=local_test_server)
    assert isinstance(result, SearchResult)
    assert result.query
    assert len(result.results) > 0
    assert len(result.results) <= 3
    for item in result.results:
        assert item.title
        assert item.url
