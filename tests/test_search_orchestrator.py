"""Tests for the multi-provider search orchestrator and its CLI/MCP wiring."""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
import pytest

from crawler import cli, mcp_server
from crawler import search_orchestrator as orchestrator
from crawler.search_orchestrator import (
    SEARXNG,
    YOUCOM,
    SearchProviderError,
    SearchResult,
    serialize_search_results,
)

LOGGER_NAME = "crawler.search_orchestrator"
YOUCOM_CONFIG = orchestrator.ProviderConfig(
    YOUCOM, orchestrator.YOUCOM_URL, api_key="sk-test"
)


def _result(title: str, url: str) -> SearchResult:
    return SearchResult(title=title, url=url, content=f"snippet-{title}")


def _configs() -> dict[str, orchestrator.ProviderConfig]:
    return {
        SEARXNG: orchestrator.ProviderConfig(SEARXNG, "https://searx.invalid"),
        YOUCOM: YOUCOM_CONFIG,
    }


def _web(count: int) -> list[dict]:
    return [
        {
            "title": f"T{i}",
            "url": f"https://example.com/{i}",
            "description": f"D{i}",
            "snippets": ["snippet"],
            "page_age": f"2026-10-0{i}T00:00:00",
        }
        for i in range(1, count + 1)
    ]


def _response(status: int = 200, *, json=None, text: str = "") -> httpx.Response:
    request = httpx.Request("GET", "https://provider.invalid")
    if json is not None:
        return httpx.Response(status, request=request, json=json)
    return httpx.Response(status, request=request, text=text)


def _request_error(message: str = "temporary network issue") -> httpx.RequestError:
    return httpx.ConnectError(message, request=httpx.Request("GET", "https://x.invalid"))


def _read_timeout() -> httpx.RequestError:
    return httpx.ReadTimeout("timed out", request=httpx.Request("GET", "https://x.invalid"))


class _Recorder:
    def __init__(self, items, route) -> None:
        self.items = list(items)
        self.route = route
        self.calls: list[dict] = []
        self.sleeps: list[float] = []
        self.timeouts: list[object] = []


def _install(monkeypatch: pytest.MonkeyPatch, *items, route=None) -> _Recorder:
    """Replace httpx.AsyncClient: record each GET, return or raise scripted items.

    Items are consumed in order and the last one repeats; ``route(url)`` picks
    the item per request instead.
    """
    recorder = _Recorder(items, route)

    class Client:
        def __init__(self, **kwargs):
            recorder.timeouts.append(kwargs.get("timeout"))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, *, params=None, headers=None, auth=None):
            recorder.calls.append(
                {"url": url, "params": params, "headers": headers, "auth": auth}
            )
            if recorder.route is not None:
                item = recorder.route(url)
            elif len(recorder.items) > 1:
                item = recorder.items.pop(0)
            else:
                item = recorder.items[0]
            if isinstance(item, BaseException):
                raise item
            return item

    async def fake_sleep(seconds: float) -> None:
        recorder.sleeps.append(seconds)

    monkeypatch.setattr(orchestrator.httpx, "AsyncClient", Client)
    monkeypatch.setattr(orchestrator.asyncio, "sleep", fake_sleep)
    return recorder


SHARED = ("Shared", "https://shared.example/a")


def _mock_providers(
    monkeypatch: pytest.MonkeyPatch,
    searxng=(SHARED, ("S only", "https://s.example/1")),
    youcom=(("Y only", "https://y.example/1"), SHARED),
) -> dict[str, list[dict]]:
    """Configure both providers and replace their calls, recording kwargs."""
    calls: dict[str, list[dict]] = {SEARXNG: [], YOUCOM: []}

    def fake(provider, items):
        async def call(query, **kwargs):
            calls[provider].append(kwargs)
            return [SearchResult(t, u, f"content {t}") for t, u in items]

        return call

    monkeypatch.setattr(orchestrator, "_resolve_provider_config", _configs)
    monkeypatch.setattr(orchestrator, "_search_searxng", fake(SEARXNG, searxng))
    monkeypatch.setattr(orchestrator, "_search_youcom", fake(YOUCOM, youcom))
    return calls


# --- Provider configuration and selection -----------------------------------


