"""Data structures representing crawled documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class Reference:
    """Outgoing link reference collected during a crawl."""

    index: int
    href: str
    label: str


@dataclass(slots=True)
class CrawledDocument:
    """Container for the raw crawl output and associated metadata."""

    request_url: str
    final_url: str
    status: str  # success, failed, redirected
    markdown: str
    html: Optional[str] = None
    headers: Dict[str, Any] = field(default_factory=dict)
    references: List[Reference] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_markdown: Optional[str] = None
    error_message: Optional[str] = None
