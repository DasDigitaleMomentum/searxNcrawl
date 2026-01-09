"""Translate Crawl4AI results into CrawledDocument instances."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from crawl4ai.models import CrawlResult, MarkdownGenerationResult

from .config import build_markdown_generator
from .document import CrawledDocument
from .references import parse_references


def build_document_from_result(result: CrawlResult) -> CrawledDocument:
    """Convert a Crawl4AI CrawlResult into our internal representation."""

    # Prepare metadata first to get URLs
    metadata = _prepare_metadata(result, "", "")
    request_url = metadata["requested_url"]
    final_url = str(result.url or request_url)

    html = result.html or result.cleaned_html or None
    headers = result.response_headers or {}

    # Handle failure
    if not result.success:
        failure_reason = _derive_failure_reason(result)
        return CrawledDocument(
            request_url=request_url,
            final_url=final_url,
            status="failed",
            error_message=failure_reason,
            markdown="",
            html=html,
            headers=headers,
            metadata=metadata,
        )

    # Handle success
    markdown = _ensure_markdown(result)

    fit_candidate = getattr(markdown, "fit_markdown", None) or ""
    fit_markdown = fit_candidate if fit_candidate.strip() else ""
    raw_markdown = markdown.raw_markdown or ""
    citations_markdown = markdown.markdown_with_citations or ""
    primary_markdown = (
        fit_markdown
        or (citations_markdown if citations_markdown.strip() else "")
        or raw_markdown
    )
    if not raw_markdown:
        raw_markdown = primary_markdown
    if not primary_markdown.strip():
        primary_markdown = raw_markdown
    cleaned_markdown = primary_markdown

    # Update metadata with stats
    metadata.update(_prepare_metadata(result, raw_markdown, fit_markdown))
    references = parse_references(markdown.references_markdown or "", result.links)

    return CrawledDocument(
        request_url=request_url,
        final_url=final_url,
        status="success",
        markdown=cleaned_markdown,
        raw_markdown=raw_markdown,
        html=html,
        headers=headers,
        references=references,
        metadata=metadata,
    )


def _prepare_metadata(
    result: CrawlResult, raw_markdown: str, fit_markdown: str
) -> Dict[str, Any]:
    source_metadata = deepcopy(result.metadata or {})

    requested_url = _extract_requested_url(source_metadata, result.url)
    resolved_url = str(result.url or requested_url)

    metadata: Dict[str, Any] = source_metadata
    metadata.setdefault("status_code", result.status_code)
    metadata["requested_url"] = requested_url
    metadata["resolved_url"] = resolved_url
    metadata["source_url"] = requested_url
    if resolved_url and resolved_url != requested_url:
        metadata.setdefault("resolved_source_url", resolved_url)
    metadata.setdefault("title_original", metadata.get("title"))
    metadata.setdefault("title_clean", metadata.get("title"))

    if raw_markdown:
        metadata.setdefault("raw_markdown_length", len(raw_markdown))
    if fit_markdown:
        metadata.setdefault("fit_markdown_length", len(fit_markdown))

    return metadata


def _derive_failure_reason(result: CrawlResult) -> str:
    if result.error_message:
        return result.error_message
    metadata = result.metadata or {}
    status_code = result.status_code or metadata.get("status_code")
    if status_code:
        return f"HTTP {status_code}"
    crawl_error = metadata.get("crawl_last_error") or metadata.get("crawl_error")
    if crawl_error:
        return str(crawl_error)
    if metadata.get("requested_url"):
        return f"Crawler returned no content for {metadata['requested_url']}"
    return "Crawler returned no content"


def _ensure_markdown(result: CrawlResult) -> MarkdownGenerationResult:
    existing = getattr(result, "markdown", None)
    if existing:
        existing_fit = getattr(existing, "fit_markdown", "") or ""
        existing_raw = getattr(existing, "raw_markdown", "") or ""
        existing_citations = getattr(existing, "markdown_with_citations", "") or ""
        if existing_fit.strip() or existing_raw.strip() or existing_citations.strip():
            return existing

    generator = build_markdown_generator()
    html_source = result.html or result.cleaned_html or ""
    if html_source:
        generated = generator.generate_markdown(
            html_source,
            base_url=str(result.url or ""),
            options=generator.options,
            content_filter=generator.content_filter,
            citations=False,
        )
        generated_fit = getattr(generated, "fit_markdown", "") or ""
        generated_raw = getattr(generated, "raw_markdown", "") or ""
        generated_citations = getattr(generated, "markdown_with_citations", "") or ""
        if (
            generated_fit.strip()
            or generated_raw.strip()
            or generated_citations.strip()
        ):
            return generated

    return MarkdownGenerationResult(
        raw_markdown="",
        markdown_with_citations="",
        references_markdown="",
        fit_markdown="",
        fit_html="",
    )


def _extract_requested_url(metadata: Dict[str, Any], default: Optional[str]) -> str:
    for key in ("requested_url", "request_url", "source_url"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(default or "")
