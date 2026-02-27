"""Output and formatting helpers for CLI commands."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .document import CrawledDocument


def strip_markdown_links(text: str) -> str:
    """Remove markdown links from text, keeping only the link text."""
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'  +', ' ', text)
    return text


def format_search_markdown(data: Dict[str, Any]) -> str:
    """Format search results as markdown."""
    lines = []
    query = data.get("query", "")
    results = data.get("results", [])

    lines.append(f"# Search: {query}")
    lines.append(f"_Found {len(results)} results_")
    lines.append("")

    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = result.get("content", "")

        lines.append(f"## {i}. {title}")
        lines.append(url)
        lines.append("")
        if content:
            lines.append(content)
            lines.append("")
        lines.append("---")
        lines.append("")

    suggestions = data.get("suggestions", [])
    if suggestions:
        lines.append("**Related searches:** " + ", ".join(suggestions[:5]))
        lines.append("")

    return "\n".join(lines)


def doc_to_dict(doc: CrawledDocument) -> dict:
    """Convert document to JSON-serializable dict."""
    return {
        "request_url": doc.request_url,
        "final_url": doc.final_url,
        "status": doc.status,
        "markdown": doc.markdown,
        "error_message": doc.error_message,
        "metadata": doc.metadata,
        "references": [
            {"index": ref.index, "href": ref.href, "label": ref.label}
            for ref in doc.references
        ],
    }


def url_to_filename(url: str) -> str:
    """Convert URL to a safe filename."""
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_") or "index"
    host = parsed.netloc.replace(":", "_").replace(".", "_")
    return f"{host}_{path}"[:100]


def write_output(
    docs: List[CrawledDocument],
    output: Optional[str],
    json_output: bool,
    remove_links: bool = False,
) -> None:
    """Write documents to output destination."""
    if remove_links and not json_output:
        for doc in docs:
            doc.markdown = strip_markdown_links(doc.markdown)

    if len(docs) == 1 and output is None:
        doc = docs[0]
        if json_output:
            doc_dict = doc_to_dict(doc)
            if remove_links and doc_dict.get("markdown"):
                doc_dict["markdown"] = strip_markdown_links(doc_dict["markdown"])
            print(json.dumps(doc_dict, indent=2, ensure_ascii=False))
        else:
            print(doc.markdown)
        return

    if len(docs) == 1 and output and not output.endswith("/"):
        doc = docs[0]
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        if json_output:
            doc_dict = doc_to_dict(doc)
            if remove_links and doc_dict.get("markdown"):
                doc_dict["markdown"] = strip_markdown_links(doc_dict["markdown"])
            path.write_text(json.dumps(doc_dict, indent=2, ensure_ascii=False))
        else:
            path.write_text(doc.markdown)
        logging.info("Wrote %s", path)
        return

    out_dir = Path(output) if output else Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)

    if json_output:
        all_docs = []
        for doc in docs:
            doc_dict = doc_to_dict(doc)
            if remove_links and doc_dict.get("markdown"):
                doc_dict["markdown"] = strip_markdown_links(doc_dict["markdown"])
            all_docs.append(doc_dict)
        out_path = out_dir / "crawl_results.json"
        out_path.write_text(json.dumps(all_docs, indent=2, ensure_ascii=False))
        logging.info("Wrote %d documents to %s", len(docs), out_path)
    else:
        for doc in docs:
            filename = url_to_filename(doc.final_url) + ".md"
            path = out_dir / filename
            path.write_text(doc.markdown)
            logging.info("Wrote %s", path)
