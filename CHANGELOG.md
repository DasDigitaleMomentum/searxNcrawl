# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Switchable markdown dedup mode across crawl surfaces:
  - CLI: `crawl --dedup-mode {exact,off}` (default: `exact`)
  - MCP tools: `crawl(..., dedup_mode=...)` and `crawl_site(..., dedup_mode=...)`
  - Python API: `crawl_page(_async)`, `crawl_pages(_async)`, and `crawl_site(_async)` accept `dedup_mode`
- New exact intra-document markdown dedup core with per-document dedup metrics in metadata:
  - `dedup_mode`, `dedup_sections_total`, `dedup_sections_removed`, `dedup_chars_removed`, `dedup_applied`
- Non-destructive dedup guardrail metadata and warning signal fields:
  - `dedup_guardrail_checked`, `dedup_guardrail_triggered`, `dedup_guardrail_reason`
  - `dedup_guardrail_section_removal_rate`, `dedup_guardrail_section_rate_threshold`
- Integration and regression test coverage for dedup behavior and parameter propagation across builder/API/CLI/MCP paths.
- Authenticated crawling MVP with `storage_state` support across:
  - CLI: `crawl --storage-state <path>`
  - MCP tools: `crawl(..., storage_state=...)` and `crawl_site(..., storage_state=...)`
  - Python API auth threading in page/pages/site crawl functions
- Isolated session capture flow via `crawl-capture` with explicit outcomes (`success`, `timeout`, `abort`).
- Auth/capture test coverage for resolver behavior, API/CLI/MCP auth propagation, and capture lifecycle.

### Fixed
- Resolved duplicate markdown blocks by improving exact dedup section segmentation around heading boundaries.

### Changed
- Updated README documentation for dedup controls, defaults, metadata fields, and usage examples.
- Updated README and module docs for authenticated crawling and isolated session capture usage.
- Kept crawler extraction selectors/configuration unchanged while introducing dedup controls (no selector/config drift).
- Preserved crawler extraction/runtime defaults while adding auth + capture support (no wait/SPA/persistent-session default drift).

## [0.1.1] - 2026-01-26

### Fixed
- Added explicit `name: searxncrawl` field for Dockge compatibility
- Converted docker-compose.yml to block-style YAML for better editor support

---

## [0.1.0] - 2026-01-26

### Added
- Initial release of searxNcrawl MCP Server
- Health check configuration in `docker-compose.yml` for container monitoring
- **Web Crawling Tools:**
  - `crawl`: Crawl one or more URLs and extract markdown content
  - `crawl_site`: Crawl entire websites with BFS strategy, depth/page limits
- **Web Search Tool:**
  - `search`: Search the web using SearXNG metasearch engine
- Output format options: `markdown` (default) and `json`
- `remove_links` option to strip URLs from markdown output
- Support for both STDIO and HTTP transports
- Docker and Docker Compose support
- CLI tools: `crawl`, `search`, `crawl-mcp`
- Environment-based configuration for SearXNG (URL, auth)
- Comprehensive README with usage examples

### Technical Details
- Built on [crawl4ai](https://github.com/unclecode/crawl4ai) for headless browser crawling
- Uses Playwright with Chromium for JavaScript rendering
- FastMCP for MCP protocol implementation
- httpx for async HTTP requests to SearXNG
