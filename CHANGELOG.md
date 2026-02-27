# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-26

### Added
- **Authenticated Crawling** - Crawl pages behind login walls (OAuth, SSO, MFA)
  - Cookies injection: Pass session cookies directly
  - Custom headers: Add `Authorization: Bearer` or any custom headers
  - Storage state: Reuse Playwright browser state (cookies + localStorage)
  - Persistent browser profiles: Use saved browser profiles
- **`capture-auth` CLI subcommand** - Interactive session capture
  - Opens a headed browser for manual login
  - Exports storage state JSON for reuse
  - Optional `--wait-for-url` regex for auto-capture
- **MCP Tool auth params** - `cookies`, `headers`, `storage_state` on `crawl()` and `crawl_site()`
- **`list_auth_profiles` MCP tool** - List available persistent browser profiles
- **CLI auth flags** - `--cookies`, `--header`, `--storage-state`, `--auth-profile`
- **Environment variable auth** - `CRAWL_AUTH_STORAGE_STATE`, `CRAWL_AUTH_COOKIES_FILE`, `CRAWL_AUTH_PROFILE`
- **New modules:**
  - `crawler/auth.py` - AuthConfig dataclass and BrowserConfig builder
  - `crawler/capture.py` - Interactive session capture tool

---

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
