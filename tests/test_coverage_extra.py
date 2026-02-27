"""Additional branch coverage tests for runtime edge paths."""

from __future__ import annotations

import argparse
import json
import runpy
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from crawler.auth import AuthConfig, build_browser_config, load_auth_from_env
from crawler.builder import build_document_from_result
from crawler.capture import (
    capture_auth_state,
    capture_auth_state_sync,
    _resolve_profile_dir,
)
from crawler.cli import (
    _build_cli_auth,
    _parse_crawl_args,
    _run_crawl_async,
    _run_search_async,
    _write_output,
    main,
    search_main,
)
from crawler.document import CrawledDocument
from crawler.mcp_server import _build_auth_config
from crawler.site import SiteCrawlResult, _iterate_results, crawl_site, crawl_site_async


def _make_crawl_result(**kwargs):
    result = MagicMock()
    result.url = kwargs.get("url", "https://example.com")
    result.success = kwargs.get("success", True)
    result.html = kwargs.get("html", "")
    result.cleaned_html = kwargs.get("cleaned_html", "")
    result.error_message = kwargs.get("error_message", None)
    result.status_code = kwargs.get("status_code", 200)
    result.response_headers = kwargs.get("response_headers", {})
    result.metadata = kwargs.get("metadata", {"requested_url": "https://example.com"})
    result.links = kwargs.get("links", {})
    markdown = MagicMock()
    markdown.fit_markdown = kwargs.get("fit_markdown", "")
    markdown.raw_markdown = kwargs.get("raw_markdown", "")
    markdown.markdown_with_citations = kwargs.get("citations_markdown", "")
    markdown.references_markdown = kwargs.get("references_markdown", "")
    result.markdown = markdown
    return result


def _make_playwright_mock(
    *,
    page_url: str = "https://example.com/dashboard",
    is_closed_side_effect=None,
    page_url_error: bool = False,
):
    page = MagicMock()
    if page_url_error:
        type(page).url = PropertyMock(side_effect=Exception("url-unavailable"))
    else:
        type(page).url = PropertyMock(return_value=page_url)
    if is_closed_side_effect is None:
        page.is_closed = MagicMock(return_value=False)
    else:
        page.is_closed = MagicMock(side_effect=is_closed_side_effect)
    page.goto = AsyncMock()

    context = AsyncMock()
    context.pages = [page]
    context.new_page = AsyncMock(return_value=page)
    context.storage_state = AsyncMock(return_value={"cookies": [], "origins": []})

    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()

    pw = MagicMock()
    pw.chromium = MagicMock()
    pw.chromium.launch = AsyncMock(return_value=browser)
    pw.chromium.launch_persistent_context = AsyncMock(return_value=context)

    pw_cm = AsyncMock()
    pw_cm.__aenter__ = AsyncMock(return_value=pw)
    pw_cm.__aexit__ = AsyncMock(return_value=None)
    return pw_cm, page, context


def _close_coro_and_return(value):
    def _runner(coro):
        coro.close()
        return value

    return _runner


def _close_coro_and_raise(exc: Exception):
    def _runner(coro):
        coro.close()
        raise exc

    return _runner


class TestSyncWrappers:
    def test_init_sync_wrappers_call_asyncio_run(self):
        from crawler import crawl_page, crawl_pages

        doc = CrawledDocument(
            request_url="u",
            final_url="u",
            status="success",
            markdown="m",
        )
        with patch(
            "crawler.asyncio.run",
            side_effect=_close_coro_and_return(doc),
        ) as mock_run:
            assert crawl_page("https://example.com") == doc
            assert mock_run.call_count == 1

        with patch(
            "crawler.asyncio.run",
            side_effect=_close_coro_and_return([doc]),
        ) as mock_run:
            assert crawl_pages(["https://example.com"]) == [doc]
            assert mock_run.call_count == 1

    def test_site_sync_wrapper_calls_asyncio_run(self):
        expected = SiteCrawlResult()
        with patch(
            "crawler.site.asyncio.run",
            side_effect=_close_coro_and_return(expected),
        ) as mock_run:
            result = crawl_site("https://example.com")
            assert result is expected
            mock_run.assert_called_once()

    def test_capture_sync_wrapper_calls_asyncio_run(self):
        with patch(
            "crawler.capture.asyncio.run",
            side_effect=_close_coro_and_return("/tmp/state.json"),
        ) as mock_run:
            out = capture_auth_state_sync("https://login.example.com")
            assert out == "/tmp/state.json"
            mock_run.assert_called_once()


class TestAuthBranches:
    def test_browser_config_storage_state_branch(self):
        cfg = build_browser_config(
            AuthConfig(storage_state_data={"cookies": [], "origins": []})
        )
        assert cfg.storage_state == {"cookies": [], "origins": []}

    def test_env_missing_cookie_file_branch(self):
        with patch.dict(
            "os.environ",
            {"CRAWL_AUTH_COOKIES_FILE": "/definitely/missing.json"},
            clear=True,
        ):
            cfg = load_auth_from_env()
            assert cfg is not None
            assert cfg.cookies is None


