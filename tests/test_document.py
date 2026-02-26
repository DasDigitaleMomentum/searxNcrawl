"""Tests for crawler.document module."""

from crawler.document import CrawledDocument, Reference


class TestReference:
    def test_reference_creation(self):
        ref = Reference(index=1, href="https://example.com", label="Example")
        assert ref.index == 1
        assert ref.href == "https://example.com"
        assert ref.label == "Example"


class TestCrawledDocument:
    def test_required_fields(self):
        doc = CrawledDocument(
            request_url="https://example.com",
            final_url="https://example.com",
            status="success",
            markdown="# Hello",
        )
        assert doc.request_url == "https://example.com"
        assert doc.final_url == "https://example.com"
        assert doc.status == "success"
        assert doc.markdown == "# Hello"

    def test_optional_fields_defaults(self):
        doc = CrawledDocument(
            request_url="u", final_url="u", status="s", markdown="m"
        )
        assert doc.html is None
        assert doc.headers == {}
        assert doc.references == []
        assert doc.metadata == {}
        assert doc.raw_markdown is None
        assert doc.error_message is None

    def test_failed_document(self):
        doc = CrawledDocument(
            request_url="u",
            final_url="u",
            status="failed",
            markdown="",
            error_message="HTTP 404",
        )
        assert doc.error_message == "HTTP 404"

    def test_with_references(self):
        refs = [Reference(index=1, href="a", label="A")]
        doc = CrawledDocument(
            request_url="u",
            final_url="u",
            status="success",
            markdown="m",
            references=refs,
        )
        assert len(doc.references) == 1
        assert doc.references[0].label == "A"
