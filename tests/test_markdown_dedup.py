from __future__ import annotations

from typing import Any
from types import SimpleNamespace

from crawler.builder import build_document_from_result
from crawler.markdown_dedup import dedup_markdown, dedup_markdown_exact


def test_exact_dedup_removes_duplicate_sections_first_wins() -> None:
    markdown = """# Intro

Alpha details.

## Setup

Install package.

Alpha details.

## Setup

Install package.

## Usage

Run command."""

    deduped, stats = dedup_markdown_exact(markdown)

    assert (
        deduped
        == """# Intro

Alpha details.

## Setup

Install package.

## Usage

Run command."""
    )
    assert stats["dedup_mode"] == "exact"
    assert stats["dedup_sections_total"] == 9
    assert stats["dedup_sections_removed"] == 3
    assert stats["dedup_applied"] is True
    chars_removed = stats["dedup_chars_removed"]
    assert isinstance(chars_removed, int)
    assert chars_removed > 0


def test_unique_content_is_preserved_with_neutral_normalization() -> None:
    markdown = """# One  

Line with space.   

## Two

Another line."""

    deduped, stats = dedup_markdown_exact(markdown)

    assert (
        deduped
        == """# One

Line with space.

## Two

Another line."""
    )
    assert stats["dedup_sections_removed"] == 0
    assert stats["dedup_applied"] is False


def test_dedup_is_idempotent() -> None:
    markdown = """Section A

Section B

Section A"""

    once, _ = dedup_markdown_exact(markdown)
    twice, _ = dedup_markdown_exact(once)

    assert twice == once


def test_agno_like_repeated_core_sections_regression_fixture() -> None:
    markdown = """# Introduction

Agno is an agent framework for reliable workflows.

## Why Agno

Use deterministic building blocks for production systems.

## Quickstart

Install and run your first agent.

## Why Agno

Use deterministic building blocks for production systems.

## Quickstart

Install and run your first agent.

## Next Steps

Read deployment guidance."""

    deduped, stats = dedup_markdown_exact(markdown)

    assert deduped.count("## Why Agno") == 1
    assert deduped.count("## Quickstart") == 1
    assert deduped.count("## Next Steps") == 1
    assert stats["dedup_sections_removed"] == 4


def test_exact_dedup_handles_preface_before_repeated_heading_block() -> None:
    markdown = """# Intro

Lead paragraph.

## What is Agno

Agno helps build production agents.

## What You Can Build

Assistants, automations, and workflows.

You own the system. You own the data. You define the rules.
## What is Agno

Agno helps build production agents.

## What You Can Build

Assistants, automations, and workflows.
"""

    deduped, stats = dedup_markdown_exact(markdown)

    assert deduped.count("## What is Agno") == 1
    assert deduped.count("## What You Can Build") == 1
    assert "You own the system. You own the data. You define the rules." in deduped
    removed = stats["dedup_sections_removed"]
    assert isinstance(removed, int)
    assert removed >= 2


def test_dedup_mode_off_preserves_duplicate_content() -> None:
    markdown = """# Intro

Repeat me.

Repeat me.
"""

    out, stats = dedup_markdown(markdown, mode="off")

    assert out == markdown
    assert stats["dedup_mode"] == "off"
    assert stats["dedup_sections_removed"] == 0
    assert stats["dedup_applied"] is False


def test_builder_integration_applies_dedup_and_emits_metadata() -> None:
    raw = """# Title

Core paragraph.

Core paragraph.

Closing paragraph."""
    markdown_result = SimpleNamespace(
        fit_markdown="",
        raw_markdown=raw,
        markdown_with_citations="",
        references_markdown="",
    )
    crawl_result: Any = SimpleNamespace(
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

    doc = build_document_from_result(crawl_result)

    assert doc.status == "success"
    assert doc.raw_markdown == raw
    assert (
        doc.markdown
        == """# Title

Core paragraph.

Closing paragraph."""
    )
    assert doc.metadata["dedup_mode"] == "exact"
    assert doc.metadata["dedup_sections_total"] == 4
    assert doc.metadata["dedup_sections_removed"] == 1
    assert doc.metadata["dedup_applied"] is True
    assert isinstance(doc.metadata["dedup_chars_removed"], int)


def test_builder_integration_supports_dedup_off_mode() -> None:
    raw = """# Title

Core paragraph.

Core paragraph.

Closing paragraph."""
    markdown_result = SimpleNamespace(
        fit_markdown="",
        raw_markdown=raw,
        markdown_with_citations="",
        references_markdown="",
    )
    crawl_result: Any = SimpleNamespace(
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

    doc = build_document_from_result(crawl_result, dedup_mode="off")

    assert doc.status == "success"
    assert doc.markdown == raw
    assert doc.metadata["dedup_mode"] == "off"
    assert doc.metadata["dedup_sections_removed"] == 0
    assert doc.metadata["dedup_applied"] is False