class TestBuilderBranches:
    def test_empty_primary_markdown_fallback(self):
        result = _make_crawl_result(
            html=None,
            cleaned_html=None,
            fit_markdown="",
            raw_markdown="",
            citations_markdown="",
        )
        doc = build_document_from_result(result)
        assert doc.status == "success"
        assert doc.markdown == ""
        assert doc.raw_markdown == ""


class TestCaptureBranches:
    def test_resolve_profile_dir_paths(self):
        absolute = _resolve_profile_dir("/tmp/profile")
        assert str(absolute) == "/tmp/profile"
        relative = _resolve_profile_dir("named-profile")
        assert str(relative).endswith("/.crawl4ai/profiles/named-profile")

    @pytest.mark.asyncio
    async def test_capture_profile_persistent_context_and_close_error(self):
        pw_cm, _, context = _make_playwright_mock()
        context.close = AsyncMock(side_effect=Exception("close-failed"))

        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir) / "profile"
            with patch("playwright.async_api.async_playwright", return_value=pw_cm):
                with patch(
                    "crawler.capture._resolve_profile_dir", return_value=profile_dir
                ):
                    with patch("crawler.capture.asyncio.sleep", new_callable=AsyncMock):
                        out = await capture_auth_state(
                            url="https://login.example.com",
                            wait_for_url="/dashboard",
                            timeout=1,
                            profile="profile-name",
                        )

            assert out == str(profile_dir / "storage_state.json")
            assert (profile_dir / "storage_state.json").exists()

    @pytest.mark.asyncio
    async def test_capture_wait_for_url_closed_in_polling_loop(self):
        pw_cm, _, _ = _make_playwright_mock(is_closed_side_effect=[False, True])
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "state.json"
            with patch("playwright.async_api.async_playwright", return_value=pw_cm):
                with patch("crawler.capture.asyncio.sleep", new_callable=AsyncMock):
                    await capture_auth_state(
                        url="https://login.example.com",
                        output_path=str(out_file),
                        wait_for_url="/never",
                        timeout=1,
                    )
            assert out_file.exists()

    @pytest.mark.asyncio
    async def test_capture_wait_for_url_page_url_exception(self):
        pw_cm, _, _ = _make_playwright_mock(
            is_closed_side_effect=[False, False],
            page_url_error=True,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "state.json"
            with patch("playwright.async_api.async_playwright", return_value=pw_cm):
                with patch("crawler.capture.asyncio.sleep", new_callable=AsyncMock):
                    await capture_auth_state(
                        url="https://login.example.com",
                        output_path=str(out_file),
                        wait_for_url="/never",
                        timeout=1,
                    )
            assert out_file.exists()

    @pytest.mark.asyncio
    async def test_capture_keyboard_interrupt_branch(self):
        pw_cm, _, _ = _make_playwright_mock()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "state.json"
            with patch("playwright.async_api.async_playwright", return_value=pw_cm):
                with patch(
                    "crawler.capture.asyncio.sleep",
                    new_callable=AsyncMock,
                    side_effect=KeyboardInterrupt,
                ):
                    await capture_auth_state(
                        url="https://login.example.com",
                        output_path=str(out_file),
                        timeout=1,
                    )
            assert out_file.exists()


class TestCliBranches:
    def test_parse_crawl_args_capture_auth_branch(self):
        args = _parse_crawl_args(["capture-auth", "--url", "https://login.example.com"])
        assert args.capture_auth is True

    def test_write_output_json_remove_links_file_and_dir(self):
        doc = CrawledDocument(
            request_url="u",
            final_url="https://example.com",
            status="success",
            markdown="[Link](https://example.com/x)",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "one.json"
            _write_output([doc], str(out_file), True, remove_links=True)
            one = json.loads(out_file.read_text())
            assert "https://" not in one["markdown"]

            out_dir = Path(tmpdir) / "many"
            _write_output([doc, doc], str(out_dir) + "/", True, remove_links=True)
            many = json.loads((out_dir / "crawl_results.json").read_text())
            assert "https://" not in many[0]["markdown"]

    def test_build_cli_auth_resolves_profile_storage_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profile = Path(tmpdir)
            (profile / "storage_state.json").write_text("{}")
            args = argparse.Namespace(
                cookies=None,
                header=None,
                storage_state=None,
                auth_profile=str(profile),
            )
            cfg = _build_cli_auth(args)
            assert cfg is not None
            assert cfg.storage_state == str(profile / "storage_state.json")

    @pytest.mark.asyncio
    async def test_run_crawl_async_with_env_auth_logs_auth_enabled(self):
        doc = CrawledDocument(
            request_url="u", final_url="u", status="success", markdown="ok"
        )
        args = argparse.Namespace(
            urls=["https://example.com"],
            site=False,
            json_output=False,
            output=None,
            remove_links=False,
            verbose=False,
            concurrency=1,
        )
        with patch(
            "crawler.cli.load_auth_from_env", return_value=AuthConfig(storage_state="x")
        ):
            with patch(
                "crawler.crawl_page_async", new_callable=AsyncMock, return_value=doc
            ):
                assert await _run_crawl_async(args) == 0

    @pytest.mark.asyncio
    async def test_run_search_async_uses_basic_auth(self):
        args = argparse.Namespace(
            query="q",
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
        mock_response.json.return_value = {"query": "q", "results": []}
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.dict(
            "os.environ",
            {"SEARXNG_USERNAME": "user", "SEARXNG_PASSWORD": "pass"},
            clear=False,
        ):
            with patch(
                "crawler.search.httpx.AsyncClient", return_value=mock_client
            ) as ctor:
                assert await _run_search_async(args) == 0
                assert ctor.call_args.kwargs["auth"] is not None

    @pytest.mark.asyncio
    async def test_run_search_async_verbose_unexpected_error(self):
        args = argparse.Namespace(
            query="q",
            language="en",
            safesearch=1,
            time_range=None,
            categories=None,
            engines=None,
            max_results=10,
            pageno=1,
            json_output=False,
            output=None,
            verbose=True,
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("boom"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("crawler.search.httpx.AsyncClient", return_value=mock_client):
            with patch("crawler.cli.logging.exception") as mock_exc:
                assert await _run_search_async(args) == 1
                mock_exc.assert_called_once()

    def test_main_keyboardinterrupt_paths(self):
        with patch(
            "crawler.cli._parse_capture_auth_args",
            return_value=SimpleNamespace(verbose=False),
        ):
            with patch(
                "crawler.cli.asyncio.run",
                side_effect=_close_coro_and_raise(KeyboardInterrupt()),
            ):
                assert (
                    main(["capture-auth", "--url", "https://login.example.com"]) == 130
                )

        with patch(
            "crawler.cli._parse_crawl_args", return_value=SimpleNamespace(verbose=False)
        ):
            with patch(
                "crawler.cli.asyncio.run",
                side_effect=_close_coro_and_raise(KeyboardInterrupt()),
            ):
                assert main(["https://example.com"]) == 130

    def test_main_verbose_exception_logs_traceback(self):
        with patch(
            "crawler.cli._parse_crawl_args", return_value=SimpleNamespace(verbose=True)
        ):
            with patch(
                "crawler.cli.asyncio.run",
                side_effect=_close_coro_and_raise(Exception("boom")),
            ):
                with patch("crawler.cli.logging.exception") as mock_exc:
                    assert main(["https://example.com"]) == 1
                    mock_exc.assert_called_once()

    def test_search_main_keyboardinterrupt_and_verbose_exception(self):
        with patch(
            "crawler.cli._parse_search_args",
            return_value=SimpleNamespace(verbose=False),
        ):
            with patch(
                "crawler.cli.asyncio.run",
                side_effect=_close_coro_and_raise(KeyboardInterrupt()),
            ):
                assert search_main(["q"]) == 130

        with patch(
            "crawler.cli._parse_search_args", return_value=SimpleNamespace(verbose=True)
        ):
            with patch(
                "crawler.cli.asyncio.run",
                side_effect=_close_coro_and_raise(Exception("boom")),
            ):
                with patch("crawler.cli.logging.exception") as mock_exc:
                    assert search_main(["q"]) == 1
                    mock_exc.assert_called_once()

    def test_load_config_copy_and_copy_error_paths(self):
        from crawler.cli import _load_config

        with tempfile.TemporaryDirectory() as tmpdir:
            env_target = Path(tmpdir) / ".env"
            cfg_dir = Path(tmpdir) / "cfg"
            with patch("crawler.cli.Path.cwd", return_value=Path("/nonexistent")):
                with patch("crawler.cli.CONFIG_ENV_FILE", env_target):
                    with patch("crawler.cli.CONFIG_DIR", cfg_dir):
                        with patch("crawler.cli.load_dotenv") as mock_load:
                            _load_config()
                            assert env_target.exists()
                            mock_load.assert_called_once_with(env_target)

        with tempfile.TemporaryDirectory() as tmpdir:
            env_target = Path(tmpdir) / ".env"
            cfg_dir = Path(tmpdir) / "cfg"
            with patch("crawler.cli.Path.cwd", return_value=Path("/nonexistent")):
                with patch("crawler.cli.CONFIG_ENV_FILE", env_target):
                    with patch("crawler.cli.CONFIG_DIR", cfg_dir):
                        with patch("crawler.cli.shutil.copy", side_effect=OSError):
                            _load_config()
            assert not env_target.exists()

    def test_cli_module_main_guard(self):
        with patch("sys.exit") as mock_exit:
            with patch("asyncio.run", side_effect=_close_coro_and_return(0)):
                with patch(
                    "argparse.ArgumentParser.parse_args",
                    return_value=SimpleNamespace(verbose=False),
                ):
                    with patch("sys.argv", ["crawl", "https://example.com"]):
                        runpy.run_module("crawler.cli", run_name="__main__")
        mock_exit.assert_called_once_with(0)


class TestMcpBranches:
    def test_build_auth_config_resolves_profile_storage_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profile = Path(tmpdir)
            (profile / "storage_state.json").write_text("{}")
            cfg = _build_auth_config(auth_profile=str(profile))
            assert cfg is not None
            assert cfg.storage_state == str(profile / "storage_state.json")

    @pytest.mark.asyncio
    async def test_crawl_site_invalid_output_format_fallback(self):
        from crawler.mcp_server import crawl_site

        result = SiteCrawlResult(
            documents=[
                CrawledDocument(
                    request_url="u",
                    final_url="u",
                    status="success",
                    markdown="ok",
                )
            ],
            stats={"total_pages": 1, "successful_pages": 1, "failed_pages": 0},
        )
        with patch(
            "crawler.crawl_site_async", new_callable=AsyncMock, return_value=result
        ):
            output = await crawl_site(
                url="https://example.com", output_format="invalid"
            )
            assert "ok" in output

    def test_mcp_module_main_guard(self):
        with patch(
            "argparse.ArgumentParser.parse_args",
            return_value=SimpleNamespace(
                transport="stdio",
                host="127.0.0.1",
                port=8000,
            ),
        ):
            with patch("fastmcp.FastMCP.run") as mock_run:
                runpy.run_module("crawler.mcp_server", run_name="__main__")
        mock_run.assert_called_once_with(transport="stdio")


class TestReferencesBranches:
    def test_parse_markdown_block_value_error_branch(self):
        from crawler.references import _parse_markdown_block

        with patch(
            "crawler.references.int",
            side_effect=ValueError("bad-index"),
            create=True,
        ):
            refs = list(_parse_markdown_block("⟨1⟩ https://example.com: label"))
            assert refs == []


class TestSiteBranches:
    @pytest.mark.asyncio
    async def test_failed_document_adds_crawl_error_and_unknown(self):
        failed_doc = CrawledDocument(
            request_url="https://example.com",
            final_url="https://example.com",
            status="failed",
            markdown="",
            error_message=None,
        )
        item = MagicMock()
        item.url = "https://example.com"
        with patch("crawler.site.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_instance.arun = AsyncMock(return_value=[item])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance
            with patch(
                "crawler.site.build_document_from_result", return_value=failed_doc
            ):
                result = await crawl_site_async("https://example.com")
                assert result.errors[0]["stage"] == "crawl"
                assert result.errors[0]["error"] == "Unknown"

    @pytest.mark.asyncio
    async def test_max_pages_limit_branch(self):
        doc1 = CrawledDocument(
            request_url="https://example.com/a",
            final_url="https://example.com/a",
            status="success",
            markdown="a",
        )
        doc2 = CrawledDocument(
            request_url="https://example.com/b",
            final_url="https://example.com/b",
            status="success",
            markdown="b",
        )
        item1 = MagicMock()
        item1.url = "https://example.com/a"
        item2 = MagicMock()
        item2.url = "https://example.com/b"
        with patch("crawler.site.AsyncWebCrawler") as MockCrawler:
            mock_instance = AsyncMock()
            mock_instance.arun = AsyncMock(return_value=[item1, item2])
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_instance
            with patch(
                "crawler.site.build_document_from_result",
                side_effect=[doc1, doc2],
            ):
                result = await crawl_site_async("https://example.com", max_pages=1)
                assert result.stats["total_pages"] == 1

    @pytest.mark.asyncio
    async def test_iterate_results_container_paths(self):
        from crawl4ai.models import CrawlResultContainer

        sub = MagicMock()
        nested = MagicMock(spec=CrawlResultContainer)
        nested.__iter__.return_value = iter([sub])
        as_list = [item async for item in _iterate_results([nested])]
        assert as_list == [sub]

        root = MagicMock(spec=CrawlResultContainer)
        root.__iter__.return_value = iter([sub])
        as_root = [item async for item in _iterate_results(root)]
        assert as_root == [sub]

    @pytest.mark.asyncio
    async def test_iterate_results_async_generator_path(self):
        item = MagicMock()

        async def gen():
            yield item

        result = [x async for x in _iterate_results(gen())]
        assert result == [item]
