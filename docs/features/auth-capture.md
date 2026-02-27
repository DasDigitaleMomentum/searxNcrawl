---
type: documentation
entity: feature
feature: "auth-capture"
version: 1.0
---

# Feature: Auth Capture

> Part of [searxNcrawl](../overview.md)

## Summary

Auth capture opens a visible (headed) Chromium browser window, lets the user complete a login flow interactively (including OAuth, SSO, MFA), then exports the browser's storage state (cookies + localStorage) to a JSON file. This file can be reused for subsequent authenticated crawls without manual login.

## How It Works

### User Flow

1. User runs: `crawl capture-auth --url https://login.example.com`
2. A Chromium browser window opens at the login URL.
3. User completes the login flow manually (type credentials, click through OAuth, solve MFA).
4. Capture triggers via one of:
   - **URL match**: Browser navigates to a URL matching `--wait-for-url` regex.
   - **Browser close**: User closes the browser window.
   - **Ctrl+C**: User interrupts from terminal.
   - **Timeout**: `--timeout` seconds elapse (default: 300s).
5. Storage state is saved to a JSON file (default: `auth_state.json`).
6. User receives a summary: cookie count, localStorage origin count, and usage instructions.

### Technical Flow

1. `capture_auth_state()` (`capture.py:44`) is called.
2. Playwright async API is lazily imported (fails gracefully if not installed).
3. **Profile mode** (`--profile`):
   - Profile dir resolved via `_resolve_profile_dir()` (absolute path or `~/.crawl4ai/profiles/<name>`).
   - `chromium.launch_persistent_context(user_data_dir=...)` opens the browser with persistent state.
   - Output path set to `<profile_dir>/storage_state.json`.
4. **Standard mode** (no `--profile`):
   - `chromium.launch(headless=False)` opens a fresh browser.
   - A new context is created; page navigates to the login URL.
5. Browser is configured with anti-detection (`--disable-blink-features=AutomationControlled`) and a realistic user agent.
6. **URL matching loop** (if `--wait-for-url` is set):
   - A grace period of min(5s, timeout) skips early matches (avoids false triggers on OAuth redirect URLs).
   - Polls `page.url` every 0.5s against the regex pattern.
   - On match, waits 2s for page to settle, then captures.
7. **Browser close loop** (no `--wait-for-url`):
   - Polls `page.is_closed()` every 0.5s.
   - Captures when browser is closed by user.
8. `context.storage_state()` exports cookies and localStorage.
9. State is written to JSON file with indentation.
10. Browser/context is closed in a `finally` block.

## Implementation

| Module | Symbols | Role |
|--------|---------|------|
| [crawler-core](../modules/crawler-core.md) | `capture_auth_state` (`capture.py:44`) | Main async capture function |
| [crawler-core](../modules/crawler-core.md) | `capture_auth_state_sync` (`capture.py:260`) | Synchronous wrapper |
| [crawler-core](../modules/crawler-core.md) | `_resolve_profile_dir` (`capture.py:35`) | Resolve profile name to absolute path |
| [crawler-core](../modules/crawler-core.md) | `_parse_capture_auth_args` (`cli.py:421`) | Parse CLI args for capture-auth subcommand |
| [crawler-core](../modules/crawler-core.md) | `_run_capture_auth_async` (`cli.py:578`) | CLI execution wrapper |

## Configuration

| Parameter | CLI Flag | Default | Purpose |
|-----------|----------|---------|---------|
| Login URL | `--url` | required | The login page to navigate to |
| Output path | `--output` | `auth_state.json` | Where to save storage state (ignored with `--profile`) |
| Wait-for URL | `--wait-for-url` | (none) | Regex: auto-capture when browser URL matches |
| Timeout | `--timeout` | `300` | Max seconds to wait for login completion |
| Profile | `--profile` | (none) | Profile name or path for persistent browser session |
| Verbose | `-v` | `false` | Enable debug logging |

### Profile Storage

- Named profiles: `~/.crawl4ai/profiles/<name>/`
- Absolute paths: used directly
- Storage state always saved as `storage_state.json` inside the profile directory

## Edge Cases & Limitations

- **Headed browser required**: This feature cannot work in headless mode or inside Docker without a display server. It requires a desktop environment.
- **OAuth redirect grace period**: The 5-second grace period prevents false URL matches during OAuth redirect chains. Some very fast logins may be missed during this window.
- **Timeout behavior**: If timeout is reached without login completion, a `TimeoutError` is raised. The storage state is NOT saved in this case.
- **Browser crash**: If the browser process crashes, the `page.is_closed()` or `page.url` checks will catch the exception and trigger capture of whatever state is available.
- **Playwright dependency**: Playwright must be installed with Chromium (`playwright install chromium`). A `RuntimeError` is raised with installation instructions if missing.
- **Anti-detection**: The browser is launched with `--disable-blink-features=AutomationControlled` and a realistic user agent, but some sites may still detect automation.

## Related Features

- [Authenticated Crawling](authenticated-crawling.md) -- uses the captured storage state for crawling
- [CLI Interface](cli.md) -- `crawl capture-auth` subcommand
