"""Tests for the multi-provider search orchestrator and its CLI/MCP wiring."""

from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlsplit

import httpx
import pytest

import crawler
from crawler import cli, mcp_server
from crawler.document import CrawledDocument
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


def _response(
    status: int = 200, *, json=None, text: str = "", headers=None
) -> httpx.Response:
    request = httpx.Request("GET", "https://provider.invalid")
    if json is not None:
        return httpx.Response(status, request=request, json=json, headers=headers)
    return httpx.Response(status, request=request, text=text, headers=headers)


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
    """Replace httpx.AsyncClient: record each request, return or raise scripted items.

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

        async def request(
            self, method, url, *, params=None, json=None, headers=None, auth=None
        ):
            recorder.calls.append(
                {
                    "method": method,
                    "url": url,
                    "params": params,
                    "json": json,
                    "headers": headers,
                    "auth": auth,
                }
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


@pytest.mark.parametrize("raw", [
    "not-json-secret", '["secret"]', '{"X-Key": 123}',
    '{"X-Key": "secret\\nvalue"}', '{"X-Key": "secret\\u007f"}',
    '{"Bad Header": "secret"}', '{"X-Key\\n": "secret"}',
    '{"X-Key": "@relative-secret"}', '{"X-Key": "secret\\u00e4"}',
])
async def test_invalid_extra_headers_disable_searxng_without_request_or_secret(
    monkeypatch, caplog, raw,
) -> None:
    monkeypatch.setenv("SEARXNG_URL", "https://searx.test")
    monkeypatch.setenv("SEARXNG_EXTRA_HEADERS", raw)
    recorder = _install(monkeypatch)

    with caplog.at_level(logging.WARNING):
        payload = json.loads(await mcp_server.search(query="q"))

    assert recorder.calls == []
    assert "No valid search provider" in payload["error"]
    assert "SEARXNG_EXTRA_HEADERS" in caplog.text
    assert "secret" not in caplog.text + json.dumps(payload)


@pytest.mark.parametrize("contents", [None, b"secret\nvalue", b"secret\xff"])
async def test_invalid_header_file_keeps_youcom_available(
    monkeypatch, tmp_path, caplog, contents,
) -> None:
    secret = tmp_path / "secret-file"
    if contents is not None:
        secret.write_bytes(contents)
    monkeypatch.setenv("SEARXNG_URL", "https://searx.test")
    monkeypatch.setenv("YDC_API_KEY", "sk-test")
    monkeypatch.setenv("SEARXNG_EXTRA_HEADERS", json.dumps({"X-Key": f"@{secret}"}))
    recorder = _install(monkeypatch, _response(json={"results": {"web": _web(1)}}))

    with caplog.at_level(logging.WARNING):
        results = await orchestrator.search("q")

    assert len(results) == 1
    assert [c["url"] for c in recorder.calls] == [orchestrator.YOUCOM_URL]
    assert "secret" not in caplog.text
    assert "secret" not in repr(orchestrator._resolve_provider_config())


@pytest.mark.parametrize("entrypoint", ["mcp", "cli"])
async def test_extra_headers_reach_searxng_only_with_required_json_headers(
    monkeypatch, tmp_path, entrypoint,
) -> None:
    secret = tmp_path / "secret"
    secret.write_text("header-secret\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SEARXNG_URL", "https://searx.test")
    monkeypatch.setenv("YDC_API_KEY", "sk-test")
    monkeypatch.setenv("SEARXNG_EXTRA_HEADERS", json.dumps({
        "CF-Access-Client-Secret": f"@{secret}" if entrypoint == "mcp" else "@~/secret",
        "User-Agent": "custom-agent",
        "accept": "text/html", "CONTENT-TYPE": "text/plain",
    }))
    recorder = _install(monkeypatch, route=lambda url: _response(
        json={"results": []} if "searx.test" in url else {"results": {"web": []}}
    ))

    if entrypoint == "mcp":
        assert "error" not in json.loads(await mcp_server.search(query="q"))
    else:
        assert await cli._run_search_async(cli._parse_search_args(["q"])) == 0

    searx = next(c for c in recorder.calls if "searx.test" in c["url"])
    youcom = next(c for c in recorder.calls if "ydc-index.io" in c["url"])
    headers = httpx.Headers(searx["headers"])
    assert headers["CF-Access-Client-Secret"] == "header-secret"
    assert headers["User-Agent"] == "custom-agent"
    assert headers.get_list("Accept") == ["application/json"]
    assert headers.get_list("Content-Type") == ["application/json"]
    assert "CF-Access-Client-Secret" not in httpx.Headers(youcom["headers"])
    assert "header-secret" not in repr(orchestrator._resolve_provider_config())


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
    assert call["method"] == "GET"
    assert call["json"] is None
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
        safesearch=1,
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

    results = await _youcom(
        language="de", time_range="week", safesearch=2, pageno=3, max_results=7
    )

    call = recorder.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == orchestrator.YOUCOM_URL
    assert call["headers"] == {
        "User-Agent": orchestrator.YOUCOM_USER_AGENT,
        "Accept": "application/json",
        "X-API-Key": "sk-test",
    }
    assert call["auth"] is None
    assert call["params"] is None
    assert call["json"] == {
        "query": "q",
        "count": 7,
        "language": "DE",
        "freshness": "week",
        "safesearch": "strict",
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


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("de", "DE"),
        ("en-us", "EN"),
        ("en-GB", "EN-GB"),
        ("en_gb", "EN-GB"),
        ("pt-br", "PT-BR"),
        (" zh-hant ", "ZH-HANT"),
        ("zh", None),
        ("all", None),
        ("auto", None),
        ("", None),
    ],
)
async def test_youcom_language_maps_to_enum_or_is_omitted(
    monkeypatch: pytest.MonkeyPatch, language: str, expected: str | None
) -> None:
    recorder = _install(monkeypatch, _response(json={"results": {"web": []}}))
    await _youcom(language=language)
    assert recorder.calls[0]["json"].get("language") == expected


@pytest.mark.parametrize(
    ("safesearch", "expected"), [(0, "off"), (1, "moderate"), (2, "strict")]
)
async def test_youcom_safesearch_maps_to_named_level(
    monkeypatch: pytest.MonkeyPatch, safesearch: int, expected: str
) -> None:
    recorder = _install(monkeypatch, _response(json={"results": {"web": []}}))
    await _youcom(safesearch=safesearch)
    assert recorder.calls[0]["json"]["safesearch"] == expected


async def test_youcom_page_beyond_ten_sends_no_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _install(monkeypatch, _response(json={"results": {"web": _web(1)}}))
    assert await _youcom(pageno=11) == []
    assert recorder.calls == []

    await _youcom(pageno=10)
    assert recorder.calls[0]["json"]["offset"] == 9


async def test_youcom_page_beyond_ten_leaves_searxng_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(orchestrator, "_resolve_provider_config", _configs)
    recorder = _install(
        monkeypatch,
        route=lambda url: _response(
            json={"results": [{"title": "S", "url": "https://s.example/11"}]}
        ),
    )
    results = await orchestrator.search("q", pageno=11)
    assert [call["url"] for call in recorder.calls] == ["https://searx.invalid/search"]
    assert recorder.calls[0]["params"]["pageno"] == 11
    assert [(item.title, item.providers) for item in results] == [("S", ["searxng"])]


async def test_youcom_content_falls_back_to_first_snippet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    web = _web(4)
    web[0]["description"] = ""
    web[0]["snippets"] = ["", "first non-empty", "second"]
    del web[1]["description"]
    web[2]["description"] = None
    web[2]["snippets"] = []
    web[3]["description"] = ""
    del web[3]["snippets"]
    _install(monkeypatch, _response(json={"results": {"web": web}}))
    results = await _youcom()
    assert [result.content for result in results] == ["first non-empty", "snippet", "", ""]


async def test_youcom_without_hits_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install(monkeypatch, _response(json={"results": {}}))
    assert await _youcom() == []


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (401, "API key rejected, check YDC_API_KEY"),
        (
            403,
            "API key lacks the required scope for this endpoint, check YDC_API_KEY",
        ),
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


def _rate_limited(retry_after: str | None = None) -> httpx.Response:
    headers = {"Retry-After": retry_after} if retry_after is not None else None
    return _response(429, text="body", headers=headers)


async def test_youcom_429_with_short_retry_after_sleeps_once_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _install(
        monkeypatch, _rate_limited("2"), _response(json={"results": {"web": _web(1)}})
    )
    results = await _youcom(max_retries=3)
    assert len(recorder.calls) == 2
    assert recorder.sleeps == [2.0]
    assert [result.title for result in results] == ["T1"]


async def test_429_is_retried_at_most_once(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _install(monkeypatch, _rate_limited("1"))
    with pytest.raises(SearchProviderError) as raised:
        await _youcom(max_retries=3)
    assert str(raised.value) == "rate limit exceeded, retry after 1s"
    assert len(recorder.calls) == 2
    assert recorder.sleeps == [1.0]


@pytest.mark.parametrize(
    ("retry_after", "max_retries", "reason"),
    [
        ("30", 3, "rate limit exceeded, retry after 30s"),
        (None, 3, "rate limit exceeded, try again later"),
        ("soon", 3, "rate limit exceeded, try again later"),
        ("2", 1, "rate limit exceeded, retry after 2s"),
    ],
)
async def test_youcom_429_without_retry_reports_hint(
    monkeypatch: pytest.MonkeyPatch,
    retry_after: str | None,
    max_retries: int,
    reason: str,
) -> None:
    recorder = _install(monkeypatch, _rate_limited(retry_after))
    with pytest.raises(SearchProviderError) as raised:
        await _youcom(max_retries=max_retries)
    assert str(raised.value) == reason
    assert len(recorder.calls) == 1
    assert recorder.sleeps == []


def test_retry_after_parses_seconds_and_http_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FixedDatetime(orchestrator.datetime):
        @classmethod
        def now(cls, tz=None):
            return orchestrator.datetime(2026, 10, 15, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(orchestrator, "datetime", FixedDatetime)
    parse = orchestrator._retry_after_seconds
    assert parse(" 3 ") == 3.0
    assert parse("Thu, 15 Oct 2026 12:00:04 GMT") == 4.0
    assert parse("Thu, 15 Oct 2026 11:59:00 GMT") == 0.0
    for invalid in (None, "", "-1", "1.5", "soon"):
        assert parse(invalid) is None


async def test_searxng_429_uses_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _install(
        monkeypatch, _rate_limited("1"), _response(json={"results": []})
    )
    assert await _searxng(max_retries=2) == []
    assert recorder.sleeps == [1.0]
    assert [call["method"] for call in recorder.calls] == ["GET", "GET"]


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
    assert not {"engines", "categories"} & set(calls[YOUCOM][0])
    assert calls[YOUCOM][0]["safesearch"] == 2
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


# --- Search with page content -------------------------------------------------


def _mock_page_crawl(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Replace crawl_pages_async; pages under y.example fail. Records URL batches."""
    batches: list[list[str]] = []

    async def fake_crawl_pages_async(urls, **kwargs):
        assert kwargs == {"timeout": 15}
        batches.append(list(urls))
        return [
            CrawledDocument(u, u, "failed", "", error_message="Timeout after 15s")
            if "y.example" in u
            else CrawledDocument(u, u, "success", f"# page {u}")
            for u in urls
        ]

    monkeypatch.setattr(crawler, "crawl_pages_async", fake_crawl_pages_async)
    return batches


