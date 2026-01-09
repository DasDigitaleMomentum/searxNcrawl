"""Factory functions for Crawl4AI run configurations."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from crawl4ai import CrawlerRunConfig
from crawl4ai.async_configs import CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

LOGGER = logging.getLogger(__name__)

# Selectors for main content areas (documentation sites, articles, etc.)
MAIN_SELECTORS: List[str] = [
    "main",
    "[role='main']",
    "article",
    ".content",
    ".main-content",
    ".markdown-body",
    ".docs-content",
    ".doc-content",
    ".prose",
    ".md-content",
    "#content-area",
    "[data-docs-content]",
    "[data-content]",
]

# Selectors for elements to exclude (navigation, footers, sidebars, cookie banners)
EXCLUDED_SELECTORS: List[str] = [
    "nav",
    "footer",
    "header",
    "aside",
    "#navbar",
    "#onetrust-banner-sdk",
    ".toc",
    ".table-of-contents",
    ".breadcrumbs",
    ".sidebar",
    "[class*='sidebar']",
    "[class*='nav']",
    "[role='navigation']",
    "[data-testid='breadcrumbs']",
    ".cky-consent-container",
    ".cky-preference-center",
    ".cky-overlay",
    ".cky-modal",
    ".cky-consent-bar",
    ".cky-notice",
]


@dataclass
class RunConfigOverrides:
    """Optional crawl-run overrides."""

    verbose: Optional[bool] = None
    semaphore_count: Optional[int] = None
    wait_until: Optional[str] = None
    delay_before_return_html: Optional[float] = None
    mean_delay: Optional[float] = None
    max_range: Optional[float] = None
    magic: Optional[bool] = None
    cache_mode: Optional[str] = None
    css_selector: Optional[str] = None
    target_elements: List[str] = field(default_factory=list)
    excluded_tags: List[str] = field(default_factory=list)
    excluded_selector: Optional[str] = None
    scan_full_page: Optional[bool] = None
    js_code: Optional[str] = None
    wait_for: Optional[str] = None
    ignore_body_visibility: Optional[bool] = None
    stream: Optional[bool] = None
    exclude_external_links: Optional[bool] = None


def _convert_cache_mode(value: Optional[str], default: CacheMode) -> CacheMode:
    if not value:
        return default
    candidate = value.strip().replace("CacheMode.", "")
    try:
        return CacheMode[candidate.upper()]
    except KeyError:
        pass
    try:
        return CacheMode(candidate.lower())
    except ValueError:
        LOGGER.warning(
            "Unknown cache_mode '%s'; falling back to %s.", value, default.name
        )
        return default


def _apply_overrides(config: CrawlerRunConfig, overrides: RunConfigOverrides) -> None:
    """Apply optional overrides to a CrawlerRunConfig."""
    if overrides.verbose is not None:
        config.verbose = overrides.verbose
    if overrides.semaphore_count is not None:
        config.semaphore_count = overrides.semaphore_count
    if overrides.wait_until is not None:
        config.wait_until = overrides.wait_until
    if overrides.delay_before_return_html is not None:
        config.delay_before_return_html = overrides.delay_before_return_html
    if overrides.mean_delay is not None:
        config.mean_delay = overrides.mean_delay
    if overrides.max_range is not None:
        config.max_range = overrides.max_range
    if overrides.magic is not None:
        config.magic = overrides.magic
    if overrides.cache_mode:
        config.cache_mode = _convert_cache_mode(overrides.cache_mode, config.cache_mode)
    if overrides.css_selector:
        config.css_selector = overrides.css_selector
    if overrides.target_elements:
        config.target_elements = list(overrides.target_elements)
    if overrides.excluded_tags:
        config.excluded_tags = list(overrides.excluded_tags)
    if overrides.excluded_selector:
        config.excluded_selector = overrides.excluded_selector
    if overrides.scan_full_page is not None:
        config.scan_full_page = overrides.scan_full_page
    if overrides.js_code:
        config.js_code = overrides.js_code
    if overrides.wait_for:
        config.wait_for = overrides.wait_for
    if overrides.ignore_body_visibility is not None:
        config.ignore_body_visibility = overrides.ignore_body_visibility
    if overrides.stream is not None:
        config.stream = overrides.stream
    if overrides.exclude_external_links is not None:
        config.exclude_external_links = overrides.exclude_external_links


def build_markdown_generator() -> DefaultMarkdownGenerator:
    """Markdown generator tuned for documentation pages."""
    prune_filter = PruningContentFilter(
        threshold=0.45,
        threshold_type="dynamic",
        min_word_threshold=1,
    )
    return DefaultMarkdownGenerator(
        content_filter=prune_filter,
        options={
            "citations": False,
            "body_width": 0,
            "skip_internal_links": True,
            "ignore_images": True,
        },
    )


def build_markdown_run_config(
    overrides: Optional[RunConfigOverrides] = None,
) -> CrawlerRunConfig:
    """RunConfig for single-page crawls, optimized for main content extraction."""
    generator = build_markdown_generator()
    config = CrawlerRunConfig(
        verbose=True,
        semaphore_count=1,
        delay_before_return_html=0.5,
        mean_delay=0.5,
        max_range=0.3,
        target_elements=list(MAIN_SELECTORS),
        excluded_tags=["nav", "footer", "header", "aside", "form", "sidebar"],
        excluded_selector=", ".join(EXCLUDED_SELECTORS),
        markdown_generator=generator,
        cache_mode=CacheMode.BYPASS,
        scan_full_page=True,
        js_code="""
            window.location.reload();
            setTimeout(() => window.scrollTo(0, document.body.scrollHeight), 500);
        """,
        wait_for="js:() => document.querySelector('main') && document.querySelector('main').innerText.trim().length > 50",
    )
    if overrides:
        _apply_overrides(config, overrides)
    return config


def build_discovery_run_config(
    overrides: Optional[RunConfigOverrides] = None,
) -> CrawlerRunConfig:
    """Configuration focused on link discovery for site crawling."""
    generator = build_markdown_generator()
    config = CrawlerRunConfig(
        verbose=True,
        semaphore_count=1,
        wait_until="networkidle",
        delay_before_return_html=2.0,
        mean_delay=2.0,
        max_range=0.3,
        magic=True,
        cache_mode=CacheMode.BYPASS,
        markdown_generator=generator,
        css_selector=", ".join(MAIN_SELECTORS),
        target_elements=list(MAIN_SELECTORS),
        excluded_tags=["nav", "footer", "header", "aside", "form"],
        excluded_selector=", ".join(EXCLUDED_SELECTORS),
        ignore_body_visibility=False,
    )
    if overrides:
        _apply_overrides(config, overrides)
    return config
