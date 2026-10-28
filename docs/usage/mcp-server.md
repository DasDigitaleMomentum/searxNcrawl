# MCP Server

<!-- Updated: 2026-10-28 -->

One-line setup commands for Claude Code, Codex, Cursor and VS Code are in the [README](../../README.md#add-it-to-your-agent). This page covers the server options and manual client configuration.

## Register with `searxncrawl setup`

- Detects Claude Code, Codex, Gemini CLI, Cursor, VS Code and Claude Desktop.
- Prompts for the SearXNG URL and an optional You.com key, suggesting `$SEARXNG_URL` and `$YDC_API_KEY`; key input is hidden.
- Shows each change and asks before applying it; `--yes` uses environment defaults and skips confirmation.
- Uses an agent's `mcp add` CLI where available; otherwise edits its JSON config. Existing files get a `<file>.searxncrawl-backup-<timestamp>` backup; repeat runs update the entry.
- Stores the You.com key as plain text in agent configs; displayed commands, diffs and agent CLI output mask it as `<hidden>`.
- Warns when no search provider is supplied.

```bash
uvx searxncrawl setup
uvx searxncrawl setup --yes --searxng-url http://your-searxng:8888   # non-interactive
uvx searxncrawl setup --yes --ydc-api-key "$YDC_API_KEY"             # You.com only
uvx searxncrawl setup --agent cursor --agent vscode                  # only these agents
uvx searxncrawl setup --remove                                       # unregister again
```

Restart the agents afterwards.

## Start the server

```bash
# STDIO transport (for MCP harnesses)
python -m crawler.mcp_server

# HTTP transport
python -m crawler.mcp_server --transport http --port 8000

# HTTP exposed through a specific public hostname
FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true python -m crawler.mcp_server --transport http --host 0.0.0.0 --allowed-hosts "mcp.example.com"

# HTTP with CORS
FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true python -m crawler.mcp_server --transport http --allowed-hosts "mcp.example.com" --cors-origins "https://app.example.com"

# Docker (HTTP only)
docker compose up --build
```

- `searxncrawl`, `crawl-mcp` and `python -m crawler.mcp_server` use the same entrypoint.
- Defaults: STDIO transport; HTTP bind address `127.0.0.1`, port `8000`, path `/mcp`. Docker Compose uses port `9555` by default.
- CLI and MCP share the [configuration file search order](installation.md#search-providers).
- Optional Arcade integration uses a separately installed, pinned-package worker adapter on a compatible host. See [adapter setup and security](../../deploy/arcade/README.md); the repository does not provision permanent hosting.

## MCP client configuration

`searxncrawl setup` writes the configuration below for you. To do it by hand:

**With uvx (no clone, no venv):**

```json
{
  "mcpServers": {
    "searxncrawl": {
      "command": "uvx",
      "args": ["searxncrawl"],
      "env": { "SEARXNG_URL": "http://your-searxng:8888" }
    }
  }
}
```

The first crawl downloads Playwright's Chromium once (about 550 MB on disk); later starts reuse it. On Linux hosts without the browser's system libraries, run `uvx --from searxncrawl playwright install --with-deps chromium` once.

**Protected SearXNG instances:**

- Add `SEARXNG_EXTRA_HEADERS` to the MCP process environment or shared `.env`; `setup` does not prompt for extra headers or copy them into agent configs.
- Use a JSON object of ASCII string values; `@/absolute/path` or `@~/path` values load UTF-8 secret files on each search call.
- Headers are SearXNG-only. Invalid configuration disables SearXNG with a value-free warning; You.com remains available when configured.
- `Accept` and `Content-Type` stay `application/json`. See [the complete header rules and Cloudflare Access example](installation.md#searxng-behind-cloudflare-access).

**Python with venv:**

```json
{
  "mcpServers": {
    "searxncrawl": {
      "command": "python",
      "args": ["-m", "crawler.mcp_server"],
      "cwd": "/path/to/searxNcrawl",
      "env": { "SEARXNG_URL": "http://your-searxng:8888" }
    }
  }
}
```

**With uv (no manual venv):**

```json
{
  "mcpServers": {
    "searxncrawl": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/searxNcrawl", "python", "-m", "crawler.mcp_server"],
      "env": { "SEARXNG_URL": "http://your-searxng:8888" }
    }
  }
}
```

**Docker (HTTP endpoint):**

```json
{
  "mcpServers": {
    "searxncrawl": {
      "url": "http://localhost:9555/mcp"
    }
  }
}
```

## HTTP Host and CORS guards

- Host and Origin guards validate request headers; they do not authenticate callers.
- The native server configures no caller authentication. Put shared HTTP access behind an authenticated TLS proxy.
- **Enable header protection explicitly:** set `FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true` in the process environment before starting the server. Locked FastMCP 4.1.3 defaults this guard to `false`; allowlists alone do not enable it.
- Export FastMCP settings before Python starts; FastMCP initializes before the native `.env` loader runs. Docker Compose injects its `.env` through `env_file`, so set the flag there for the container.

With protection enabled, FastMCP validates the HTTP `Host` header independently
of the bind address. Allow the externally visible names:

```bash
FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true crawl-mcp --transport http --host 0.0.0.0 --allowed-hosts "mcp.example.com,mcp.internal.example"
```

Alternatively, use FastMCP's environment setting. It uses JSON-list syntax:

```bash
FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true FASTMCP_HTTP_ALLOWED_HOSTS='["mcp.example.com"]' crawl-mcp --transport http --host 0.0.0.0
```

- Browser Origin validation and CORS response headers are separate controls.
- `--cors-origins` supplies the enabled Origin guard and the CORS middleware with the same normalized values.
- With the guard disabled, the option still configures CORS response headers; it does not enforce request-time Origin rejection.

```bash
FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true crawl-mcp --transport http --cors-origins "http://localhost:3000,https://myapp.com"
FASTMCP_HTTP_HOST_ORIGIN_PROTECTION=true crawl-mcp --transport http --cors-origins "*"   # all origins — local dev only
```

- Omitting an allowlist leaves FastMCP's corresponding setting unchanged; it does not enable the guard.
- `*` explicitly admits arbitrary Hosts or Origins when protection is enabled; prefer exact allowlists.
- Without `--cors-origins`, the native entrypoint adds no CORS middleware.