async def test_mcp_include_content_adds_markdown_and_crawl_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_providers(monkeypatch)
    batches = _mock_page_crawl(monkeypatch)
    monkeypatch.delenv("SEARCH_RESULT_FIELDS", raising=False)

    plain = json.loads(await mcp_server.search(query="q"))
    assert batches == []
    assert not any({"markdown", "crawl_error"} & set(item) for item in plain["results"])

    payload = json.loads(await mcp_server.search(query="q", include_content=True))
    urls = [item["url"] for item in payload["results"]]
    assert batches == [urls]
    for item in payload["results"]:
        if "y.example" in item["url"]:
            assert item["crawl_error"] == "Timeout after 15s"
            assert "markdown" not in item
        else:
            assert item["markdown"] == f"# page {item['url']}"
            assert "crawl_error" not in item

    # SEARCH_RESULT_FIELDS may drop url; the pages are still crawled by URL.
    monkeypatch.setenv("SEARCH_RESULT_FIELDS", "title")
    payload = json.loads(await mcp_server.search(query="q", include_content=True))
    assert batches[-1] == urls
    assert payload["results"][0] == {"title": "Shared", "markdown": f"# page {urls[0]}"}


async def test_include_content_skips_crawl_without_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_providers(monkeypatch, searxng=(), youcom=())
    batches = _mock_page_crawl(monkeypatch)

    payload = json.loads(await mcp_server.search(query="q", include_content=True))

    assert payload["results"] == []
    assert batches == []


