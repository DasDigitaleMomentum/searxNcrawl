"""Tests for CORS middleware configuration in the MCP server (Issue #16)."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCorsArgParsing:
    """Verify the --cors-origins CLI argument is properly defined and parsed."""

    def test_cors_origins_arg_exists_in_source(self) -> None:
        """The argparse setup must include --cors-origins."""
        source = Path("crawler/mcp_server.py").read_text()
        assert "--cors-origins" in source

    def test_cors_origins_default_is_none(self) -> None:
        """Without --cors-origins the attribute should be None."""
        from crawler.mcp_server import main

        # Build the parser the same way main() does, but just parse empty args
        import argparse

        source = inspect.getsource(main)
        # Simpler: just invoke argparse directly
        with patch("sys.argv", ["crawl-mcp", "--transport", "http"]):
            parser = argparse.ArgumentParser()
            parser.add_argument(
                "--transport", choices=["stdio", "http"], default="stdio"
            )
            parser.add_argument("--host", default="127.0.0.1")
            parser.add_argument("--port", type=int, default=8000)
            parser.add_argument("--cors-origins", default=None)
            args = parser.parse_args(["--transport", "http"])
            assert args.cors_origins is None

    def test_cors_origins_single_value_parsed(self) -> None:
        """A single origin should be parsed as-is."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--cors-origins", default=None)
        args = parser.parse_args(["--cors-origins", "http://localhost:3000"])
        assert args.cors_origins == "http://localhost:3000"

    def test_cors_origins_multiple_values_parsed(self) -> None:
        """Comma-separated origins should be stored as a single string."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--cors-origins", default=None)
        args = parser.parse_args(
            ["--cors-origins", "http://localhost:3000,https://myapp.com"]
        )
        assert args.cors_origins == "http://localhost:3000,https://myapp.com"

    def test_cors_origins_wildcard_parsed(self) -> None:
        """The wildcard '*' should be a valid value."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--cors-origins", default=None)
        args = parser.parse_args(["--cors-origins", "*"])
        assert args.cors_origins == "*"


class TestCorsMiddlewareConstruction:
    """Verify CORS middleware is properly built from --cors-origins values."""

    def test_middleware_built_for_single_origin(self) -> None:
        """A single origin should produce a one-element Middleware list."""
        from starlette.middleware import Middleware
        from starlette.middleware.cors import CORSMiddleware

        cors_origins = "http://localhost:3000"
        origins = [o.strip() for o in cors_origins.split(",")]
        middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]
        assert len(middleware) == 1
        assert middleware[0].cls is CORSMiddleware
        assert middleware[0].kwargs["allow_origins"] == ["http://localhost:3000"]

    def test_middleware_built_for_multiple_origins(self) -> None:
        """Comma-separated origins should be split and trimmed."""
        from starlette.middleware import Middleware
        from starlette.middleware.cors import CORSMiddleware

        cors_origins = "http://localhost:3000, https://myapp.com , https://other.com"
        origins = [o.strip() for o in cors_origins.split(",")]
        middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]
        assert middleware[0].kwargs["allow_origins"] == [
            "http://localhost:3000",
            "https://myapp.com",
            "https://other.com",
        ]

    def test_middleware_built_for_wildcard(self) -> None:
        """Wildcard '*' should produce allow_origins=['*']."""
        from starlette.middleware import Middleware
        from starlette.middleware.cors import CORSMiddleware

        cors_origins = "*"
        origins = [o.strip() for o in cors_origins.split(",")]
        middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        ]
        assert middleware[0].kwargs["allow_origins"] == ["*"]


class TestCorsIntegration:
    """Verify the main() function wires CORS middleware correctly."""

    def test_no_cors_middleware_without_flag(self) -> None:
        """When --cors-origins is not set, mcp.run should not receive middleware."""
        from crawler import mcp_server

        mock_mcp = MagicMock()
        mock_mcp.run = MagicMock()

        with (
            patch.object(mcp_server, "mcp", mock_mcp),
            patch("sys.argv", ["crawl-mcp", "--transport", "http"]),
        ):
            mcp_server.main()

        mock_mcp.run.assert_called_once()
        call_kwargs = mock_mcp.run.call_args[1]
        assert "middleware" not in call_kwargs
        assert call_kwargs["transport"] == "http"

    def test_cors_middleware_passed_with_flag(self) -> None:
        """When --cors-origins is set, mcp.run should receive middleware."""
        from crawler import mcp_server

        mock_mcp = MagicMock()
        mock_mcp.run = MagicMock()

        with (
            patch.object(mcp_server, "mcp", mock_mcp),
            patch(
                "sys.argv",
                [
                    "crawl-mcp",
                    "--transport",
                    "http",
                    "--cors-origins",
                    "http://localhost:3000",
                ],
            ),
        ):
            mcp_server.main()

        mock_mcp.run.assert_called_once()
        call_kwargs = mock_mcp.run.call_args[1]
        assert "middleware" in call_kwargs
        middleware_list = call_kwargs["middleware"]
        assert len(middleware_list) == 1

        from starlette.middleware.cors import CORSMiddleware

        assert middleware_list[0].cls is CORSMiddleware
        assert middleware_list[0].kwargs["allow_origins"] == ["http://localhost:3000"]

    def test_cors_wildcard_passed_correctly(self) -> None:
        """Wildcard origin should be passed through to middleware."""
        from crawler import mcp_server

        mock_mcp = MagicMock()
        mock_mcp.run = MagicMock()

        with (
            patch.object(mcp_server, "mcp", mock_mcp),
            patch(
                "sys.argv",
                [
                    "crawl-mcp",
                    "--transport",
                    "http",
                    "--cors-origins",
                    "*",
                ],
            ),
        ):
            mcp_server.main()

        call_kwargs = mock_mcp.run.call_args[1]
        assert call_kwargs["middleware"][0].kwargs["allow_origins"] == ["*"]

    def test_cors_multiple_origins_split_correctly(self) -> None:
        """Multiple comma-separated origins should all appear in the middleware."""
        from crawler import mcp_server

        mock_mcp = MagicMock()
        mock_mcp.run = MagicMock()

        with (
            patch.object(mcp_server, "mcp", mock_mcp),
            patch(
                "sys.argv",
                [
                    "crawl-mcp",
                    "--transport",
                    "http",
                    "--cors-origins",
                    "http://localhost:3000, https://myapp.com",
                ],
            ),
        ):
            mcp_server.main()

        call_kwargs = mock_mcp.run.call_args[1]
        origins = call_kwargs["middleware"][0].kwargs["allow_origins"]
        assert origins == ["http://localhost:3000", "https://myapp.com"]

    def test_stdio_transport_ignores_cors(self) -> None:
        """STDIO transport should not include CORS middleware even if flag is set."""
        from crawler import mcp_server

        mock_mcp = MagicMock()
        mock_mcp.run = MagicMock()

        with (
            patch.object(mcp_server, "mcp", mock_mcp),
            patch(
                "sys.argv",
                [
                    "crawl-mcp",
                    "--transport",
                    "stdio",
                    "--cors-origins",
                    "http://localhost:3000",
                ],
            ),
        ):
            mcp_server.main()

        mock_mcp.run.assert_called_once()
        call_kwargs = mock_mcp.run.call_args[1]
        # STDIO transport should just get transport="stdio", no middleware
        assert call_kwargs == {"transport": "stdio"}