def test_provider_configuration_and_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEARXNG_URL", "https://s.example/")
    monkeypatch.setenv("YDC_API_KEY", " key \n")
    configured = orchestrator._resolve_provider_config()
    assert list(configured) == ["searxng", "youcom"]
    assert configured[SEARXNG].base_url == "https://s.example"
    assert configured[YOUCOM].base_url == orchestrator.YOUCOM_URL
    assert configured[YOUCOM].api_key == "key"
    assert orchestrator.configured_providers() == ["searxng", "youcom"]
    assert orchestrator._select_providers(configured) == ["searxng", "youcom"]
    assert orchestrator._select_providers(configured, "youcom,searxng,youcom") == [
        "searxng",
        "youcom",
    ]
    assert orchestrator._select_providers(configured, [" YouCom "]) == ["youcom"]

    monkeypatch.setenv("SEARXNG_USERNAME", "user")
    monkeypatch.setenv("SEARXNG_PASSWORD", "password")
    assert orchestrator._resolve_provider_config()[SEARXNG].username == "user"

    monkeypatch.setenv("YDC_API_KEY", " ")
    monkeypatch.delenv("SEARXNG_PASSWORD")
    configured = orchestrator._resolve_provider_config()
    assert configured == {}
    with pytest.raises(SearchProviderError) as raised:
        orchestrator._select_providers(configured)
    message = str(raised.value)
    assert "No valid" in message
    assert "SEARXNG_URL" in message
    assert "YDC_API_KEY" in message
    with pytest.raises(SearchProviderError, match="Unknown"):
        orchestrator._select_providers(_configs(), ["other"])
    with pytest.raises(SearchProviderError, match="not configured: youcom"):
        orchestrator._select_providers({SEARXNG: _configs()[SEARXNG]}, ["youcom"])
    with pytest.raises(SearchProviderError, match="empty"):
        orchestrator._select_providers(_configs(), " , ")


@pytest.mark.parametrize(
    "url", ["localhost:8888", "ftp://s.example", "https://user:pw@s.example"]
)
def test_invalid_searxng_url_disables_provider_and_warns_without_value(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, url: str
) -> None:
    monkeypatch.setenv("SEARXNG_URL", url)
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        assert orchestrator._resolve_provider_config() == {}
    assert len(caplog.records) == 1
    assert "SEARXNG_URL" in caplog.text
    assert url not in caplog.text
    assert "user:pw" not in caplog.text


def test_single_searxng_credential_warns_without_value(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("SEARXNG_URL", "https://s.example")
    monkeypatch.setenv("SEARXNG_USERNAME", "lonely-user-marker")
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        assert orchestrator._resolve_provider_config() == {}
    assert len(caplog.records) == 1
    assert "SEARXNG_USERNAME" in caplog.text
    assert "lonely-user-marker" not in caplog.text
    assert "s.example" not in caplog.text


@pytest.mark.parametrize("url", ["", "   "])
def test_empty_searxng_url_means_not_configured_without_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, url: str
) -> None:
    monkeypatch.setenv("SEARXNG_URL", url)
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        assert orchestrator._resolve_provider_config() == {}
    assert caplog.records == []


# --- SearXNG provider ---------------------------------------------------------


