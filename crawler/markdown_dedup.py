"""Markdown deduplication helpers."""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Literal, Tuple

DedupMode = Literal["exact", "off"]


def dedup_markdown(
    markdown: str, mode: DedupMode = "exact"
) -> Tuple[str, Dict[str, int | str | bool]]:
    """Apply configured markdown dedup mode and return stats."""
    source = _normalize_line_endings(markdown or "")

    if mode == "off":
        sections = _split_sections(source)
        stats: Dict[str, int | str | bool] = {
            "dedup_mode": "off",
            "dedup_sections_total": len(sections),
            "dedup_sections_removed": 0,
            "dedup_chars_removed": 0,
            "dedup_applied": False,
        }
        return source, stats

    return dedup_markdown_exact(source)


def dedup_markdown_exact(markdown: str) -> Tuple[str, Dict[str, int | str | bool]]:
    """Remove exact normalized duplicate sections (first occurrence wins)."""
    source = _normalize_line_endings(markdown or "")
    sections = _split_sections(source)

    if not sections:
        empty_stats: Dict[str, int | str | bool] = {
            "dedup_mode": "exact",
            "dedup_sections_total": 0,
            "dedup_sections_removed": 0,
            "dedup_chars_removed": 0,
            "dedup_applied": False,
        }
        return "", empty_stats

    seen: set[str] = set()
    kept: List[str] = []
    removed_count = 0

    for section in sections:
        fingerprint = _fingerprint_section(section)
        if fingerprint in seen:
            removed_count += 1
            continue
        seen.add(fingerprint)
        kept.append(section)

    deduped = "\n\n".join(kept)
    chars_removed = max(0, len(source.strip()) - len(deduped))
    stats: Dict[str, int | str | bool] = {
        "dedup_mode": "exact",
        "dedup_sections_total": len(sections),
        "dedup_sections_removed": removed_count,
        "dedup_chars_removed": chars_removed,
        "dedup_applied": removed_count > 0,
    }
    return deduped, stats


def _split_sections(markdown: str) -> List[str]:
    text = _normalize_line_endings(markdown).strip()
    if not text:
        return []
    chunks = re.split(r"\n\s*\n+", text)

    sections: List[str] = []
    for chunk in chunks:
        chunk = _normalize_section(chunk)
        if not chunk:
            continue
        # Further split chunks that contain heading boundaries to avoid
        # preface-text + repeated heading block being treated as one section.
        subchunks = re.split(r"(?m)(?=^\s{0,3}#{1,6}\s+\S)", chunk)
        normalized_subchunks = [
            _normalize_section(sub) for sub in subchunks if sub and sub.strip()
        ]
        if normalized_subchunks:
            sections.extend(normalized_subchunks)
        else:
            sections.append(chunk)

    return sections


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _normalize_section(section: str) -> str:
    lines = [line.rstrip() for line in _normalize_line_endings(section).split("\n")]
    normalized = "\n".join(lines).strip()
    return normalized


def _fingerprint_section(section: str) -> str:
    normalized = _normalize_section(section)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
