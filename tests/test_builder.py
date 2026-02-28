from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from crawler.builder import build_document_from_result


def _crawl_result(markdown: str) -> Any:
    markdown_result = SimpleNamespace(
        fit_markdown="",
        raw_markdown=markdown,
        markdown_with_citations="",
        references_markdown="",
    )
    return SimpleNamespace(
        success=True,
        url="https://example.com/page",
        html="<html></html>",
        cleaned_html=None,
        response_headers={"content-type": "text/html"},
        status_code=200,
        error_message=None,
        links={"internal": [], "external": []},
        metadata={"requested_url": "https://example.com/page", "title": "Example"},
        markdown=markdown_result,
    )


def test_builder_guardrail_triggers_for_high_removal_rate() -> None:
    raw = """A

A

A

B"""

    doc = build_document_from_result(_crawl_result(raw), dedup_mode="exact")

    assert doc.status == "success"
    assert doc.metadata["dedup_guardrail_checked"] is True
    assert doc.metadata["dedup_guardrail_triggered"] is True
    assert doc.metadata["dedup_guardrail_reason"] == "high-removal-rate"
    assert doc.metadata["dedup_guardrail_section_removal_rate"] == 0.5


def test_builder_guardrail_does_not_trigger_within_threshold() -> None:
    raw = """A

B

C

A

D

E"""

    doc = build_document_from_result(_crawl_result(raw), dedup_mode="exact")

    assert doc.status == "success"
    assert doc.metadata["dedup_guardrail_checked"] is True
    assert doc.metadata["dedup_guardrail_triggered"] is False
    assert doc.metadata["dedup_guardrail_reason"] == "within-threshold"


def test_builder_guardrail_disabled_when_dedup_mode_off() -> None:
    raw = """A

A

A

B"""

    doc = build_document_from_result(_crawl_result(raw), dedup_mode="off")

    assert doc.status == "success"
    assert doc.metadata["dedup_guardrail_checked"] is False
    assert doc.metadata["dedup_guardrail_triggered"] is False
    assert doc.metadata["dedup_guardrail_reason"] == "dedup-inactive"
