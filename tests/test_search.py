"""Tests for crawler.search module (shared search implementation)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from crawler.search import (
    SearchError,
    SearchResult,
    SearchResultItem,
    _raw_to_item,
    search,
    search_async,
)


# ---------------------------------------------------------------------------
# Dataclass unit tests
# ---------------------------------------------------------------------------


class TestSearchResultItem:
    def test_defaults(self):
        item = SearchResultItem(title="T", url="https://a.com")
        assert item.title == "T"
        assert item.url == "https://a.com"
        assert item.content == ""
        assert item.engine == ""
        assert item.score == 0.0
        assert item.category == ""
        assert item.extra == {}

    def test_all_fields(self):
        item = SearchResultItem(
            title="T",
            url="https://a.com",
            content="body",
            engine="google",
            score=1.5,
            category="general",
            extra={"publishedDate": "2026-01-01"},
        )
        assert item.engine == "google"
        assert item.extra["publishedDate"] == "2026-01-01"


class TestSearchResult:
    def test_defaults(self):
        result = SearchResult(query="q", number_of_results=0)
        assert result.results == []
        assert result.answers == []
        assert result.suggestions == []
        assert result.corrections == []

    def test_to_dict_basic(self):
        item = SearchResultItem(
            title="T",
            url="https://a.com",
            content="c",
            engine="g",
            score=1.0,
            category="general",
        )
        result = SearchResult(query="q", number_of_results=1, results=[item])
        d = result.to_dict()
        assert d["query"] == "q"
        assert d["number_of_results"] == 1
        assert len(d["results"]) == 1
        assert d["results"][0]["title"] == "T"
        assert d["results"][0]["url"] == "https://a.com"
        assert d["answers"] == []
        assert d["suggestions"] == []
        assert d["corrections"] == []

    def test_to_dict_spreads_extra(self):
        item = SearchResultItem(
            title="T",
            url="u",
            extra={"publishedDate": "2026-01-01", "thumbnail": "img.png"},
        )
        result = SearchResult(query="q", number_of_results=1, results=[item])
        d = result.to_dict()
        r = d["results"][0]
        assert r["publishedDate"] == "2026-01-01"
        assert r["thumbnail"] == "img.png"
        assert "extra" not in r

    def test_to_dict_with_suggestions(self):
        result = SearchResult(
            query="q",
            number_of_results=0,
            suggestions=["a", "b"],
            corrections=["c"],
        )
        d = result.to_dict()
        assert d["suggestions"] == ["a", "b"]
        assert d["corrections"] == ["c"]


class TestSearchError:
    def test_message_and_query(self):
        exc = SearchError("Something failed", query="test")
        assert str(exc) == "Something failed"
        assert exc.query == "test"

    def test_default_query(self):
        exc = SearchError("fail")
        assert exc.query == ""


class TestRawToItem:
    def test_known_fields_extracted(self):
        raw = {
            "title": "T",
            "url": "u",
            "content": "c",
            "engine": "g",
            "score": 2.0,
            "category": "general",
            "publishedDate": "2026-01-01",
        }
        item = _raw_to_item(raw)
        assert item.title == "T"
        assert item.score == 2.0
        assert item.extra == {"publishedDate": "2026-01-01"}


# ---------------------------------------------------------------------------
# Helpers for mocking httpx
# ---------------------------------------------------------------------------

_SAMPLE_SEARXNG_RESPONSE = {
    "query": "test",
    "number_of_results": 2,
    "results": [
        {
            "title": "Result 1",
            "url": "https://a.com",
            "content": "Content 1",
            "engine": "google",
            "score": 1.0,
            "category": "general",
        },
        {
            "title": "Result 2",
            "url": "https://b.com",
            "content": "Content 2",
            "engine": "bing",
            "score": 0.5,
            "category": "general",
            "publishedDate": "2026-01-15",
        },
    ],
    "answers": ["42"],
    "suggestions": ["test query"],
    "corrections": [],
}


def _mock_client(response_data=None, status_code=200):
    """Build an AsyncMock httpx client that returns *response_data* as JSON."""
    if response_data is None:
        response_data = _SAMPLE_SEARXNG_RESPONSE

    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ---------------------------------------------------------------------------
# search_async tests
# ---------------------------------------------------------------------------


class TestSearchAsync:
    @pytest.mark.asyncio
    async def test_success(self):
        mc = _mock_client()
        with patch("crawler.search.httpx.AsyncClient", return_value=mc):
            result = await search_async("test", searxng_url="http://x:1234")

        assert isinstance(result, SearchResult)
        assert result.query == "test"
        assert result.number_of_results == 2
        assert len(result.results) == 2
        assert result.results[0].title == "Result 1"
        assert result.results[1].extra.get("publishedDate") == "2026-01-15"
        assert result.answers == ["42"]
        assert result.suggestions == ["test query"]

    @pytest.mark.asyncio
    async def test_param_passthrough(self):
        mc = _mock_client()
        with patch("crawler.search.httpx.AsyncClient", return_value=mc):
            await search_async(
                "q",
                language="de",
                time_range="week",
                categories=["general", "news"],
                engines=["google", "bing"],
                safesearch=2,
                pageno=3,
                searxng_url="http://x:1234",
            )

        call_kwargs = mc.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["q"] == "q"
        assert params["language"] == "de"
        assert params["time_range"] == "week"
        assert params["categories"] == "general,news"
        assert params["engines"] == "google,bing"
        assert params["safesearch"] == 2
        assert params["pageno"] == 3

    @pytest.mark.asyncio
    async def test_max_results_clamping(self):
        data = dict(_SAMPLE_SEARXNG_RESPONSE)
        data["results"] = list(_SAMPLE_SEARXNG_RESPONSE["results"]) * 5  # 10 results
        mc = _mock_client(data)
        with patch("crawler.search.httpx.AsyncClient", return_value=mc):
            result = await search_async("q", max_results=3, searxng_url="http://x:1")

        assert len(result.results) == 3
        assert result.number_of_results == 3

    @pytest.mark.asyncio
    async def test_pageno_floor(self):
        mc = _mock_client()
        with patch("crawler.search.httpx.AsyncClient", return_value=mc):
            await search_async("q", pageno=0, searxng_url="http://x:1")

        params = mc.get.call_args.kwargs.get("params") or mc.get.call_args[1]["params"]
        assert params["pageno"] == 1

    @pytest.mark.asyncio
    async def test_http_401_raises_search_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_request = MagicMock()

        mc = AsyncMock()
        mc.__aenter__ = AsyncMock(return_value=mc)
        mc.__aexit__ = AsyncMock(return_value=False)
        mc.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "401", request=mock_request, response=mock_response
            )
        )

        with patch("crawler.search.httpx.AsyncClient", return_value=mc):
            with pytest.raises(SearchError, match="Authentication"):
                await search_async("q", searxng_url="http://x:1")

    @pytest.mark.asyncio
    async def test_http_500_raises_search_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_request = MagicMock()

        mc = AsyncMock()
        mc.__aenter__ = AsyncMock(return_value=mc)
        mc.__aexit__ = AsyncMock(return_value=False)
        mc.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "500", request=mock_request, response=mock_response
            )
        )

        with patch("crawler.search.httpx.AsyncClient", return_value=mc):
            with pytest.raises(SearchError, match="SearXNG API error"):
                await search_async("q", searxng_url="http://x:1")

    @pytest.mark.asyncio
    async def test_network_error_raises_search_error(self):
        mc = AsyncMock()
        mc.__aenter__ = AsyncMock(return_value=mc)
        mc.__aexit__ = AsyncMock(return_value=False)
        mc.get = AsyncMock(
            side_effect=httpx.RequestError("Connection refused", request=MagicMock())
        )

        with patch("crawler.search.httpx.AsyncClient", return_value=mc):
            with pytest.raises(SearchError, match="Request failed"):
                await search_async("q", searxng_url="http://x:1")

    @pytest.mark.asyncio
    async def test_env_var_override(self):
        mc = _mock_client()
        with patch("crawler.search.httpx.AsyncClient", return_value=mc) as mock_cls:
            await search_async("q", searxng_url="http://custom:9999")

        # The AsyncClient should have been called with base_url="http://custom:9999"
        call_kwargs = mock_cls.call_args
        assert call_kwargs.kwargs.get("base_url") == "http://custom:9999"

    @pytest.mark.asyncio
    async def test_runtime_env_lookup(self, monkeypatch):
        """Env var updates between calls are honoured (no import-time caching)."""
        mc = _mock_client()

        monkeypatch.setenv("SEARXNG_URL", "http://first:1111")
        with patch("crawler.search.httpx.AsyncClient", return_value=mc) as mock_cls:
            await search_async("q")
        assert mock_cls.call_args.kwargs["base_url"] == "http://first:1111"

        monkeypatch.setenv("SEARXNG_URL", "http://second:2222")
        with patch("crawler.search.httpx.AsyncClient", return_value=mc) as mock_cls:
            await search_async("q")
        assert mock_cls.call_args.kwargs["base_url"] == "http://second:2222"

    @pytest.mark.asyncio
    async def test_invalid_time_range_ignored(self):
        mc = _mock_client()
        with patch("crawler.search.httpx.AsyncClient", return_value=mc):
            await search_async("q", time_range="invalid", searxng_url="http://x:1")

        params = mc.get.call_args.kwargs.get("params") or mc.get.call_args[1]["params"]
        assert "time_range" not in params


class TestSearchSync:
    def test_sync_wrapper(self):
        expected = SearchResult(query="q", number_of_results=0)
        with patch(
            "crawler.search.search_async",
            new_callable=lambda: lambda: AsyncMock(return_value=expected),
        ):
            # We need to actually mock the asyncio.run path
            pass

        mc = _mock_client(
            {
                "query": "q",
                "number_of_results": 0,
                "results": [],
                "answers": [],
                "suggestions": [],
                "corrections": [],
            }
        )
        with patch("crawler.search.httpx.AsyncClient", return_value=mc):
            result = search("q", searxng_url="http://x:1")
        assert isinstance(result, SearchResult)
        assert result.query == "q"
