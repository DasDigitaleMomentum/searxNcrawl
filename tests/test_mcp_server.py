"""Tests for crawler.mcp_server module."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

# Patch dotenv before importing mcp_server
with patch("dotenv.load_dotenv"):
    from crawler.mcp_server import (
        OutputFormat,
        _build_auth_config,
        _doc_to_dict,
        _format_multiple_docs_markdown,
        _format_output,
        _format_single_doc_markdown,
        _format_timestamp,
        _strip_markdown_links,
    )

from crawler.auth import AuthConfig
from crawler.document import CrawledDocument, Reference


class TestOutputFormat:
    def test_markdown(self):
        assert OutputFormat("markdown") == OutputFormat.markdown

    def test_json(self):
        assert OutputFormat("json") == OutputFormat.json


class TestFormatTimestamp:
    def test_returns_string(self):
        ts = _format_timestamp()
        assert isinstance(ts, str)
        assert "UTC" in ts


class TestStripMarkdownLinks:
    def test_basic_link(self):
        result = _strip_markdown_links("[Click](https://example.com)")
        assert result == "Click"

    def test_standalone_url(self):
        result = _strip_markdown_links("Visit https://example.com today")
        assert "https" not in result

    def test_no_links(self):
        result = _strip_markdown_links("Hello World")
        assert result == "Hello World"


class TestDocToDict:
    def test_basic(self):
        doc = CrawledDocument(
            request_url="https://a.com",
            final_url="https://b.com",
            status="success",
            markdown="# Hello",
            references=[Reference(index=1, href="https://c.com", label="C")],
            metadata={"key": "value"},
        )
        d = _doc_to_dict(doc)
        assert d["request_url"] == "https://a.com"
        assert d["final_url"] == "https://b.com"
        assert d["status"] == "success"
        assert d["markdown"] == "# Hello"
        assert len(d["references"]) == 1
        assert d["references"][0]["href"] == "https://c.com"
        assert d["metadata"]["key"] == "value"


class TestFormatSingleDocMarkdown:
    def test_success(self):
        doc = CrawledDocument(
            request_url="u",
            final_url="https://example.com",
            status="success",
            markdown="Content here",
        )
        result = _format_single_doc_markdown(doc)
        assert "https://example.com" in result
        assert "Content here" in result

    def test_failed(self):
        doc = CrawledDocument(
            request_url="u",
            final_url="https://example.com",
            status="failed",
            markdown="",
            error_message="Timeout",
        )
        result = _format_single_doc_markdown(doc)
        assert "Error" in result
        assert "Timeout" in result


class TestFormatMultipleDocsMarkdown:
    def test_single_doc(self):
        docs = [
            CrawledDocument(
                request_url="u",
                final_url="https://a.com",
                status="success",
                markdown="A",
            )
        ]
        result = _format_multiple_docs_markdown(docs)
        assert "https://a.com" in result

    def test_multiple_docs(self):
        docs = [
            CrawledDocument(
                request_url="u",
                final_url="https://a.com",
                status="success",
                markdown="A",
            ),
            CrawledDocument(
                request_url="u",
                final_url="https://b.com",
                status="success",
                markdown="B",
            ),
        ]
        result = _format_multiple_docs_markdown(docs)
        assert "---" in result


class TestFormatOutput:
    def test_markdown_format(self):
        docs = [
            CrawledDocument(
                request_url="u",
                final_url="https://a.com",
                status="success",
                markdown="Content",
            )
        ]
        result = _format_output(docs, OutputFormat.markdown)
        assert "Content" in result

    def test_json_format(self):
        docs = [
            CrawledDocument(
                request_url="u",
                final_url="https://a.com",
                status="success",
                markdown="Content",
            )
        ]
        result = _format_output(docs, OutputFormat.json)
        data = json.loads(result)
        assert "documents" in data
        assert data["summary"]["total"] == 1

    def test_json_with_stats(self):
        docs = [
            CrawledDocument(
                request_url="u",
                final_url="https://a.com",
                status="success",
                markdown="C",
            )
        ]
        result = _format_output(
            docs, OutputFormat.json, stats={"pages": 1}
        )
        data = json.loads(result)
        assert data["stats"]["pages"] == 1

    def test_remove_links_markdown(self):
        docs = [
            CrawledDocument(
                request_url="u",
                final_url="https://a.com",
                status="success",
                markdown="[Click](https://foo.com)",
            )
        ]
        result = _format_output(docs, OutputFormat.markdown, remove_links=True)
        assert "https://foo.com" not in result

    def test_remove_links_json(self):
        docs = [
            CrawledDocument(
                request_url="u",
                final_url="https://a.com",
                status="success",
                markdown="[Click](https://foo.com) content",
            )
        ]
        result = _format_output(docs, OutputFormat.json, remove_links=True)
        data = json.loads(result)
        assert "https://foo.com" not in data["documents"][0]["markdown"]


class TestBuildAuthConfig:
    def test_no_args_no_env(self):
        with patch("crawler.mcp_server.load_auth_from_env", return_value=None):
            result = _build_auth_config()
            assert result is None

    def test_with_cookies(self):
        cookies = [{"name": "s", "value": "v", "domain": ".e.com"}]
        result = _build_auth_config(cookies=cookies)
        assert result is not None
        assert result.cookies == cookies

    def test_with_headers(self):
        result = _build_auth_config(headers={"Authorization": "Bearer xyz"})
        assert result is not None
        assert result.headers["Authorization"] == "Bearer xyz"

    def test_with_storage_state(self):
        result = _build_auth_config(storage_state="/path/to/state.json")
        assert result is not None
        assert result.storage_state == "/path/to/state.json"

    def test_fallback_to_env(self):
        env_auth = AuthConfig(storage_state="/env/state.json")
        with patch(
            "crawler.mcp_server.load_auth_from_env", return_value=env_auth
        ):
            result = _build_auth_config()
            assert result is not None
            assert result.storage_state == "/env/state.json"

    def test_with_auth_profile(self):
        result = _build_auth_config(auth_profile="/path/to/profile")
        assert result is not None
        assert result.user_data_dir == "/path/to/profile"

    def test_auth_profile_with_cookies(self):
        cookies = [{"name": "s", "value": "v", "domain": ".e.com"}]
        result = _build_auth_config(cookies=cookies, auth_profile="/profile")
        assert result is not None
        assert result.cookies == cookies
        assert result.user_data_dir == "/profile"


class TestCrawlTool:
    @pytest.mark.asyncio
    async def test_crawl_single_url(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl

        mock_doc = CrawledDocument(
            request_url="https://a.com",
            final_url="https://a.com",
            status="success",
            markdown="Content",
        )
        with patch(
            "crawler.crawl_page_async",
            new_callable=AsyncMock,
            return_value=mock_doc,
        ):
            result = await crawl(urls=["https://a.com"])
            assert "Content" in result

    @pytest.mark.asyncio
    async def test_crawl_multiple_urls(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl

        mock_doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="C"
        )
        with patch(
            "crawler.crawl_pages_async",
            new_callable=AsyncMock,
            return_value=[mock_doc, mock_doc],
        ):
            result = await crawl(urls=["https://a.com", "https://b.com"])
            assert "C" in result

    @pytest.mark.asyncio
    async def test_crawl_failure(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl

        with patch(
            "crawler.crawl_page_async",
            new_callable=AsyncMock,
            side_effect=Exception("failed"),
        ):
            result = await crawl(urls=["https://fail.com"])
            assert "failed" in result

    @pytest.mark.asyncio
    async def test_crawl_invalid_format(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl

        mock_doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="C"
        )
        with patch(
            "crawler.crawl_page_async",
            new_callable=AsyncMock,
            return_value=mock_doc,
        ):
            # Invalid format should default to markdown
            result = await crawl(
                urls=["https://a.com"], output_format="invalid"
            )
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_crawl_with_auth(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl

        mock_doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="C"
        )
        with patch(
            "crawler.crawl_page_async",
            new_callable=AsyncMock,
            return_value=mock_doc,
        ):
            result = await crawl(
                urls=["https://a.com"],
                storage_state="/path/to/state.json",
            )
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_crawl_with_auth_profile(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl

        mock_doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="C"
        )
        with patch(
            "crawler.crawl_page_async",
            new_callable=AsyncMock,
            return_value=mock_doc,
        ) as mock_crawl:
            result = await crawl(
                urls=["https://a.com"],
                auth_profile="/path/to/profile",
            )
            assert isinstance(result, str)
            # Verify auth was passed with user_data_dir
            call_kwargs = mock_crawl.call_args[1]
            assert call_kwargs["auth"] is not None
            assert call_kwargs["auth"].user_data_dir == "/path/to/profile"

    @pytest.mark.asyncio
    async def test_crawl_with_delay_and_wait_until(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl

        mock_doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="C"
        )
        with patch(
            "crawler.crawl_page_async",
            new_callable=AsyncMock,
            return_value=mock_doc,
        ) as mock_crawl:
            result = await crawl(
                urls=["https://a.com"],
                delay=3.0,
                wait_until="networkidle",
            )
            assert isinstance(result, str)
            # Verify run config was passed with SPA settings
            call_kwargs = mock_crawl.call_args[1]
            run_config = call_kwargs["config"]
            assert run_config is not None
            assert run_config.delay_before_return_html == 3.0
            assert run_config.wait_until == "networkidle"
            assert run_config.js_code is None

    @pytest.mark.asyncio
    async def test_crawl_with_aggressive_spa(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl

        mock_doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="C"
        )
        with patch(
            "crawler.crawl_page_async",
            new_callable=AsyncMock,
            return_value=mock_doc,
        ) as mock_crawl:
            result = await crawl(
                urls=["https://a.com"],
                aggressive_spa=True,
            )
            assert isinstance(result, str)
            run_config = mock_crawl.call_args[1]["config"]
            assert run_config.js_code is not None
            assert run_config.wait_for is not None

    @pytest.mark.asyncio
    async def test_crawl_multiple_with_spa_params(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl

        mock_doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="C"
        )
        with patch(
            "crawler.crawl_pages_async",
            new_callable=AsyncMock,
            return_value=[mock_doc, mock_doc],
        ) as mock_crawl:
            result = await crawl(
                urls=["https://a.com", "https://b.com"],
                delay=2.0,
            )
            assert isinstance(result, str)
            call_kwargs = mock_crawl.call_args[1]
            assert call_kwargs["config"] is not None
            assert call_kwargs["config"].delay_before_return_html == 2.0


class TestCrawlSiteTool:
    @pytest.mark.asyncio
    async def test_crawl_site(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl_site

        from crawler.site import SiteCrawlResult

        mock_result = SiteCrawlResult(
            documents=[
                CrawledDocument(
                    request_url="u",
                    final_url="u",
                    status="success",
                    markdown="Page",
                )
            ],
            stats={
                "total_pages": 1,
                "successful_pages": 1,
                "failed_pages": 0,
            },
        )
        with patch(
            "crawler.crawl_site_async",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await crawl_site(url="https://example.com")
            assert "Page" in result

    @pytest.mark.asyncio
    async def test_crawl_site_json(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl_site

        from crawler.site import SiteCrawlResult

        mock_result = SiteCrawlResult(
            documents=[],
            stats={
                "total_pages": 0,
                "successful_pages": 0,
                "failed_pages": 0,
            },
        )
        with patch(
            "crawler.crawl_site_async",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await crawl_site(
                url="https://example.com", output_format="json"
            )
            data = json.loads(result)
            assert "stats" in data

    @pytest.mark.asyncio
    async def test_crawl_site_with_auth_profile(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl_site

        from crawler.site import SiteCrawlResult

        mock_result = SiteCrawlResult(
            documents=[
                CrawledDocument(
                    request_url="u",
                    final_url="u",
                    status="success",
                    markdown="Page",
                )
            ],
            stats={
                "total_pages": 1,
                "successful_pages": 1,
                "failed_pages": 0,
            },
        )
        with patch(
            "crawler.crawl_site_async",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_crawl:
            result = await crawl_site(
                url="https://example.com",
                auth_profile="/path/to/profile",
            )
            assert "Page" in result
            call_kwargs = mock_crawl.call_args[1]
            assert call_kwargs["auth"] is not None
            assert call_kwargs["auth"].user_data_dir == "/path/to/profile"

    @pytest.mark.asyncio
    async def test_crawl_site_with_spa_params(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl_site

        from crawler.site import SiteCrawlResult

        mock_result = SiteCrawlResult(
            documents=[
                CrawledDocument(
                    request_url="u",
                    final_url="u",
                    status="success",
                    markdown="SPA",
                )
            ],
            stats={
                "total_pages": 1,
                "successful_pages": 1,
                "failed_pages": 0,
            },
        )
        with patch(
            "crawler.crawl_site_async",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_crawl:
            result = await crawl_site(
                url="https://example.com",
                delay=5.0,
                wait_until="networkidle",
            )
            assert "SPA" in result
            call_kwargs = mock_crawl.call_args[1]
            assert call_kwargs["run_config"] is not None
            assert call_kwargs["run_config"].delay_before_return_html == 5.0
            assert call_kwargs["run_config"].wait_until == "networkidle"
            assert call_kwargs["run_config"].magic is True

    @pytest.mark.asyncio
    async def test_crawl_site_with_stream(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import crawl_site

        from crawler.site import SiteCrawlResult

        mock_result = SiteCrawlResult(
            documents=[],
            stats={
                "total_pages": 0,
                "successful_pages": 0,
                "failed_pages": 0,
            },
        )
        with patch(
            "crawler.crawl_site_async",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_crawl:
            await crawl_site(url="https://example.com", site_stream=True)
            assert mock_crawl.call_args[1]["stream"] is True


class TestListAuthProfilesTool:
    @pytest.mark.asyncio
    async def test_no_profiles(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import list_auth_profiles

        with patch(
            "crawler.mcp_server._list_auth_profiles", return_value=[]
        ):
            result = await list_auth_profiles()
            data = json.loads(result)
            assert data["profiles"] == []
            assert "message" in data

    @pytest.mark.asyncio
    async def test_with_profiles(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import list_auth_profiles

        profiles = [
            {"name": "test", "path": "/tmp/test", "modified": 1234567890.0}
        ]
        with patch(
            "crawler.mcp_server._list_auth_profiles", return_value=profiles
        ):
            result = await list_auth_profiles()
            data = json.loads(result)
            assert len(data["profiles"]) == 1
            assert data["profiles"][0]["name"] == "test"

    @pytest.mark.asyncio
    async def test_backward_compat_alias(self):
        with patch("dotenv.load_dotenv"):
            from crawler.mcp_server import list_auth_profiles_tool

        with patch("crawler.mcp_server._list_auth_profiles", return_value=[]):
            result = await list_auth_profiles_tool()
            data = json.loads(result)
            assert "profiles" in data