async def test_searxng_request_mapping_auth_retry_and_page_clamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _install(
        monkeypatch,
        _request_error("marker-secret"),
        _response(
            json={
                "results": [
                    {
                        "title": "S",
                        "url": "https://s.example/r",
                        "content": "body",
                        "publishedDate": "2026-07-17",
                    },
                    "ignored",
                ]
            }
        ),
    )
    results = await orchestrator._search_searxng(
        "private-query",
        config=orchestrator.ProviderConfig(
            SEARXNG, "https://secret.invalid", username="user", password="password"
        ),
        language="de",
        time_range="week",
        categories=["general", "news"],
        engines=["duckduckgo", "brave"],
        safesearch=2,
        pageno=0,
        max_retries=2,
    )
    assert len(recorder.calls) == 2
    assert recorder.sleeps == [0.5]
    assert recorder.timeouts == [30.0]
    call = recorder.calls[-1]
    assert call["url"] == "https://secret.invalid/search"
    assert call["params"] == {
        "q": "private-query",
        "format": "json",
        "language": "de",
        "safesearch": 2,
        "pageno": 1,
        "time_range": "week",
        "categories": "general,news",
        "engines": "duckduckgo,brave",
    }
    assert call["headers"] == {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    assert isinstance(call["auth"], httpx.BasicAuth)
    assert results == [
        SearchResult(
            title="S",
            url="https://s.example/r",
            content="body",
            publishedDate="2026-07-17",
            providers=["searxng"],
        )
    ]

    recorder = _install(monkeypatch, _response(json={"results": []}))
    await orchestrator._search_searxng(
        "q",
        config=orchestrator.ProviderConfig(SEARXNG, "https://s.invalid"),
        language="en",
        time_range="decade",
        categories=None,
        engines=None,
        safesearch=1,
        pageno=3,
        max_retries=1,
    )
    assert recorder.calls[0]["auth"] is None
    assert recorder.calls[0]["params"] == {
        "q": "q",
        "format": "json",
        "language": "en",
        "safesearch": 1,
        "pageno": 3,
    }


async def _searxng(**overrides) -> list[SearchResult]:
    kwargs = dict(
        config=orchestrator.ProviderConfig(SEARXNG, "https://endpoint-marker.invalid"),
        language="en",
        time_range=None,
        categories=None,
        engines=None,
        safesearch=1,
        pageno=1,
        max_retries=1,
    )
    kwargs.update(overrides)
    return await orchestrator._search_searxng("query-marker", **kwargs)


async def test_searxng_public_failures_are_sanitized(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _install(monkeypatch, _request_error("exception-marker"))
    with caplog.at_level(logging.DEBUG), pytest.raises(SearchProviderError) as raised:
        await _searxng()
    assert str(raised.value) == "request failed"
    combined = f"{raised.value} {caplog.text}"
    for marker in ("exception-marker", "query-marker", "endpoint-marker"):
        assert marker not in combined


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (401, "authentication failed, check SEARXNG_USERNAME/SEARXNG_PASSWORD"),
        (500, "request failed"),
    ],
)
async def test_searxng_status_reason_without_body_and_no_retry(
    monkeypatch: pytest.MonkeyPatch, status: int, reason: str
) -> None:
    recorder = _install(monkeypatch, _response(status, text="body-marker"))
    with pytest.raises(SearchProviderError) as raised:
        await _searxng(max_retries=3)
    assert str(raised.value) == reason
    assert len(recorder.calls) == 1
    assert recorder.sleeps == []


async def test_searxng_invalid_json_is_reported_as_invalid_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch, _response(text="<html>not json</html>"))
    with pytest.raises(SearchProviderError, match="^invalid response$"):
        await _searxng()


def test_searxng_published_date_missing_null_and_scalar_fallbacks() -> None:
    results = orchestrator._map_searxng_results(
        {
            "results": [
                {"title": "missing", "url": "https://missing", "content": ""},
                {
                    "title": "null",
                    "url": "https://null",
                    "content": "",
                    "publishedDate": None,
                },
                {
                    "title": "scalar",
                    "url": "https://scalar",
                    "content": "",
                    "publishedDate": 0,
                },
            ]
        }
    )
    assert [result.publishedDate for result in results] == ["", "", "0"]


# --- You.com provider ---------------------------------------------------------


async def _youcom(**overrides) -> list[SearchResult]:
    kwargs = dict(
        config=YOUCOM_CONFIG,
        language="en",
        time_range=None,
        pageno=1,
        max_results=10,
        max_retries=1,
    )
    kwargs.update(overrides)
    return await orchestrator._search_youcom("q", **kwargs)


async def test_youcom_request_and_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    web = _web(2)
    del web[1]["page_age"]
    recorder = _install(monkeypatch, _response(json={"results": {"web": web}}))

    results = await _youcom(language="de", time_range="week", pageno=3, max_results=7)

    call = recorder.calls[0]
    assert call["url"] == orchestrator.YOUCOM_URL
    assert call["headers"] == {
        "User-Agent": orchestrator.YOUCOM_USER_AGENT,
        "Accept": "application/json",
        "X-API-Key": "sk-test",
    }
    assert call["auth"] is None
    assert call["params"] == {
        "query": "q",
        "count": 7,
        "language": "DE",
        "freshness": "week",
        "offset": 2,
    }
    assert results == [
        SearchResult(
            "T1",
            "https://example.com/1",
            "D1",
            publishedDate="2026-10-01T00:00:00",
            providers=["youcom"],
        ),
        SearchResult("T2", "https://example.com/2", "D2", providers=["youcom"]),
    ]


