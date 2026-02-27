"""Tests for crawler.references module."""

from crawler.references import parse_references, _parse_markdown_block, _build_from_links, _split_reference_tail


class TestParseReferences:
    def test_empty_inputs(self):
        result = parse_references("", None)
        assert result == []

    def test_markdown_block_parsing(self):
        md = "⟨1⟩ https://example.com: Example Site\n⟨2⟩ https://other.com: Other"
        result = parse_references(md, None)
        assert len(result) == 2
        assert result[0].index == 1
        assert result[0].href == "https://example.com"
        assert result[0].label == "Example Site"
        assert result[1].index == 2

    def test_fallback_to_links(self):
        links = {
            "internal": [
                {"href": "https://a.com", "text": "A"},
            ],
            "external": [
                {"href": "https://b.com", "text": "B"},
            ],
        }
        result = parse_references("", links)
        assert len(result) == 2
        assert result[0].index == 1
        assert result[0].href == "https://a.com"
        assert result[1].href == "https://b.com"

    def test_markdown_takes_precedence_over_links(self):
        md = "⟨1⟩ https://example.com: Site"
        links = {"internal": [{"href": "https://other.com", "text": "Other"}]}
        result = parse_references(md, links)
        assert len(result) == 1
        assert result[0].href == "https://example.com"


class TestParseMarkdownBlock:
    def test_empty_string(self):
        assert list(_parse_markdown_block("")) == []

    def test_blank_lines_skipped(self):
        assert list(_parse_markdown_block("\n\n\n")) == []

    def test_non_matching_lines_skipped(self):
        assert list(_parse_markdown_block("Some random text")) == []

    def test_valid_reference_line(self):
        refs = list(_parse_markdown_block("⟨42⟩ https://test.com: Test"))
        assert len(refs) == 1
        assert refs[0].index == 42
        assert refs[0].href == "https://test.com"
        assert refs[0].label == "Test"

    def test_href_only_no_label(self):
        refs = list(_parse_markdown_block("⟨1⟩ https://example.com"))
        assert len(refs) == 1
        assert refs[0].href == "https://example.com"
        assert refs[0].label == ""


class TestBuildFromLinks:
    def test_empty_links(self):
        assert list(_build_from_links({})) == []

    def test_deduplication(self):
        links = {
            "internal": [
                {"href": "https://a.com", "text": "A"},
                {"href": "https://a.com", "text": "A"},
            ],
        }
        result = list(_build_from_links(links))
        assert len(result) == 1

    def test_skips_empty_href(self):
        links = {
            "internal": [
                {"href": "", "text": "Empty"},
                {"href": None, "text": "None"},
                {"text": "Missing"},
                None,
            ],
        }
        result = list(_build_from_links(links))
        assert len(result) == 0

    def test_uses_href_as_label_when_text_missing(self):
        links = {
            "internal": [{"href": "https://a.com"}],
        }
        result = list(_build_from_links(links))
        assert result[0].label == "https://a.com"

    def test_none_bucket(self):
        links = {"internal": None}
        result = list(_build_from_links(links))
        assert result == []


class TestSplitReferenceTail:
    def test_with_colon_separator(self):
        href, label = _split_reference_tail("https://example.com: My Label")
        assert href == "https://example.com"
        assert label == "My Label"

    def test_without_colon(self):
        href, label = _split_reference_tail("https://example.com")
        assert href == "https://example.com"
        assert label == ""