async def test_cli_include_content_markdown_and_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _mock_providers(monkeypatch)
    batches = _mock_page_crawl(monkeypatch)
    monkeypatch.delenv("SEARCH_RESULT_FIELDS", raising=False)

    assert await cli._run_search_async(cli._parse_search_args(["q"])) == 0
    assert batches == []
    capsys.readouterr()

    argv = ["q", "--include-content"]
    assert await cli._run_search_async(cli._parse_search_args(argv)) == 0
    out = capsys.readouterr().out
    assert "content Shared\n\n### page https://shared.example/a\n\n---" in out
    result_headings = [line for line in out.splitlines() if line.startswith("## ")]
    assert result_headings == ["## 1. Shared", "## 2. Y only", "## 3. S only"]
    assert "**Crawl error:** Timeout after 15s" in out

    argv = ["q", "--include-content", "--json"]
    assert await cli._run_search_async(cli._parse_search_args(argv)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["results"][0]["markdown"] == "# page https://shared.example/a"
    assert len(batches) == 2


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
            if urlsplit(url).hostname == "searx.test"
            else _response(json={"results": {"web": _web(2)}})
        ),
    )

    assert await cli._run_search_async(cli._parse_search_args(["q", "--json"])) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [item["title"] for item in payload["results"]] == ["T1", "T2"]
    assert len(recorder.calls) == 2
    assert recorder.sleeps == []


async def test_cli_never_sleeps_on_429(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("YDC_API_KEY", "sk-test")
    recorder = _install(monkeypatch, _rate_limited("1"))

    assert await cli._run_search_async(cli._parse_search_args(["q"])) == 1
    assert len(recorder.calls) == 1
    assert recorder.sleeps == []
    assert "youcom: rate limit exceeded, retry after 1s" in caplog.text


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
