"""Tests for HTTP Host, Origin, and CORS configuration."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


def _run_main(*arguments: str):
    from crawler import mcp_server

    mock_mcp = MagicMock()
    with (
        patch.object(mcp_server, "mcp", mock_mcp),
        patch.object(sys, "argv", ["crawl-mcp", *arguments]),
    ):
        mcp_server.main()
    mock_mcp.run.assert_called_once()
    return mock_mcp.run.call_args.kwargs


class TestHttpAllowlistIntegration:
    """Verify CLI allowlists are normalized at the FastMCP run boundary."""

    def test_omitted_allowlists_preserve_fastmcp_defaults(self) -> None:
        kwargs = _run_main("--transport", "http")

        assert kwargs["transport"] == "http"
        assert "allowed_hosts" not in kwargs
        assert "allowed_origins" not in kwargs
        assert "middleware" not in kwargs

    @pytest.mark.parametrize(
        ("raw_hosts", "expected"),
        [
            ("mcp.example.com", ["mcp.example.com"]),
            (
                " mcp.example.com, mcp.internal.example ",
                ["mcp.example.com", "mcp.internal.example"],
            ),
            ("mcp.example.com, ,mcp.internal.example,", ["mcp.example.com", "mcp.internal.example"]),
            ("*", ["*"]),
        ],
    )
    def test_allowed_hosts_are_normalized(self, raw_hosts, expected) -> None:
        kwargs = _run_main(
            "--transport", "http", "--allowed-hosts", raw_hosts
        )

        assert kwargs["allowed_hosts"] == expected

    def test_effectively_empty_hosts_do_not_override_defaults(self) -> None:
        kwargs = _run_main("--transport", "http", "--allowed-hosts", " , , ")

        assert "allowed_hosts" not in kwargs

    @pytest.mark.parametrize(
        ("raw_origins", "expected"),
        [
            ("http://localhost:3000", ["http://localhost:3000"]),
            (
                " http://localhost:3000, ,https://app.example.com ",
                ["http://localhost:3000", "https://app.example.com"],
            ),
            ("*", ["*"]),
        ],
    )
    def test_origins_reach_guard_and_cors_middleware(
        self, raw_origins, expected
    ) -> None:
        from starlette.middleware.cors import CORSMiddleware

        kwargs = _run_main(
            "--transport", "http", "--cors-origins", raw_origins
        )

        assert kwargs["allowed_origins"] == expected
        middleware = kwargs["middleware"]
        assert len(middleware) == 1
        assert middleware[0].cls is CORSMiddleware
        assert middleware[0].kwargs == {
            "allow_origins": expected,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

    def test_effectively_empty_origins_do_not_add_overrides(self) -> None:
        kwargs = _run_main("--transport", "http", "--cors-origins", " , ")

        assert "allowed_origins" not in kwargs
        assert "middleware" not in kwargs

    def test_stdio_ignores_all_http_only_configuration(self) -> None:
        from crawler import mcp_server

        kwargs = _run_main(
            "--transport",
            "stdio",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--allowed-hosts",
            "*",
            "--cors-origins",
            "*",
        )

        assert kwargs == {"transport": "stdio", "log_level": mcp_server.LOG_LEVEL_STR}
        for key in ("host", "port", "allowed_hosts", "allowed_origins", "middleware"):
            assert key not in kwargs


class TestFastMcpHttpGuard:
    """Exercise FastMCP's public ASGI Host/Origin guard."""

    @staticmethod
    def _request(app, *, host: str, origin: str | None = None):
        from starlette.testclient import TestClient

        headers = {"host": host}
        if origin is not None:
            headers["origin"] = origin
        with TestClient(app) as client:
            return client.get("/mcp", headers=headers)

    def test_default_rejects_untrusted_public_host(self) -> None:
        from fastmcp import FastMCP

        app = FastMCP("guard-test").http_app(host_origin_protection=True)
        response = self._request(app, host="public.example")
        assert response.status_code == 421

    def test_default_rejects_untrusted_origin(self) -> None:
        from fastmcp import FastMCP

        app = FastMCP("guard-test").http_app(host_origin_protection=True)
        response = self._request(
            app,
            host="localhost",
            origin="https://untrusted.example",
        )
        assert response.status_code == 403

    @pytest.mark.parametrize(
        ("allowed_hosts", "allowed_origins", "host", "origin"),
        [
            (["mcp.example.com"], ["https://app.example.com"], "mcp.example.com", "https://app.example.com"),
            (["*"], ["*"], "arbitrary.example", "https://arbitrary.example"),
        ],
    )
    def test_explicit_allowlists_pass_the_guard(
        self, allowed_hosts, allowed_origins, host, origin
    ) -> None:
        from fastmcp import FastMCP

        app = FastMCP("guard-test").http_app(
            host_origin_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=allowed_origins,
        )
        response = self._request(app, host=host, origin=origin)

        # GET reaches normal MCP request validation (406), not either guard.
        assert response.status_code == 406


class TestTransportEncoding:
    def test_stdio_invokes_encoding_configuration(self) -> None:
        from crawler import mcp_server

        with patch.object(mcp_server, "_configure_stdio_encoding") as configure:
            _run_main("--transport", "stdio")
        configure.assert_called_once()

    def test_http_skips_encoding_configuration(self) -> None:
        from crawler import mcp_server

        with patch.object(mcp_server, "_configure_stdio_encoding") as configure:
            _run_main("--transport", "http")
        configure.assert_not_called()
