---
type: documentation
entity: feature
feature: "authenticated-crawling"
version: 1.0
---

# Feature: Authenticated Crawling

> Part of [searxNcrawl](../overview.md)

## Summary

Authenticated crawling allows users to crawl pages behind login walls (OAuth, SSO, MFA) by injecting cookies, custom HTTP headers, Playwright storage state (cookies + localStorage), or reusing persistent browser profiles. Auth configuration is composable and can be provided via CLI flags, MCP tool parameters, environment variables, or the Python API.

## How It Works

### User Flow

1. User obtains auth credentials via one of:
   - **Manual**: Export cookies or generate API tokens.
   - **Capture-auth**: Use the interactive browser flow to export storage state (see [Auth Capture](auth-capture.md)).
2. User passes auth credentials when crawling:
   - CLI: `crawl --storage-state auth_state.json https://protected.example.com`
   - MCP: `crawl(urls=[...], storage_state="/path/to/auth_state.json")`
   - Python: `crawl_page_async(url, auth=AuthConfig(storage_state="..."))`.
   - Environment: Set `CRAWL_AUTH_STORAGE_STATE=/path/to/auth_state.json` (applies to all crawls).
3. The crawler uses the auth context to access protected content.

### Technical Flow

1. Auth credentials are resolved in priority order:
   - **Explicit parameters** (CLI args, MCP params, Python `auth=` kwarg) take precedence.
   - **Environment variables** (`CRAWL_AUTH_*`) are used as fallback.
2. An `AuthConfig` dataclass is constructed (`auth.py:44`) with optional fields:
   - `cookies`: List of cookie dicts
   - `headers`: Dict of custom HTTP headers
   - `storage_state`: Path to Playwright storage state JSON
   - `storage_state_data`: Inline storage state dict
   - `user_data_dir`: Path to persistent browser profile
   - `use_persistent_context`: Auto-enabled when `user_data_dir` is set
3. `build_browser_config(auth)` (`auth.py:102`) creates a crawl4ai `BrowserConfig`:
   - Injects cookies, headers, resolved storage state, and/or persistent profile.
   - Returns default non-auth config if `AuthConfig` is empty.
4. The `BrowserConfig` is passed to `AsyncWebCrawler(config=browser_cfg)`.
5. crawl4ai uses the browser config to launch Chromium with the auth context.

### Auth Profile Auto-Resolution

When `auth_profile` (or `user_data_dir`) is set without an explicit `storage_state`, the system auto-resolves `storage_state.json` from the profile directory. This happens in:
- `_build_auth_config()` in `mcp_server.py:191`
- `_build_cli_auth()` in `cli.py:211`
- `load_auth_from_env()` in `auth.py:147`

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-core](../modules/crawler-core.md) | `AuthConfig` (`auth.py:44`) | Dataclass holding all auth configuration fields |
| [crawler-core](../modules/crawler-core.md) | `AuthConfig.is_empty` (`auth.py:74`) | Check if any auth is configured |
| [crawler-core](../modules/crawler-core.md) | `AuthConfig.resolved_storage_state` (`auth.py:85`) | Load storage state from file or inline data |
| [crawler-core](../modules/crawler-core.md) | `build_browser_config` (`auth.py:102`) | Build crawl4ai BrowserConfig from AuthConfig |
| [crawler-core](../modules/crawler-core.md) | `load_auth_from_env` (`auth.py:147`) | Load auth from CRAWL_AUTH_* env vars |
| [crawler-core](../modules/crawler-core.md) | `load_auth_from_file` (`auth.py:201`) | Load auth from JSON config file |
| [crawler-core](../modules/crawler-core.md) | `list_auth_profiles` (`auth.py:232`) | List profiles in ~/.crawl4ai/profiles/ |
| [crawler-core](../modules/crawler-core.md) | `_build_auth_config` (`mcp_server.py:191`) | Build AuthConfig from MCP tool params |
| [crawler-core](../modules/crawler-core.md) | `_build_cli_auth` (`cli.py:211`) | Build AuthConfig from CLI args |
| [crawler-core](../modules/crawler-core.md) | `_add_auth_args` (`cli.py:265`) | Add auth CLI flags to argparse |

## Configuration

### Auth Methods (Priority Order)

| Method | CLI Flag | MCP Param | Env Var | Description |
|--------|----------|-----------|---------|-------------|
| Cookies | `--cookies` | `cookies` | `CRAWL_AUTH_COOKIES_FILE` | JSON string, file path, or list of cookie dicts |
| Headers | `--header` (repeatable) | `headers` | -- | Custom HTTP headers (e.g. `Authorization: Bearer xyz`) |
| Storage state | `--storage-state` | `storage_state` | `CRAWL_AUTH_STORAGE_STATE` | Playwright storage state JSON (cookies + localStorage) |
| Browser profile | `--auth-profile` | `auth_profile` | `CRAWL_AUTH_PROFILE` | Persistent Chromium user-data-dir |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `CRAWL_AUTH_STORAGE_STATE` | Path to Playwright storage state JSON file |
| `CRAWL_AUTH_COOKIES_FILE` | Path to cookies JSON file (list of cookie dicts) |
| `CRAWL_AUTH_PROFILE` | Path to persistent browser profile directory |

### Env Variable Sanitisation

The `load_auth_from_env()` function sanitises env values: strips whitespace, ignores empty strings and values starting with `#` (commented-out). This prevents `.env` template values from being treated as real config.

### Default Profiles Directory

Persistent browser profiles are stored under `~/.crawl4ai/profiles/<name>/`. The `list_auth_profiles()` function enumerates this directory.

## Edge Cases & Limitations

- **Composable auth**: Cookies, headers, and storage state can be combined in a single `AuthConfig`. All are injected simultaneously.
- **Storage state vs profile**: `storage_state` injects cookies/localStorage into a fresh context. `user_data_dir` reuses a full Chromium profile (including service workers, cache). The profile approach is more robust for complex auth flows but less portable.
- **Session expiry**: Storage state files and cookies have expiration. Expired sessions will fail silently (the page loads but auth is not recognized). Users must re-capture.
- **crawl4ai limitation**: crawl4ai does not use `user_data_dir` as a Playwright persistent context directly; it needs `storage_state` for cookie injection. The auto-resolution logic works around this by reading `storage_state.json` from the profile directory.
- **Security**: Auth state files contain secrets. The `.gitignore` excludes `auth_state*.json`, `*_cookies.json`, `*_auth.json`, and `profiles/`.

## Related Features

- [Auth Capture](auth-capture.md) -- interactive flow to create storage state files
- [Web Crawling](web-crawling.md) -- auth is threaded through all crawl functions
- [MCP Server](mcp-server.md) -- auth parameters exposed on crawl/crawl_site tools
- [CLI Interface](cli.md) -- auth flags on the crawl command
