# Session Capture (`crawl-capture`)

`crawl-capture` produces a Playwright `storage_state` file for authenticated crawling. Two methods are supported.

## Option A — Manual login flow (built-in browser)

Use when your identity provider allows login in Playwright-launched browsers.

```bash
# Capture after login redirect matches completion URL regex
crawl-capture \
  --start-url https://example.com/login \
  --completion-url 'https://example.com/dashboard.*' \
  --output ./state.json

# Overwrite existing output (explicit flag required)
crawl-capture \
  --start-url https://example.com/login \
  --completion-url 'https://example.com/app.*' \
  --output ./state.json \
  --overwrite
```

## Option B — Export from running Chrome/Chromium via CDP

Use when providers (e.g. Google) reject automated-login browsers.

### 1) Start Chrome with remote debugging

```bash
# Linux
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-cdp-searxncrawl"
```

### 2) Log in manually in that browser

Navigate to your target app and sign in.

### 3) List selectable sessions

```bash
crawl-capture --cdp-url http://127.0.0.1:9222 --list-sessions
```

### 4) Export by session index

```bash
crawl-capture \
  --cdp-url http://127.0.0.1:9222 \
  --cdp-session 2 \
  --output ./state.json
```

Or use interactive selection:

```bash
crawl-capture \
  --cdp-url http://127.0.0.1:9222 \
  --list-sessions \
  --select \
  --output ./state.json
```

## Using the captured state

```bash
crawl https://example.com/private --storage-state ./state.json
```

## Exit codes

| Code | Meaning                                                             |
| ---- | ------------------------------------------------------------------- |
| `0`  | Success — storage state written                                     |
| `2`  | Timeout — completion condition not reached in time (manual flow only) |
| `130` | Abort — browser/session closed before completion (manual flow only) |

## Safety notes

- Keep `storage_state` files out of version control (add to `.gitignore`)
- Capture/export is isolated from standard `crawl` / `crawl_site` paths
- Multiple tabs sharing one browser context/profile share the same exported session state
