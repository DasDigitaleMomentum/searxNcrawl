"""Tests for crawler.cli module."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# We need to isolate CLI imports from _load_config side effects
with patch("dotenv.load_dotenv"):
    from crawler.cli import (
        _add_auth_args,
        _build_cli_auth,
        _doc_to_dict,
        _format_search_markdown,
        _parse_capture_auth_args,
        _parse_crawl_args,
        _strip_markdown_links,
        _url_to_filename,
        _write_output,
    )

from crawler.auth import AuthConfig
from crawler.document import CrawledDocument, Reference


class TestStripMarkdownLinks:
    def test_link_removal(self):
        assert _strip_markdown_links("[text](https://url.com)") == "text"

    def test_url_removal(self):
        result = _strip_markdown_links("Visit https://example.com here")
        assert "https" not in result


class TestFormatSearchMarkdown:
    def test_basic(self):
        data = {
            "query": "test",
            "results": [
                {"title": "Result 1", "url": "https://a.com", "content": "Content"},
            ],
            "suggestions": ["suggest1", "suggest2"],
        }
        result = _format_search_markdown(data)
        assert "# Search: test" in result
        assert "Result 1" in result
        assert "suggest1" in result

    def test_empty_results(self):
        data = {"query": "test", "results": []}
        result = _format_search_markdown(data)
        assert "0 results" in result

    def test_no_suggestions(self):
        data = {"query": "test", "results": [], "suggestions": []}
        result = _format_search_markdown(data)
        assert "Related searches" not in result

    def test_no_content(self):
        data = {
            "query": "test",
            "results": [{"title": "T", "url": "u"}],
        }
        result = _format_search_markdown(data)
        assert "T" in result


class TestDocToDict:
    def test_conversion(self):
        doc = CrawledDocument(
            request_url="https://a.com",
            final_url="https://b.com",
            status="success",
            markdown="# Hello",
            references=[Reference(index=1, href="h", label="l")],
        )
        d = _doc_to_dict(doc)
        assert d["request_url"] == "https://a.com"
        assert d["references"][0]["index"] == 1


class TestUrlToFilename:
    def test_basic(self):
        name = _url_to_filename("https://example.com/page/1")
        assert "example" in name
        assert "page" in name

    def test_index_fallback(self):
        name = _url_to_filename("https://example.com/")
        assert "index" in name

    def test_long_url_truncated(self):
        url = "https://example.com/" + "a" * 200
        name = _url_to_filename(url)
        assert len(name) <= 100


class TestWriteOutput:
    def test_single_doc_stdout(self, capsys):
        doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="Hello"
        )
        _write_output([doc], None, False)
        captured = capsys.readouterr()
        assert "Hello" in captured.out

    def test_single_doc_stdout_json(self, capsys):
        doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="Hello"
        )
        _write_output([doc], None, True)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["markdown"] == "Hello"

    def test_single_doc_to_file(self):
        doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="Content"
        )
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            path = f.name
        try:
            _write_output([doc], path, False)
            assert Path(path).read_text() == "Content"
        finally:
            os.unlink(path)

    def test_single_doc_to_file_json(self):
        doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="Content"
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            _write_output([doc], path, True)
            data = json.loads(Path(path).read_text())
            assert data["markdown"] == "Content"
        finally:
            os.unlink(path)

    def test_multiple_docs_to_dir(self):
        docs = [
            CrawledDocument(
                request_url="u",
                final_url="https://a.com/page1",
                status="success",
                markdown="A",
            ),
            CrawledDocument(
                request_url="u",
                final_url="https://b.com/page2",
                status="success",
                markdown="B",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_output(docs, tmpdir, False)
            files = list(Path(tmpdir).iterdir())
            assert len(files) == 2

    def test_multiple_docs_json(self):
        docs = [
            CrawledDocument(
                request_url="u",
                final_url="https://a.com",
                status="success",
                markdown="A",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_output(docs, tmpdir + "/", True)
            json_file = Path(tmpdir) / "crawl_results.json"
            assert json_file.exists()

    def test_remove_links(self, capsys):
        doc = CrawledDocument(
            request_url="u",
            final_url="u",
            status="success",
            markdown="[Click](https://foo.com)",
        )
        _write_output([doc], None, False, remove_links=True)
        captured = capsys.readouterr()
        assert "https://foo.com" not in captured.out

    def test_remove_links_json(self, capsys):
        doc = CrawledDocument(
            request_url="u",
            final_url="u",
            status="success",
            markdown="[Link](https://example.com) text",
        )
        _write_output([doc], None, True, remove_links=True)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "https://example.com" not in data["markdown"]


class TestBuildCliAuth:
    def test_no_auth(self):
        args = argparse.Namespace()
        with patch("crawler.cli.load_auth_from_env", return_value=None):
            assert _build_cli_auth(args) is None

    def test_with_cookies_json(self):
        args = argparse.Namespace(
            cookies='[{"name":"s","value":"v","domain":".e.com"}]',
            header=None,
            storage_state=None,
            auth_profile=None,
        )
        result = _build_cli_auth(args)
        assert result is not None
        assert len(result.cookies) == 1

    def test_with_cookies_single_object(self):
        args = argparse.Namespace(
            cookies='{"name":"s","value":"v","domain":".e.com"}',
            header=None,
            storage_state=None,
            auth_profile=None,
        )
        result = _build_cli_auth(args)
        assert result is not None
        assert len(result.cookies) == 1

    def test_with_cookies_file(self):
        cookies = [{"name": "s", "value": "v", "domain": ".e.com"}]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(cookies, f)
            path = f.name
        try:
            args = argparse.Namespace(
                cookies=path,
                header=None,
                storage_state=None,
                auth_profile=None,
            )
            result = _build_cli_auth(args)
            assert result is not None
            assert result.cookies == cookies
        finally:
            os.unlink(path)

    def test_with_invalid_cookies(self):
        args = argparse.Namespace(
            cookies="not_json_and_not_a_file",
            header=None,
            storage_state=None,
            auth_profile=None,
        )
        result = _build_cli_auth(args)
        # Falls back to env
        assert result is None or result.cookies is None

    def test_with_headers(self):
        args = argparse.Namespace(
            cookies=None,
            header=["Authorization: Bearer xyz", "X-Custom: value"],
            storage_state=None,
            auth_profile=None,
        )
        result = _build_cli_auth(args)
        assert result is not None
        assert result.headers["Authorization"] == "Bearer xyz"
        assert result.headers["X-Custom"] == "value"

    def test_with_invalid_header(self):
        args = argparse.Namespace(
            cookies=None,
            header=["InvalidFormat"],
            storage_state=None,
            auth_profile=None,
        )
        # Should log warning and not crash
        result = _build_cli_auth(args)
        # No valid auth args, falls back to env
        assert result is None or result.headers == {}

    def test_with_storage_state(self):
        args = argparse.Namespace(
            cookies=None,
            header=None,
            storage_state="/path/to/state.json",
            auth_profile=None,
        )
        result = _build_cli_auth(args)
        assert result is not None
        assert result.storage_state == "/path/to/state.json"

    def test_with_auth_profile(self):
        args = argparse.Namespace(
            cookies=None,
            header=None,
            storage_state=None,
            auth_profile="/path/to/profile",
        )
        result = _build_cli_auth(args)
        assert result is not None
        assert result.user_data_dir == "/path/to/profile"

    def test_env_fallback(self):
        args = argparse.Namespace()
        env_auth = AuthConfig(storage_state="/env/path.json")
        with patch("crawler.cli.load_auth_from_env", return_value=env_auth):
            result = _build_cli_auth(args)
            assert result is not None
            assert result.storage_state == "/env/path.json"


class TestAddAuthArgs:
    def test_adds_auth_group(self):
        parser = argparse.ArgumentParser()
        _add_auth_args(parser)
        # Should not raise when parsing auth args
        args = parser.parse_args(
            ["--storage-state", "state.json", "--auth-profile", "/tmp/p"]
        )
        assert args.storage_state == "state.json"
        assert args.auth_profile == "/tmp/p"

    def test_header_append(self):
        parser = argparse.ArgumentParser()
        _add_auth_args(parser)
        args = parser.parse_args(
            ["--header", "Auth: test", "--header", "X: y"]
        )
        assert len(args.header) == 2


class TestParseCrawlArgs:
    def test_basic(self):
        args = _parse_crawl_args(["https://example.com"])
        assert args.urls == ["https://example.com"]
        assert args.site is False
        assert args.verbose is False

    def test_site_mode(self):
        args = _parse_crawl_args(
            ["https://example.com", "--site", "--max-depth", "3"]
        )
        assert args.site is True
        assert args.max_depth == 3

    def test_with_auth_args(self):
        args = _parse_crawl_args(
            ["https://example.com", "--storage-state", "state.json"]
        )
        assert args.storage_state == "state.json"


class TestParseCaptureAuthArgs:
    def test_basic(self):
        args = _parse_capture_auth_args(
            ["--url", "https://login.example.com"]
        )
        assert args.url == "https://login.example.com"
        assert args.output == "auth_state.json"
        assert args.timeout == 300
        assert args.capture_auth is True

    def test_with_all_options(self):
        args = _parse_capture_auth_args(
            [
                "--url", "https://login.example.com",
                "--output", "my_auth.json",
                "--wait-for-url", "/dashboard",
                "--timeout", "600",
                "-v",
            ]
        )
        assert args.output == "my_auth.json"
        assert args.wait_for_url == "/dashboard"
        assert args.timeout == 600
        assert args.verbose is True


class TestMainEntryPoint:
    def test_main_capture_auth(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import main

        with patch("crawler.cli._run_capture_auth_async", new_callable=AsyncMock) as mock:
            mock.return_value = 0
            result = main(["capture-auth", "--url", "https://login.example.com"])
            assert result == 0

    def test_main_crawl(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import main

        with patch("crawler.cli._run_crawl_async", new_callable=AsyncMock) as mock:
            mock.return_value = 0
            result = main(["https://example.com"])
            assert result == 0

    def test_main_capture_auth_error(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import main

        with patch(
            "crawler.cli._run_capture_auth_async",
            new_callable=AsyncMock,
            side_effect=Exception("error"),
        ):
            result = main(["capture-auth", "--url", "https://login.example.com"])
            assert result == 1

    def test_main_crawl_error(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import main

        with patch(
            "crawler.cli._run_crawl_async",
            new_callable=AsyncMock,
            side_effect=Exception("error"),
        ):
            result = main(["https://example.com"])
            assert result == 1


class TestSearchMain:
    def test_search_main_exists(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import search_main

        assert callable(search_main)


class TestRunCrawlAsync:
    @pytest.mark.asyncio
    async def test_single_url(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_crawl_async

        doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="C"
        )
        args = argparse.Namespace(
            urls=["https://example.com"],
            site=False,
            json_output=False,
            output=None,
            remove_links=False,
            verbose=False,
            concurrency=3,
        )
        # Remove auth attrs so _build_cli_auth falls back
        with patch("crawler.cli.load_auth_from_env", return_value=None):
            with patch(
                "crawler.crawl_page_async",
                new_callable=AsyncMock,
                return_value=doc,
            ):
                result = await _run_crawl_async(args)
                assert result == 0

    @pytest.mark.asyncio
    async def test_site_crawl(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_crawl_async

        from crawler.site import SiteCrawlResult

        doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="C"
        )
        mock_result = SiteCrawlResult(
            documents=[doc],
            stats={"total_pages": 1, "successful_pages": 1, "failed_pages": 0},
        )
        args = argparse.Namespace(
            urls=["https://example.com"],
            site=True,
            max_depth=2,
            max_pages=25,
            include_subdomains=False,
            json_output=False,
            output=None,
            remove_links=False,
            verbose=False,
        )
        with patch("crawler.cli.load_auth_from_env", return_value=None):
            with patch(
                "crawler.crawl_site_async",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                result = await _run_crawl_async(args)
                assert result == 0

    @pytest.mark.asyncio
    async def test_site_crawl_multiple_urls_error(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_crawl_async

        args = argparse.Namespace(
            urls=["https://a.com", "https://b.com"],
            site=True,
            json_output=False,
            output=None,
            remove_links=False,
            verbose=False,
        )
        with patch("crawler.cli.load_auth_from_env", return_value=None):
            result = await _run_crawl_async(args)
            assert result == 1

    @pytest.mark.asyncio
    async def test_multiple_urls(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_crawl_async

        doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="C"
        )
        args = argparse.Namespace(
            urls=["https://a.com", "https://b.com"],
            site=False,
            json_output=False,
            output=None,
            remove_links=False,
            verbose=False,
            concurrency=3,
        )
        with patch("crawler.cli.load_auth_from_env", return_value=None):
            with patch(
                "crawler.crawl_pages_async",
                new_callable=AsyncMock,
                return_value=[doc, doc],
            ):
                result = await _run_crawl_async(args)
                assert result == 0

    @pytest.mark.asyncio
    async def test_all_failed(self):
        with patch("dotenv.load_dotenv"):
            from crawler.cli import _run_crawl_async

        doc = CrawledDocument(
            request_url="u",
            final_url="u",
            status="failed",
            markdown="",
            error_message="fail",
        )
        args = argparse.Namespace(
            urls=["https://fail.com"],
            site=False,
            json_output=False,
            output=None,
            remove_links=False,
            verbose=False,
            concurrency=3,
        )
        with patch("crawler.cli.load_auth_from_env", return_value=None):
            with patch(
                "crawler.crawl_page_async",
                new_callable=AsyncMock,
                return_value=doc,
            ):
                result = await _run_crawl_async(args)
                assert result == 1