@pytest.mark.parametrize("language", ["all", "auto", ""])
async def test_youcom_omits_no_filter_language(
    monkeypatch: pytest.MonkeyPatch, language: str
) -> None:
    recorder = _install(monkeypatch, _response(json={"results": {"web": []}}))
    await _youcom(language=language)
    assert recorder.calls[0]["params"] == {"query": "q", "count": 10}


async def test_youcom_without_hits_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch, _response(json={"results": {}}))
    assert await _youcom() == []


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (401, "API key rejected, check YDC_API_KEY"),
        (403, "API key rejected, check YDC_API_KEY"),
        (402, "API credits exhausted"),
        (429, "rate limit exceeded, try again later"),
        (500, "HTTP 500"),
    ],
)
async def test_youcom_status_reason_without_body(
    monkeypatch: pytest.MonkeyPatch, status: int, reason: str
) -> None:
    recorder = _install(monkeypatch, _response(status, text="error-body-marker"))
    with pytest.raises(SearchProviderError) as raised:
        await _youcom(max_retries=3)
    assert str(raised.value) == reason
    assert len(recorder.calls) == 1


async def test_youcom_retries_on_request_error(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _install(
        monkeypatch, _request_error(), _response(json={"results": {"web": _web(1)}})
    )
    results = await _youcom(max_retries=3)
    assert len(recorder.calls) == 2
    assert recorder.sleeps == [0.5]
    assert [result.title for result in results] == ["T1"]


# --- Merge --------------------------------------------------------------------


def test_round_robin_conservative_dedup_and_limit() -> None:
    first = [
        _result("x1", "HTTPS://Example.COM:443/a?b=2&a=1#one"),
        _result("x2", "https://example.com/second"),
        _result("empty-1", ""),
    ]
    second = [
        _result("duplicate", "https://example.com/a?b=2&a=1#two"),
        _result("query-order", "https://example.com/a?a=1&b=2"),
        _result("empty-2", ""),
    ]
    merged = orchestrator._merge_results([(SEARXNG, first), (YOUCOM, second)], 5)
    assert [item.title for item in merged] == [
        "x1",
        "x2",
        "query-order",
        "empty-1",
        "empty-2",
    ]
    assert merged[0].providers == ["searxng", "youcom"]
    assert all(item.providers for item in merged)
    assert orchestrator._url_dedup_key("http://EXAMPLE.com:80/a#x") == "http://example.com/a"
    assert (
        orchestrator._url_dedup_key("https://example.com:444/a")
        == "https://example.com:444/a"
    )
    assert orchestrator._url_dedup_key("not a url") is None
    assert orchestrator._merge_results([(SEARXNG, first), (YOUCOM, second)], -1) == []


def test_consensus_first_retains_fields_and_round_encounter_before_limiting() -> None:
    searxng = [
        SearchResult(
            "shared-first",
            "https://shared.test/item#x",
            "x-fields",
            publishedDate="2026-07-18",
        ),
        _result("x-only-2", "https://x.test/2"),
        _result("x-only-3", "https://x.test/3"),
    ]
    youcom = [
        _result("y-only-1", "https://y.test/1"),
        _result("y-only-2", "https://y.test/2"),
        SearchResult(
            "duplicate-loses",
            "HTTPS://SHARED.TEST:443/item#y",
            "y-fields",
            publishedDate="2025-01-01",
        ),
        _result("bad-url", "relative/path"),
        _result("bad-url-again", "relative/path"),
    ]

    merged = orchestrator._merge_results([(YOUCOM, youcom), (SEARXNG, searxng)], 6)

    assert [item.title for item in merged] == [
        "shared-first",
        "y-only-1",
        "x-only-2",
        "y-only-2",
        "x-only-3",
        "bad-url",
    ]
    assert merged[0].content == "x-fields"
    assert merged[0].publishedDate == "2026-07-18"
    assert merged[0].providers == ["searxng", "youcom"]
    assert merged[-1].providers == ["youcom"]
    assert [
        item.title
        for item in orchestrator._merge_results(
            [(SEARXNG, searxng), (YOUCOM, youcom)], 1
        )
    ] == ["shared-first"]


def test_reverse_rank_duplicate_keeps_earlier_rank_fields_and_fixed_order() -> None:
    searxng = [
        _result("x-only", "https://x.test/only"),
        SearchResult("x-later", "https://shared.test/item#x", "x-fields"),
    ]
    youcom = [
        SearchResult(
            "y-first",
            "HTTPS://SHARED.TEST:443/item#y",
            "y-fields",
            publishedDate="2026-06-01",
        )
    ]

    merged = orchestrator._merge_results([(SEARXNG, searxng), (YOUCOM, youcom)], 2)

    assert [item.title for item in merged] == ["y-first", "x-only"]
    assert merged[0].url == "HTTPS://SHARED.TEST:443/item#y"
    assert merged[0].content == "y-fields"
    assert merged[0].publishedDate == "2026-06-01"
    assert merged[0].providers == ["searxng", "youcom"]


def test_duplicate_from_one_provider_is_attributed_once() -> None:
    results = [_result("first", "https://same.test"), _result("again", "https://same.test#x")]
    merged = orchestrator._merge_results([(SEARXNG, results)], 10)
    assert [item.title for item in merged] == ["first"]
    assert merged[0].providers == ["searxng"]


# --- Orchestration --------------------------------------------------------------


async def test_parallel_start_and_partial_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    started = asyncio.Event()

    async def searxng(*args, **kwargs):
        await started.wait()
        return [_result("s1", "https://s/1"), _result("s2", "https://s/2")]

    async def youcom(*args, **kwargs):
        started.set()
        return [_result("y1", "https://y/1"), _result("y2", "https://y/2")]

    monkeypatch.setattr(orchestrator, "_resolve_provider_config", _configs)
    monkeypatch.setattr(orchestrator, "_search_searxng", searxng)
    monkeypatch.setattr(orchestrator, "_search_youcom", youcom)
    results = await orchestrator.search("q", max_results=4)
    assert [item.title for item in results] == ["s1", "y1", "s2", "y2"]
    assert [item.providers for item in results] == [
        ["searxng"],
        ["youcom"],
        ["searxng"],
        ["youcom"],
    ]

    async def failing(*args, **kwargs):
        raise SearchProviderError("API key rejected, check YDC_API_KEY")

    monkeypatch.setattr(orchestrator, "_search_youcom", failing)
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        results = await orchestrator.search("q")
    assert [item.title for item in results] == ["s1", "s2"]
    assert [item.providers for item in results] == [["searxng"], ["searxng"]]
    assert (
        "Search provider youcom failed: API key rejected, check YDC_API_KEY"
        in caplog.text
    )


async def test_total_failure_lists_sanitized_reasons(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def searxng_failing(*args, **kwargs):
        raise SearchProviderError("request failed")

    async def youcom_crashing(*args, **kwargs):
        raise RuntimeError("secret backend detail")

    monkeypatch.setattr(orchestrator, "_resolve_provider_config", _configs)
    monkeypatch.setattr(orchestrator, "_search_searxng", searxng_failing)
    monkeypatch.setattr(orchestrator, "_search_youcom", youcom_crashing)
    with caplog.at_level(logging.DEBUG), pytest.raises(SearchProviderError) as raised:
        await orchestrator.search("private query")
    assert str(raised.value) == (
        "All selected search providers failed: "
        "searxng: request failed; youcom: unexpected error"
    )
    assert "Search provider youcom failed: unexpected error (RuntimeError)" in caplog.text
    assert "secret backend detail" not in caplog.text


@pytest.mark.parametrize(("requested", "expected"), [(0, 1), (100, 50)])
async def test_max_results_is_clamped(
    monkeypatch: pytest.MonkeyPatch, requested: int, expected: int
) -> None:
    seen: dict[str, int] = {}

    async def youcom(*args, max_results, **kwargs):
        seen["count"] = max_results
        return [_result(f"y{i}", f"https://y/{i}") for i in range(60)]

    monkeypatch.setattr(
        orchestrator, "_resolve_provider_config", lambda: {YOUCOM: YOUCOM_CONFIG}
    )
    monkeypatch.setattr(orchestrator, "_search_youcom", youcom)
    results = await orchestrator.search("q", max_results=requested)
    assert seen["count"] == expected
    assert len(results) == expected


async def test_outer_cancellation_cancels_running_provider_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = {SEARXNG: asyncio.Event(), YOUCOM: asyncio.Event()}
    cancelled: list[str] = []

    def hanging(provider: str):
        async def call(*args, **kwargs):
            started[provider].set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(provider)

        return call

    monkeypatch.setattr(orchestrator, "_resolve_provider_config", _configs)
    monkeypatch.setattr(orchestrator, "_search_searxng", hanging(SEARXNG))
    monkeypatch.setattr(orchestrator, "_search_youcom", hanging(YOUCOM))
    outer = asyncio.create_task(orchestrator.search("q"))
    # Cancel only after both calls run; a call cancelled before its first step
    # never enters its finally block.
    await asyncio.wait_for(
        asyncio.gather(*(event.wait() for event in started.values())), timeout=1
    )
    outer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await outer
    assert sorted(cancelled) == ["searxng", "youcom"]


# --- Serializer ---------------------------------------------------------------


def _two_results() -> list[SearchResult]:
    return [
        SearchResult(
            "Result A",
            "https://a.example",
            "A",
            publishedDate="2026-01-01",
            providers=["searxng"],
        ),
        SearchResult("Result B", "https://b.example", "B", providers=["searxng", "youcom"]),
    ]


def test_serialize_selected_fields_and_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEARCH_RESULT_FIELDS", "title,url")
    assert serialize_search_results("python", _two_results()) == {
        "query": "python",
        "number_of_results": 2,
        "results": [
            {"title": "Result A", "url": "https://a.example"},
            {"title": "Result B", "url": "https://b.example"},
        ],
    }


@pytest.mark.parametrize("value", [None, "", "   "])
def test_serialize_all_normalized_fields_when_unset_or_empty(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("SEARCH_RESULT_FIELDS", raising=False)
    else:
        monkeypatch.setenv("SEARCH_RESULT_FIELDS", value)
    payload = serialize_search_results("python", _two_results())
    assert payload["number_of_results"] == 2
    assert payload["results"][0] == {
        "title": "Result A",
        "url": "https://a.example",
        "content": "A",
        "publishedDate": "2026-01-01",
        "providers": ["searxng"],
    }


def test_serialize_empty_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEARCH_RESULT_FIELDS", "title,url")
    assert serialize_search_results("python", []) == {
        "query": "python",
        "number_of_results": 0,
        "results": [],
    }


def test_serialize_missing_requested_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEARCH_RESULT_FIELDS", "title,engine")
    assert serialize_search_results("python", _two_results())["results"] == [
        {"title": "Result A"},
        {"title": "Result B"},
    ]


@pytest.mark.parametrize("value", ["", "   "])
def test_parse_search_result_fields_returns_none_for_empty_or_whitespace(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("SEARCH_RESULT_FIELDS", value)
    assert orchestrator._parse_search_result_fields() is None


def test_parse_search_result_fields_returns_none_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SEARCH_RESULT_FIELDS", raising=False)
    assert orchestrator._parse_search_result_fields() is None


# --- CLI and MCP with mocked providers ------------------------------------------


async def test_mcp_envelope_and_result_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_providers(monkeypatch)
    monkeypatch.delenv("SEARCH_RESULT_FIELDS", raising=False)

    payload = json.loads(await mcp_server.search(query="q"))

    assert payload["query"] == "q"
    assert payload["number_of_results"] == 3
    assert [item["title"] for item in payload["results"]] == ["Shared", "Y only", "S only"]
    assert payload["results"][0] == {
        "title": "Shared",
        "url": "https://shared.example/a",
        "content": "content Shared",
        "publishedDate": "",
        "providers": ["searxng", "youcom"],
    }

    monkeypatch.setenv("SEARCH_RESULT_FIELDS", "title,providers")
    payload = json.loads(await mcp_server.search(query="q"))
    assert payload["results"][0] == {
        "title": "Shared",
        "providers": ["searxng", "youcom"],
    }


async def test_mcp_providers_param_selects_youcom_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _mock_providers(monkeypatch)
    monkeypatch.delenv("SEARCH_RESULT_FIELDS", raising=False)

    payload = json.loads(
        await mcp_server.search(
            query="q",
            providers=["youcom"],
            engines=["google"],
            categories=["news"],
            safesearch=2,
            max_retries=2,
        )
    )

    assert calls[SEARXNG] == []
    assert len(calls[YOUCOM]) == 1
    assert not {"engines", "categories", "safesearch"} & set(calls[YOUCOM][0])
    assert calls[YOUCOM][0]["max_retries"] == 2
    assert [item["providers"] for item in payload["results"]] == [["youcom"], ["youcom"]]


async def test_cli_markdown_sources_and_providers_flag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = _mock_providers(monkeypatch)
    monkeypatch.delenv("SEARCH_RESULT_FIELDS", raising=False)

    assert await cli._run_search_async(cli._parse_search_args(["q"])) == 0
    out = capsys.readouterr().out
    assert "## 1. Shared\nhttps://shared.example/a\n**Sources:** searxng, youcom\n" in out
    assert "**Sources:** youcom" in out
    assert "Related searches" not in out
    assert calls[SEARXNG][0]["max_retries"] == 1
    assert calls[YOUCOM][0]["max_retries"] == 1

    argv = ["q", "--providers", "youcom", "--json"]
    assert await cli._run_search_async(cli._parse_search_args(argv)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [item["providers"] for item in payload["results"]] == [["youcom"], ["youcom"]]
    assert len(calls[SEARXNG]) == 1

    monkeypatch.setenv("SEARCH_RESULT_FIELDS", "title,url")
    assert await cli._run_search_async(cli._parse_search_args(["q"])) == 0
    assert "**Sources:**" not in capsys.readouterr().out


async def test_mcp_retries_provider_on_read_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SEARXNG_URL", "https://searx.test")
    monkeypatch.delenv("SEARCH_RESULT_FIELDS", raising=False)
    recorder = _install(
        monkeypatch,
        _read_timeout(),
        _response(json={"results": [{"title": "ok", "url": "https://ok.example"}]}),
    )

    payload = json.loads(await mcp_server.search(query="q", max_retries=3))

    assert len(recorder.calls) == 2
    assert recorder.sleeps == [0.5]
    assert payload["results"][0]["title"] == "ok"


async def test_cli_single_attempt_on_read_timeout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SEARXNG_URL", "https://searx.test")
    monkeypatch.delenv("SEARCH_RESULT_FIELDS", raising=False)
    recorder = _install(monkeypatch, _read_timeout())

    assert await cli._run_search_async(cli._parse_search_args(["q"])) == 1
    assert len(recorder.calls) == 1
    assert recorder.sleeps == []

    monkeypatch.setenv("YDC_API_KEY", "sk-test")
    recorder = _install(
        monkeypatch,
        route=lambda url: (
            _read_timeout()
            if url.startswith("https://searx.test")
            else _response(json={"results": {"web": _web(2)}})
        ),
    )

    assert await cli._run_search_async(cli._parse_search_args(["q", "--json"])) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [item["title"] for item in payload["results"]] == ["T1", "T2"]
    assert len(recorder.calls) == 2
    assert recorder.sleeps == []


@pytest.mark.parametrize(
    ("providers", "message"),
    [
        (None, "No valid search provider is configured"),
        (["bing"], "Unknown search provider: bing"),
        (["youcom"], "Search provider is not configured: youcom"),
    ],
)
async def test_selection_errors_in_mcp_and_cli(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    providers: list[str] | None,
    message: str,
) -> None:
    if providers is not None:
        monkeypatch.setenv("SEARXNG_URL", "https://searx.test")
    recorder = _install(monkeypatch, _response(json={"results": []}))

    payload = json.loads(await mcp_server.search(query="q", providers=providers))
    argv = ["q"] + (["--providers", ",".join(providers)] if providers else [])
    rc = await cli._run_search_async(cli._parse_search_args(argv))

    assert payload["query"] == "q"
    assert message in payload["error"]
    assert rc == 1
    assert message in caplog.text
    assert recorder.calls == []


# --- Secret leak ------------------------------------------------------------------

SECRETS = {
    "YDC_API_KEY": "ydc-secret-marker",
    "SEARXNG_USERNAME": "user-secret-marker",
    "SEARXNG_PASSWORD": "pass-secret-marker",
}
ENDPOINT_MARKER = "searx-endpoint-marker"


@pytest.mark.parametrize("failure", [401, 403, 429, 500, "request-error"])
async def test_secrets_never_leak_into_results_or_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, failure
) -> None:
    caplog.set_level(logging.DEBUG)
    for name, value in SECRETS.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("SEARXNG_URL", f"https://{ENDPOINT_MARKER}.test")
    markers = [*SECRETS.values(), ENDPOINT_MARKER]
    leak = " ".join(markers)

    def route(url: str):
        if failure == "request-error":
            return httpx.ConnectError(f"failed {leak}", request=httpx.Request("GET", url))
        return _response(failure, text=f"body {leak}")

    _install(monkeypatch, route=route)

    out = await mcp_server.search(query="q", max_retries=2)

    assert "All selected search providers failed" in json.loads(out)["error"]
    for marker in markers:
        assert marker not in out
        assert marker not in caplog.text
