"""Helpers for parsing references from Crawl4AI results."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .document import Reference

REFERENCE_LINE = re.compile(r"^⟨(?P<index>\d+)⟩\s*(?P<tail>.+)$")


def parse_references(
    references_markdown: str,
    links: Optional[Dict[str, List[Dict[str, Any]]]],
) -> List[Reference]:
    """Build reference objects from markdown or the fallback link metadata."""
    parsed = list(_parse_markdown_block(references_markdown or ""))
    if parsed:
        return parsed
    return list(_build_from_links(links or {}))


def _parse_markdown_block(markdown_block: str) -> Iterable[Reference]:
    for raw_line in markdown_block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = REFERENCE_LINE.match(line)
        if not match:
            continue
        rest = match.group("tail").strip()
        href, label = _split_reference_tail(rest)
        try:
            yield Reference(index=int(match.group("index")), href=href, label=label)
        except ValueError:
            continue


def _build_from_links(links: Dict[str, List[Dict[str, Any]]]) -> Iterable[Reference]:
    seen: set[Tuple[str, str]] = set()
    merged: List[Tuple[str, str]] = []
    for bucket in ("internal", "external"):
        for entry in links.get(bucket, []) or []:
            href = (entry or {}).get("href")
            if not href:
                continue
            label = ((entry or {}).get("text") or href).strip()
            key = (href, label)
            if key in seen:
                continue
            seen.add(key)
            merged.append(key)
    for index, (href, label) in enumerate(merged, start=1):
        yield Reference(index=index, href=href, label=label)


def _split_reference_tail(rest: str) -> Tuple[str, str]:
    if ": " in rest:
        href, _, label = rest.partition(": ")
        return href.strip(), label.strip()
    return rest.strip(), ""
