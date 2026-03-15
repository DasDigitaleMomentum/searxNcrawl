from __future__ import annotations

from crawler.config import build_discovery_run_config, build_markdown_run_config


def test_default_run_configs_disable_verbose_logging_for_mcp_stdio() -> None:
    """MCP stdio transport must not emit noisy crawler init logs to stdout."""
    markdown_config = build_markdown_run_config()
    discovery_config = build_discovery_run_config()

    assert markdown_config.verbose is False
    assert discovery_config.verbose is False
