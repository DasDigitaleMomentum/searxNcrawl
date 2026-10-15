# MCP Server

One-line setup commands for Claude Code, Codex, Cursor and VS Code are in the [README](../../README.md#add-it-to-your-agent). This page covers the server options and manual client configuration.

## Register with `searxncrawl setup`

`setup` detects Claude Code, Codex, Gemini CLI, Cursor, VS Code and Claude Desktop, asks for your SearXNG URL (suggesting `$SEARXNG_URL`) and, optionally, a You.com API key (hidden input, suggesting `$YDC_API_KEY`), shows the exact change for each agent and applies it only after you confirm. It uses the agent's own `mcp add` CLI where one exists and otherwise edits the agent's JSON config. Every file it touches is backed up next to the original as `<file>.searxncrawl-backup-<timestamp>`. Re-running updates the entry instead of adding a second one.

The You.com key is written in plain text into each agent's MCP config (that is where agents read it from), but `setup` never prints it: commands, diffs and agent CLI output show `<hidden>` instead. With `--yes` and no `--ydc-api-key`, `setup` uses `$YDC_API_KEY` if it is set. If neither a SearXNG URL nor a You.com key is given, `setup` warns that search has no provider.

```bash
uvx searxncrawl setup
uvx searxncrawl setup --yes --searxng-url http://your-searxng:8888   # non-interactive
uvx searxncrawl setup --yes --ydc-api-key "$YDC_API_KEY"             # You.com only
uvx searxncrawl setup --agent cursor --agent vscode                  # only these agents
uvx searxncrawl setup --remove                                       # unregister again
```

Restart the agents afterwards. `setup` is not in the 0.31.0 release on PyPI; until the next release, replace `uvx searxncrawl` with `uvx --from git+https://github.com/DasDigitaleMomentum/searxNcrawl searxncrawl`.

## Start the server

```bash
# STDIO transport (for MCP harnesses)
python -m crawler.mcp_server

# HTTP transport
python -m crawler.mcp_server --transport http --port 8000

# HTTP exposed through a specific public hostname
python -m crawler.mcp_server --transport http --host 0.0.0.0 --allowed-hosts "mcp.example.com"

# HTTP with CORS
python -m crawler.mcp_server --transport http --allowed-hosts "mcp.example.com" --cors-origins "https://app.example.com"

# Docker (HTTP only)
docker compose up --build
```

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

FastMCP validates the HTTP `Host` header independently of the address on which
the server listens. For remote access, allow the exact externally visible Host
header with a comma-separated CLI value:

```bash
crawl-mcp --transport http --host 0.0.0.0 --allowed-hosts "mcp.example.com,mcp.internal.example"
```

Alternatively, use FastMCP's environment setting. It uses JSON-list syntax:

```bash
FASTMCP_HTTP_ALLOWED_HOSTS='["mcp.example.com"]' crawl-mcp --transport http --host 0.0.0.0
```

Browser Origin validation and CORS response headers are separate from Host
validation. `--cors-origins` configures both FastMCP's Origin guard and the CORS
middleware using the same normalized, comma-separated values:

```bash
crawl-mcp --transport http --cors-origins "http://localhost:3000,https://myapp.com"
crawl-mcp --transport http --cors-origins "*"   # all origins — local dev only
```

Omitting either allowlist preserves FastMCP's secure defaults (and permits the
upstream environment setting to apply). A value of `*` for Hosts or Origins is
an explicit opt-in to broad access and should only be used when that security
trade-off is intentional. Without `--cors-origins`, no CORS headers are sent.

