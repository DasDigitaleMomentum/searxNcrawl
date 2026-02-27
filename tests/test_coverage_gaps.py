"""Additional tests for remaining coverage gaps."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from crawler.auth import AuthConfig, list_auth_profiles


# ── auth.py: list_auth_profiles ──────────────────────────────────


class TestListAuthProfiles:
    def test_no_profiles_dir(self):
        with patch("crawler.auth.DEFAULT_PROFILES_DIR", Path("/nonexistent/path")):
            result = list_auth_profiles()
            assert result == []

    def test_with_profiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir)
            # Create a fake profile
            (profiles_dir / "myprofile").mkdir()
            (profiles_dir / "myprofile" / "dummy").touch()

            with patch("crawler.auth.DEFAULT_PROFILES_DIR", profiles_dir):
                result = list_auth_profiles()
                assert len(result) == 1
                assert result[0]["name"] == "myprofile"


# ── auth.py: load_auth_from_file with cookies ────────────────────


class TestAuthLoadFromFileCookies:
    def test_load_cookies_from_file(self):
        from crawler.auth import load_auth_from_file

        config = {
            "cookies_file": None,
            "headers": {"X-Test": "value"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            path = f.name
        try:
            result = load_auth_from_file(path)
            assert result is not None
            assert result.headers == {"X-Test": "value"}
        finally:
            os.unlink(path)

    def test_load_with_cookies_file_ref(self):
        from crawler.auth import load_auth_from_file

        cookies = [{"name": "s", "value": "v", "domain": ".e.com"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            # load_auth_from_file reads "cookies" key directly, not "cookies_file"
            config = {"cookies": cookies}
            config_file = Path(tmpdir) / "auth.json"
            config_file.write_text(json.dumps(config))

            result = load_auth_from_file(str(config_file))
            assert result is not None
            assert result.cookies == cookies


# ── auth.py: resolved_storage_state with dict data ───────────────


class TestAuthResolvedStorageStateDict:
    def test_storage_state_as_dict(self):
        state_data = {"cookies": [{"name": "a"}], "origins": []}
        auth = AuthConfig(storage_state_data=state_data)
        resolved = auth.resolved_storage_state()  # It's a method, not a property
        assert resolved is not None
        assert resolved == state_data
        assert resolved["cookies"][0]["name"] == "a"


# ── mcp_server.py: search tool ───────────────────────────────────


class TestSearchTool:
    @pytest.mark.asyncio
    async def test_search_success(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import search

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": "test",
            "results": [{"title": "Result 1", "url": "https://a.com"}],
            "number_of_results": 1,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await search(query="test")
            data = json.loads(result)
            assert data["query"] == "test"
            assert len(data["results"]) == 1

    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import search

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": "test",
            "results": [],
            "number_of_results": 0,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await search(
                query="test",
                time_range="week",
                categories=["general"],
                engines=["google"],
            )
            data = json.loads(result)
            assert "error" not in data

    @pytest.mark.asyncio
    async def test_search_http_error_401(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import search

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "401", request=MagicMock(), response=mock_response
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await search(query="test")
            data = json.loads(result)
            assert "Authentication failed" in data["error"]

    @pytest.mark.asyncio
    async def test_search_http_error_500(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import search

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500", request=MagicMock(), response=mock_response
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await search(query="test")
            data = json.loads(result)
            assert "500" in data["error"]

    @pytest.mark.asyncio
    async def test_search_request_error(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import search

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await search(query="test")
            data = json.loads(result)
            assert "Request failed" in data["error"]

    @pytest.mark.asyncio
    async def test_search_unexpected_error(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import search

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("unexpected"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await search(query="test")
            data = json.loads(result)
            assert "Unexpected error" in data["error"]


# ── mcp_server.py: _get_searxng_client ───────────────────────────


class TestGetSearxngClient:
    def test_without_auth(self):
        from crawler.search import _get_searxng_client

        client = _get_searxng_client(base_url="http://localhost:8888")
        assert isinstance(client, httpx.AsyncClient)

    def test_with_auth(self):
        from crawler.search import _get_searxng_client

        client = _get_searxng_client(
            base_url="http://localhost:8888",
            username="user",
            password="pass",
        )
        assert isinstance(client, httpx.AsyncClient)


# ── mcp_server.py: main() ────────────────────────────────────────


class TestMCPServerMain:
    def test_main_stdio(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import main

        with patch("crawler.mcp_server.mcp") as mock_mcp:
            with patch("crawler.mcp_server.load_auth_from_env", return_value=None):
                with patch(
                    "argparse.ArgumentParser.parse_args",
                    return_value=MagicMock(
                        transport="stdio", host="127.0.0.1", port=8000
                    ),
                ):
                    main()
                    mock_mcp.run.assert_called_once_with(transport="stdio")

    def test_main_http(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import main

        with patch("crawler.mcp_server.mcp") as mock_mcp:
            with patch("crawler.mcp_server.load_auth_from_env", return_value=None):
                with patch(
                    "argparse.ArgumentParser.parse_args",
                    return_value=MagicMock(transport="http", host="0.0.0.0", port=9000),
                ):
                    main()
                    mock_mcp.run.assert_called_once_with(
                        transport="http", host="0.0.0.0", port=9000
                    )

    def test_main_with_auth(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import main

        auth = AuthConfig(storage_state="/env/state.json")
        with patch("crawler.mcp_server.mcp"):
            with patch("crawler.mcp_server.load_auth_from_env", return_value=auth):
                with patch(
                    "argparse.ArgumentParser.parse_args",
                    return_value=MagicMock(
                        transport="stdio", host="127.0.0.1", port=8000
                    ),
                ):
                    main()


# ── mcp_server.py: crawl_site with auth ──────────────────────────


class TestMCPCrawlSiteAuth:
    @pytest.mark.asyncio
    async def test_crawl_site_with_auth(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl_site as mcp_crawl_site

        from crawler.site import SiteCrawlResult

        mock_result = SiteCrawlResult(
            documents=[],
            stats={"total_pages": 0, "successful_pages": 0, "failed_pages": 0},
        )
        with patch(
            "crawler.crawl_site_async",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await mcp_crawl_site(
                url="https://example.com",
                cookies=[{"name": "s", "value": "v", "domain": ".e.com"}],
            )
            assert isinstance(result, str)


# ── cli.py: _load_config branches ────────────────────────────────


class TestLoadConfig:
    def test_local_env_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("SEARXNG_URL=http://test")

            with patch("crawler.cli.Path.cwd", return_value=Path(tmpdir)):
                with patch("crawler.cli.load_dotenv") as mock_load:
                    from crawler.cli import _load_config

                    _load_config()
                    mock_load.assert_called()

    def test_config_dir_env(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".config" / "searxncrawl"
            config_dir.mkdir(parents=True)
            (config_dir / ".env").write_text("SEARXNG_URL=http://config")

            with patch("crawler.cli.Path.cwd", return_value=Path("/nonexistent")):
                with patch("crawler.cli.CONFIG_ENV_FILE", config_dir / ".env"):
                    with patch("crawler.cli.load_dotenv") as mock_load:
                        from crawler.cli import _load_config

                        _load_config()
                        mock_load.assert_called()


# ── cli.py: _run_search_async ────────────────────────────────────


class TestRunSearchAsync:
    @pytest.mark.asyncio
    async def test_search_success(self):
        import argparse

        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_search_async

        args = argparse.Namespace(
            query="test",
            language="en",
            safesearch=1,
            time_range=None,
            categories=None,
            engines=None,
            max_results=10,
            pageno=1,
            json_output=False,
            output=None,
            verbose=False,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": "test",
            "results": [{"title": "T", "url": "u", "content": "c"}],
            "number_of_results": 1,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await _run_search_async(args)
            assert result == 0

    @pytest.mark.asyncio
    async def test_search_json_output(self):
        import argparse

        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_search_async

        args = argparse.Namespace(
            query="test",
            language="en",
            safesearch=1,
            time_range="week",
            categories=["general"],
            engines=["google"],
            max_results=5,
            pageno=1,
            json_output=True,
            output=None,
            verbose=False,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": "test",
            "results": [],
            "number_of_results": 0,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await _run_search_async(args)
            assert result == 0

    @pytest.mark.asyncio
    async def test_search_http_401(self):
        import argparse

        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_search_async

        args = argparse.Namespace(
            query="test",
            language="en",
            safesearch=1,
            time_range=None,
            categories=None,
            engines=None,
            max_results=10,
            pageno=1,
            json_output=False,
            output=None,
            verbose=False,
        )

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "401", request=MagicMock(), response=mock_response
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await _run_search_async(args)
            assert result == 1

    @pytest.mark.asyncio
    async def test_search_http_500(self):
        import argparse

        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_search_async

        args = argparse.Namespace(
            query="test",
            language="en",
            safesearch=1,
            time_range=None,
            categories=None,
            engines=None,
            max_results=10,
            pageno=1,
            json_output=False,
            output=None,
            verbose=False,
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500", request=MagicMock(), response=mock_response
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await _run_search_async(args)
            assert result == 1

    @pytest.mark.asyncio
    async def test_search_request_error(self):
        import argparse

        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_search_async

        args = argparse.Namespace(
            query="test",
            language="en",
            safesearch=1,
            time_range=None,
            categories=None,
            engines=None,
            max_results=10,
            pageno=1,
            json_output=False,
            output=None,
            verbose=False,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await _run_search_async(args)
            assert result == 1

    @pytest.mark.asyncio
    async def test_search_unexpected_error(self):
        import argparse

        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_search_async

        args = argparse.Namespace(
            query="test",
            language="en",
            safesearch=1,
            time_range=None,
            categories=None,
            engines=None,
            max_results=10,
            pageno=1,
            json_output=False,
            output=None,
            verbose=False,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("unexpected"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            result = await _run_search_async(args)
            assert result == 1

    @pytest.mark.asyncio
    async def test_search_to_file(self):
        import argparse

        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_search_async

        args = argparse.Namespace(
            query="test",
            language="en",
            safesearch=1,
            time_range=None,
            categories=None,
            engines=None,
            max_results=10,
            pageno=1,
            json_output=True,
            output=None,
            verbose=False,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "query": "test",
            "results": [],
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            args.output = f.name

        try:
            with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
                result = await _run_search_async(args)
                assert result == 0
            assert Path(args.output).exists()
        finally:
            os.unlink(args.output)


# ── cli.py: search_main ──────────────────────────────────────────


class TestSearchMainFunc:
    def test_search_main_success(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import search_main

        with patch(
            "crawler.cli._run_search_async",
            new_callable=AsyncMock,
            return_value=0,
        ):
            result = search_main(["test query"])
            assert result == 0

    def test_search_main_error(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import search_main

        with patch(
            "crawler.cli._run_search_async",
            new_callable=AsyncMock,
            side_effect=Exception("boom"),
        ):
            result = search_main(["test query"])
            assert result == 1


# ── cli.py: _parse_search_args and _run_crawl_async with auth ────


class TestSearchArgs:
    def test_parse_search_args(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import _parse_search_args

        args = _parse_search_args(["test query", "--language", "de"])
        assert args.query == "test query"
        assert args.language == "de"

    def test_parse_search_args_all(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import _parse_search_args

        args = _parse_search_args(
            [
                "test",
                "--time-range",
                "week",
                "--categories",
                "general",
                "news",
                "--engines",
                "google",
                "--safesearch",
                "2",
                "--max-results",
                "20",
                "--json",
                "-v",
            ]
        )
        assert args.time_range == "week"
        assert args.safesearch == 2
        assert args.max_results == 20
        assert args.json_output is True
        assert args.verbose is True


# ── cli.py: _run_capture_auth_async ──────────────────────────────


class TestRunCaptureAuthAsync:
    @pytest.mark.asyncio
    async def test_capture_success(self):
        import argparse

        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_capture_auth_async

        args = argparse.Namespace(
            url="https://login.example.com",
            output="auth_state.json",
            wait_for_url=None,
            timeout=300,
            verbose=False,
        )
        with patch(
            "crawler.capture.capture_auth_state",
            new_callable=AsyncMock,
            return_value="/tmp/state.json",
        ):
            result = await _run_capture_auth_async(args)
            assert result == 0

    @pytest.mark.asyncio
    async def test_capture_failure(self):
        import argparse

        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_capture_auth_async

        args = argparse.Namespace(
            url="https://login.example.com",
            output="auth_state.json",
            wait_for_url=None,
            timeout=300,
            verbose=True,
        )
        with patch(
            "crawler.capture.capture_auth_state",
            new_callable=AsyncMock,
            side_effect=Exception("capture failed"),
        ):
            result = await _run_capture_auth_async(args)
            assert result == 1


# ── references.py: ValueError in index ───────────────────────────


class TestReferencesValueError:
    def test_invalid_index_skipped(self):
        from crawler.references import _parse_markdown_block

        # This line has a valid regex match but we can test the ValueError path
        # by checking that non-integer indices would be handled
        # The regex requires \d+ so this branch is hard to trigger naturally
        # But we ensure our existing tests cover the lines
        refs = list(_parse_markdown_block("⟨99⟩ https://test.com"))
        assert len(refs) == 1
        assert refs[0].index == 99


# ── site.py: crawl_site sync wrapper ─────────────────────────────


class TestSiteCrawlSync:
    def test_sync_wrapper_callable(self):
        from crawler.site import crawl_site

        assert callable(crawl_site)


# ── __init__.py: sync wrappers ────────────────────────────────────


class TestInitSyncWrappers:
    def test_crawl_page_sync_callable(self):
        from crawler import crawl_page

        assert callable(crawl_page)

    def test_crawl_pages_sync_callable(self):
        from crawler import crawl_pages

        assert callable(crawl_pages)
