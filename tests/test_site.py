"""Tests for crawler.site module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from crawler.site import (
    SiteCrawlResult,
    _iterate_results,
    _normalize_host,
    _registrable_domain,
    crawl_site_async,
)


class TestNormalizeHost:
    def test_basic(self):
        assert _normalize_host("Example.COM") == "example.com"

    def test_with_port(self):
        assert _normalize_host("Example.COM:8080") == "example.com"

    def test_empty(self):
        assert _normalize_host("") == ""

    def test_none(self):
        assert _normalize_host(None) == ""


class TestRegistrableDomain:
    def test_domain(self):
        result = _registrable_domain("www.example.com")
        assert result == "example.com"

    def test_empty(self):
        result = _registrable_domain("")
        assert result is None

    def test_simple_host(self):
        result = _registrable_domain("localhost")
        assert result is not None


class TestSiteCrawlResult:
    def test_defaults(self):
        result = SiteCrawlResult()
        assert result.documents == []
        assert result.errors == []
        assert result.stats == {}


class TestIterateResults:
    @pytest.mark.asyncio
    async def test_list_of_results(self):
        mock_result = MagicMock()
        mock_result.url = "https://example.com"
        results = [item async for item in _iterate_results([mock_result])]
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_single_crawl_result(self):
        from crawl4ai.models import CrawlResult

        mock_result = MagicMock(spec=CrawlResult)
        results = [item async for item in _iterate_results(mock_result)]
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_empty_list(self):
        results = [item async for item in _iterate_results([])]
        assert results == []


class TestCrawlSiteAsync:
    @pytest.mark.asyncio
    async def test_basic_site_crawl(self):
        mock_doc = MagicMock()
        mock_doc.request_url = "https://example.com"
        mock_doc.final_url = "https://example.com"
        mock_doc.status = "success"

        mock_result_item = MagicMock()
        mock_result_item.url = "https://example.com"

        with patch("crawler.site.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_instance.arun = AsyncMock(return_value=[mock_result_item])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance

            with patch(
                "crawler.site.build_document_from_result", return_value=mock_doc
            ):
                result = await crawl_site_async(
                    "https://example.com", max_depth=1, max_pages=5
                )

                assert isinstance(result, SiteCrawlResult)
                assert result.stats["total_pages"] >= 0

    @pytest.mark.asyncio
    async def test_site_crawl_with_auth(self):
        from crawler.auth import AuthConfig

        auth = AuthConfig(headers={"Authorization": "Bearer test"})

        with patch("crawler.site.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_instance.arun = AsyncMock(return_value=[])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance

            with patch("crawler.site.build_browser_config") as mock_build:
                await crawl_site_async(
                    "https://example.com", auth=auth
                )
                mock_build.assert_called_once_with(auth)

    @pytest.mark.asyncio
    async def test_site_crawl_with_subdomains(self):
        with patch("crawler.site.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_instance.arun = AsyncMock(return_value=[])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance

            result = await crawl_site_async(
                "https://docs.example.com",
                include_subdomains=True,
            )
            assert isinstance(result, SiteCrawlResult)

    @pytest.mark.asyncio
    async def test_site_crawl_deduplication(self):
        """Test that duplicate URLs are skipped."""
        mock_doc = MagicMock()
        mock_doc.request_url = "https://example.com"
        mock_doc.final_url = "https://example.com"
        mock_doc.status = "success"

        mock_result_item = MagicMock()
        mock_result_item.url = "https://example.com"

        with patch("crawler.site.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            # Return two identical results
            mock_instance.arun = AsyncMock(
                return_value=[mock_result_item, mock_result_item]
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance

            with patch(
                "crawler.site.build_document_from_result", return_value=mock_doc
            ):
                result = await crawl_site_async(
                    "https://example.com", max_depth=1, max_pages=10
                )
                # Should only have 1 doc due to deduplication
                assert result.stats["total_pages"] == 1

    @pytest.mark.asyncio
    async def test_site_crawl_build_failure(self):
        """Test handling when build_document_from_result raises."""
        mock_result_item = MagicMock()
        mock_result_item.url = "https://example.com"

        with patch("crawler.site.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_instance.arun = AsyncMock(return_value=[mock_result_item])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance

            with patch(
                "crawler.site.build_document_from_result",
                side_effect=Exception("build failed"),
            ):
                result = await crawl_site_async(
                    "https://example.com", max_depth=1, max_pages=5
                )
                assert len(result.errors) == 1
                assert result.errors[0]["stage"] == "build"


class TestCrawlSiteSync:
    def test_sync_wrapper_exists(self):
        from crawler.site import crawl_site

        assert callable(crawl_site)
