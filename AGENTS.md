# AGENTS.md

Guidance for coding agents (Claude Code, Codex, Cursor, Copilot and others) working in this repository. Humans should start with the [README](README.md) and the [contributing guide](https://github.com/DasDigitaleMomentum/.github/blob/main/.github/CONTRIBUTING.md).

## Project

searxNcrawl is an MCP server, CLI and Python package for web search through SearXNG and/or You.com and Markdown crawling through Crawl4AI and Playwright. It is published on PyPI as `searxncrawl`; `server.json` describes it as `io.github.DasDigitaleMomentum/searxncrawl` for the MCP Registry.

## Layout

| Path | Contents |
| --- | --- |
| `crawler/mcp_server.py` | FastMCP server with the `crawl`, `crawl_site` and `search` tools; console scripts `searxncrawl` and `crawl-mcp` |
| `crawler/cli.py` | `crawl`, `search` and `crawl-capture` commands |
| `crawler/__init__.py` | Public Python API (`crawl_page`, `crawl_site` and async variants) |
| `crawler/config.py` | Crawl4AI run configuration and overrides |
| `crawler/search_orchestrator.py` | Search providers (SearXNG, You.com), parallel queries and result merging |
| `crawler/site.py` | Multi-page site crawling |
| `crawler/markdown_dedup.py` | Removal of repeated Markdown blocks |
| `crawler/document.py`, `builder.py`, `references.py` | `CrawledDocument` model and Markdown/JSON output |
| `crawler/auth.py`, `session_capture.py` | Authenticated crawling and session capture |
| `crawler/browser_setup.py` | Automatic Chromium install |
| `crawler/setup.py` | `searxncrawl setup`: registers the server with installed coding agents |
| `tests/` | pytest suite |
| `docs/usage/` | User guides linked from the README |
| `docs/modules/`, `docs/features/` | Architecture notes per module and feature |
| `server.json` | MCP Registry metadata |
| `mcpb/` | Claude Desktop MCPB source and legacy Smithery compatibility builder |
| `deploy/arcade/` | Optional Arcade adapter with separate dependencies and container; standard installations use the native MCP server |

## Commands

```bash
uv sync --extra dev                         # install with test dependencies
uv run playwright install chromium          # browser for crawl tests
uv run --extra dev pytest                   # full test suite, as in CI
uvx ruff@0.16.10 check .                    # lint, same version as CI
uv run python -m crawler.mcp_server         # MCP server over STDIO
```

## Rules

- **Keep stdout clean.** Over STDIO, stdout carries the MCP protocol. Logs and subprocess output go to stderr.
- **Tests with every change.** Add or update pytest tests for new behaviour and bug fixes. Unit tests must not depend on a live search provider or external websites.
- **Lint must pass.** CI runs `ruff check` with the configuration in `pyproject.toml`.
- **Changelog.** Add user-visible changes under `## [Unreleased]` in `CHANGELOG.md` ([Keep a Changelog](https://keepachangelog.com/en/1.1.0/)).
- **Commits and PRs.** English, [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:` …). PRs are squash-merged into `main` and need one approval.
- **Docs follow code.** When a tool parameter, default or environment variable changes, update `docs/usage/` and, if affected, the README.
- **No invented claims.** README and docs describe only what is merged. Mark planned work as planned.
- **Default integration.** Standard installations connect directly to the native MCP server over STDIO or HTTP. Arcade is optional and is not a runtime or release prerequisite.

## Releases

1. Bump `version` in `pyproject.toml`, both `version` fields in `server.json`, `version` in `mcpb/manifest.json` and the `searxncrawl==` pin in `mcpb/pyproject.toml`; keep the environment variables in `server.json` and `mcpb/manifest.json` in line with the released code.
2. Move the `Unreleased` changelog entries under the new version.
3. Publish a GitHub release tagged `v<version>`. The release workflow checks both versions and publishes to PyPI.
4. Publish the registry entry with `mcp-publisher login github` and `mcp-publisher publish`, pack the native MCPB bundle and attach it to the GitHub release (see [MCP Registry](docs/registry.md)).

- Smithery API/CLI shutdown: 2026-10-31; publishing currently returns HTTP 403. Smithery publication is no longer a release gate.
- Keep the Smithery compatibility builder for legacy artifacts; do not claim the curated listing was updated without verification.
