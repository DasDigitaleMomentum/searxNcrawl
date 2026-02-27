"""Tests for crawler.builder module."""

from __future__ import annotations

from unittest.mock import MagicMock

from crawl4ai.models import CrawlResult, MarkdownGenerationResult

from crawler.builder import (
    _derive_failure_reason,
    _ensure_markdown,
    _extract_requested_url,
    _prepare_metadata,
    build_document_from_result,
)


def _make_result(**kwargs) -> CrawlResult:
    """Create a minimal CrawlResult mock."""
    result = MagicMock(spec=CrawlResult)
    result.url = kwargs.get("url", "https://example.com")
    result.success = kwargs.get("success", True)
    result.html = kwargs.get("html", "<h1>Hello</h1>")
    result.cleaned_html = kwargs.get("cleaned_html", None)
    result.error_message = kwargs.get("error_message", None)
    result.status_code = kwargs.get("status_code", 200)
    result.response_headers = kwargs.get("response_headers", {})
    result.metadata = kwargs.get("metadata", {"requested_url": "https://example.com"})
    result.links = kwargs.get("links", {})

    md = kwargs.get("markdown", None)
    if md is None:
        md = MagicMock(spec=MarkdownGenerationResult)
        md.fit_markdown = kwargs.get("fit_markdown", "# Hello")
        md.raw_markdown = kwargs.get("raw_markdown", "# Hello Raw")
        md.markdown_with_citations = kwargs.get("citations_markdown", "")
        md.references_markdown = kwargs.get("references_markdown", "")
    result.markdown = md

    return result


class TestBuildDocumentFromResult:
    def test_success(self):
        result = _make_result()
        doc = build_document_from_result(result)
        assert doc.status == "success"
        assert doc.request_url == "https://example.com"
        assert doc.final_url == "https://example.com"
        assert doc.markdown != ""

    def test_failure(self):
        result = _make_result(
            success=False,
            error_message="Connection timeout",
        )
        doc = build_document_from_result(result)
        assert doc.status == "failed"
        assert doc.error_message == "Connection timeout"

    def test_success_with_references(self):
        result = _make_result(
            references_markdown="⟨1⟩ https://test.com: Test",
        )
        result.markdown.references_markdown = "⟨1⟩ https://test.com: Test"
        doc = build_document_from_result(result)
        assert doc.status == "success"

    def test_success_fit_markdown_empty_uses_raw(self):
        result = _make_result(
            fit_markdown="",
            raw_markdown="# Raw Content",
            citations_markdown="",
        )
        doc = build_document_from_result(result)
        assert doc.status == "success"
        assert "Raw Content" in doc.markdown


class TestPrepareMetadata:
    def test_basic_metadata(self):
        result = _make_result()
        meta = _prepare_metadata(result, "", "")
        assert "requested_url" in meta
        assert "resolved_url" in meta

    def test_with_markdown_lengths(self):
        result = _make_result()
        meta = _prepare_metadata(result, "raw content", "fit content")
        assert meta.get("raw_markdown_length") == 11
        assert meta.get("fit_markdown_length") == 11

    def test_resolved_url_differs(self):
        result = _make_result(
            metadata={"requested_url": "https://old.com"},
            url="https://new.com",
        )
        meta = _prepare_metadata(result, "", "")
        assert meta["resolved_url"] == "https://new.com"


class TestDeriveFailureReason:
    def test_error_message(self):
        result = _make_result(error_message="Test error")
        assert _derive_failure_reason(result) == "Test error"

    def test_status_code(self):
        result = _make_result(error_message=None, status_code=404)
        assert _derive_failure_reason(result) == "HTTP 404"

    def test_crawl_error_from_metadata(self):
        result = _make_result(
            error_message=None,
            status_code=None,
            metadata={"crawl_last_error": "DNS failed"},
        )
        assert _derive_failure_reason(result) == "DNS failed"

    def test_crawl_error_fallback(self):
        result = _make_result(
            error_message=None,
            status_code=None,
            metadata={"crawl_error": "Network issue"},
        )
        assert _derive_failure_reason(result) == "Network issue"

    def test_requested_url_in_metadata(self):
        result = _make_result(
            error_message=None,
            status_code=None,
            metadata={"requested_url": "https://fail.com"},
        )
        reason = _derive_failure_reason(result)
        assert "fail.com" in reason

    def test_generic_fallback(self):
        result = _make_result(
            error_message=None,
            status_code=None,
            metadata={},
        )
        assert _derive_failure_reason(result) == "Crawler returned no content"


class TestEnsureMarkdown:
    def test_existing_markdown_returned(self):
        result = _make_result(raw_markdown="# Existing")
        md = _ensure_markdown(result)
        assert md is not None

    def test_empty_markdown_regenerates(self):
        result = _make_result()
        result.markdown.fit_markdown = ""
        result.markdown.raw_markdown = ""
        result.markdown.markdown_with_citations = ""
        result.html = "<h1>Test</h1>"
        md = _ensure_markdown(result)
        assert md is not None

    def test_no_html_returns_empty(self):
        result = _make_result()
        result.markdown.fit_markdown = ""
        result.markdown.raw_markdown = ""
        result.markdown.markdown_with_citations = ""
        result.html = None
        result.cleaned_html = None
        md = _ensure_markdown(result)
        assert md.raw_markdown == ""


class TestExtractRequestedUrl:
    def test_from_requested_url(self):
        assert _extract_requested_url(
            {"requested_url": "https://a.com"}, "default"
        ) == "https://a.com"

    def test_from_request_url(self):
        assert _extract_requested_url(
            {"request_url": "https://b.com"}, "default"
        ) == "https://b.com"

    def test_from_source_url(self):
        assert _extract_requested_url(
            {"source_url": "https://c.com"}, "default"
        ) == "https://c.com"

    def test_fallback_to_default(self):
        assert _extract_requested_url({}, "https://default.com") == "https://default.com"

    def test_fallback_none_default(self):
        assert _extract_requested_url({}, None) == ""

    def test_ignores_empty_strings(self):
        assert _extract_requested_url(
            {"requested_url": "  ", "request_url": "https://ok.com"}, "default"
        ) == "https://ok.com"
