"""Tests for crawler.config module."""

from crawl4ai import CrawlerRunConfig
from crawl4ai.async_configs import CacheMode

from crawler.config import (
    AGGRESSIVE_SPA_WAIT_FOR,
    EXCLUDED_SELECTORS,
    MAIN_SELECTORS,
    RunConfigOverrides,
    _apply_overrides,
    _convert_cache_mode,
    build_discovery_run_config,
    build_markdown_generator,
    build_markdown_run_config,
)


class TestRunConfigOverrides:
    def test_defaults(self):
        o = RunConfigOverrides()
        assert o.verbose is None
        assert o.target_elements == []
        assert o.excluded_tags == []

    def test_with_values(self):
        o = RunConfigOverrides(verbose=True, semaphore_count=5)
        assert o.verbose is True
        assert o.semaphore_count == 5


class TestConvertCacheMode:
    def test_none_returns_default(self):
        assert _convert_cache_mode(None, CacheMode.BYPASS) == CacheMode.BYPASS

    def test_empty_returns_default(self):
        assert _convert_cache_mode("", CacheMode.BYPASS) == CacheMode.BYPASS

    def test_name_lookup(self):
        assert _convert_cache_mode("BYPASS", CacheMode.ENABLED) == CacheMode.BYPASS

    def test_value_lookup(self):
        result = _convert_cache_mode("bypass", CacheMode.ENABLED)
        assert result == CacheMode.BYPASS

    def test_with_prefix(self):
        result = _convert_cache_mode("CacheMode.BYPASS", CacheMode.ENABLED)
        assert result == CacheMode.BYPASS

    def test_unknown_falls_back(self):
        result = _convert_cache_mode("nonexistent", CacheMode.BYPASS)
        assert result == CacheMode.BYPASS


class TestApplyOverrides:
    def test_no_overrides(self):
        config = CrawlerRunConfig(verbose=False)
        _apply_overrides(config, RunConfigOverrides())
        assert config.verbose is False

    def test_all_overrides(self):
        config = CrawlerRunConfig()
        overrides = RunConfigOverrides(
            verbose=True,
            semaphore_count=5,
            wait_until="networkidle",
            delay_before_return_html=1.0,
            mean_delay=2.0,
            max_range=0.5,
            magic=True,
            cache_mode="BYPASS",
            css_selector="main",
            target_elements=["main", "article"],
            excluded_tags=["nav", "footer"],
            excluded_selector="aside",
            scan_full_page=True,
            js_code="console.log(1)",
            wait_for="js:() => true",
            ignore_body_visibility=True,
            stream=False,
            exclude_external_links=True,
        )
        _apply_overrides(config, overrides)
        assert config.verbose is True
        assert config.semaphore_count == 5
        assert config.wait_until == "networkidle"
        assert config.delay_before_return_html == 1.0
        assert config.mean_delay == 2.0
        assert config.max_range == 0.5
        assert config.magic is True
        assert config.cache_mode == CacheMode.BYPASS
        assert config.css_selector == "main"
        assert config.target_elements == ["main", "article"]
        assert config.excluded_tags == ["nav", "footer"]
        assert config.excluded_selector == "aside"
        assert config.scan_full_page is True
        assert config.js_code == "console.log(1)"
        assert config.wait_for == "js:() => true"
        assert config.ignore_body_visibility is True
        assert config.stream is False
        assert config.exclude_external_links is True


class TestBuildMarkdownGenerator:
    def test_returns_generator(self):
        gen = build_markdown_generator()
        assert gen is not None
        assert hasattr(gen, "generate_markdown")


class TestBuildMarkdownRunConfig:
    def test_default_config(self):
        config = build_markdown_run_config()
        assert isinstance(config, CrawlerRunConfig)
        assert config.cache_mode == CacheMode.BYPASS
        assert config.scan_full_page is True
        assert config.js_code is None
        assert config.wait_for is None

    def test_aggressive_spa_config(self):
        config = build_markdown_run_config(aggressive_spa=True)
        assert config.js_code is not None
        assert config.wait_for == AGGRESSIVE_SPA_WAIT_FOR

    def test_with_overrides(self):
        overrides = RunConfigOverrides(verbose=False, semaphore_count=10)
        config = build_markdown_run_config(overrides=overrides)
        assert config.verbose is False
        assert config.semaphore_count == 10


class TestBuildDiscoveryRunConfig:
    def test_default_config(self):
        config = build_discovery_run_config()
        assert isinstance(config, CrawlerRunConfig)
        assert config.cache_mode == CacheMode.BYPASS
        assert config.magic is True

    def test_aggressive_spa_config(self):
        config = build_discovery_run_config(aggressive_spa=True)
        assert config.js_code is not None
        assert config.wait_for == AGGRESSIVE_SPA_WAIT_FOR

    def test_with_overrides(self):
        overrides = RunConfigOverrides(verbose=False)
        config = build_discovery_run_config(overrides=overrides)
        assert config.verbose is False


class TestSelectors:
    def test_main_selectors_not_empty(self):
        assert len(MAIN_SELECTORS) > 0

    def test_excluded_selectors_not_empty(self):
        assert len(EXCLUDED_SELECTORS) > 0
