"""Tests for crawler.__init__ module (crawl_page, crawl_pages, etc.)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from crawler import (
    __getattr__ as module_getattr,
    get_mcp_server,
)
from crawler.auth import AuthConfig
from crawler.document import CrawledDocument


class TestCrawlPageAsync:
    @pytest.mark.asyncio
    async def test_crawl_page_async_success(self):
        """Test successful page crawl."""
        mock_doc = CrawledDocument(
            request_url="https://example.com",
            final_url="https://example.com",
            status="success",
            markdown="# Hello",
        )

        with patch("crawler.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_result = MagicMock()
            mock_result.__getitem__ = MagicMock(return_value=MagicMock())
            mock_instance.arun = AsyncMock(return_value=mock_result)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance

            with patch("crawler.build_document_from_result", return_value=mock_doc):
                from crawler import crawl_page_async

                doc = await crawl_page_async("https://example.com")
                assert doc.status == "success"

    @pytest.mark.asyncio
    async def test_crawl_page_async_no_results(self):
        """Test ValueError when crawler returns nothing."""
        with patch("crawler.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_result = MagicMock()
            mock_result.__getitem__ = MagicMock(side_effect=IndexError)
            mock_instance.arun = AsyncMock(return_value=mock_result)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance

            from crawler import crawl_page_async

            with pytest.raises(ValueError, match="no results"):
                await crawl_page_async("https://example.com")

    @pytest.mark.asyncio
    async def test_crawl_page_async_type_error(self):
        """Test ValueError when result container is None."""
        with patch("crawler.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_instance.arun = AsyncMock(return_value=None)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance

            from crawler import crawl_page_async

            with pytest.raises(ValueError, match="no results"):
                await crawl_page_async("https://example.com")

    @pytest.mark.asyncio
    async def test_crawl_page_async_with_auth(self):
        """Test that auth config is passed through."""
        mock_doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="m"
        )
        auth = AuthConfig(cookies=[{"name": "s", "value": "v", "domain": ".e.com"}])

        with patch("crawler.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_result = MagicMock()
            mock_result.__getitem__ = MagicMock(return_value=MagicMock())
            mock_instance.arun = AsyncMock(return_value=mock_result)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance

            with patch("crawler.build_document_from_result", return_value=mock_doc):
                with patch("crawler.build_browser_config") as mock_build:
                    from crawler import crawl_page_async

                    await crawl_page_async("https://example.com", auth=auth)
                    mock_build.assert_called_once_with(auth)


class TestCrawlPagesAsync:
    @pytest.mark.asyncio
    async def test_multiple_urls(self):
        """Test crawling multiple URLs."""
        mock_doc_a = CrawledDocument(
            request_url="https://a.com",
            final_url="https://a.com",
            status="success",
            markdown="A",
        )
        mock_doc_b = CrawledDocument(
            request_url="https://b.com",
            final_url="https://b.com",
            status="success",
            markdown="B",
        )

        mock_result_a = MagicMock()
        mock_result_a.url = "https://a.com"
        mock_result_b = MagicMock()
        mock_result_b.url = "https://b.com"

        with patch("crawler.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_instance.arun_many = AsyncMock(return_value=[mock_result_a, mock_result_b])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance

            with patch(
                "crawler.build_document_from_result",
                side_effect=[mock_doc_a, mock_doc_b],
            ):
                from crawler import crawl_pages_async

                docs = await crawl_pages_async(["https://a.com", "https://b.com"])
                assert len(docs) == 2
                assert docs[0].request_url == "https://a.com"
                assert docs[1].request_url == "https://b.com"

    @pytest.mark.asyncio
    async def test_failed_crawl_returns_failed_doc(self):
        """Test that exceptions are caught and returned as failed docs."""
        with patch("crawler.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_instance.arun_many = AsyncMock(side_effect=Exception("boom"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance

            from crawler import crawl_pages_async

            docs = await crawl_pages_async(["https://fail.com"])
            assert len(docs) == 1
            assert docs[0].status == "failed"
            assert "boom" in docs[0].error_message


class TestCrawlPageSync:
    def test_sync_wrapper(self):
        """Test synchronous wrapper calls asyncio.run."""
        mock_doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="m"
        )
        with patch("crawler.crawl_page_async", new_callable=AsyncMock) as mock:
            mock.return_value = mock_doc
            with patch("crawler.asyncio.run", return_value=mock_doc):
                from crawler import crawl_page

                assert callable(crawl_page)


class TestCrawlPagesSync:
    def test_sync_wrapper(self):
        """Test synchronous wrapper exists."""
        from crawler import crawl_pages

        assert callable(crawl_pages)


class TestLazyImports:
    def test_getattr_mcp(self):
        """Test lazy mcp import."""
        with patch("crawler.mcp_server.mcp", create=True):
            result = module_getattr("mcp")
            assert result is not None

    def test_getattr_unknown_raises(self):
        with pytest.raises(AttributeError):
            module_getattr("nonexistent_attribute")

    def test_get_mcp_server(self):
        with patch("crawler.mcp_server.mcp", create=True):
            result = get_mcp_server()
            assert result is not None
