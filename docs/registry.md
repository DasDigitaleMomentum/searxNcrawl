# MCP Registry

- [`server.json`](../server.json) describes searxNcrawl for the [official MCP Registry](https://registry.modelcontextprotocol.io/).
- Public snapshot verified **28 October 2026**: PyPI and MCP Registry package version **0.33.0**. Recheck the public endpoints after each release.

| Field | Value |
| --- | --- |
| Name | `io.github.DasDigitaleMomentum/searxncrawl` |
| Package | PyPI `searxncrawl`, STDIO transport |
| Environment | `SEARXNG_URL`, `SEARXNG_USERNAME`, `SEARXNG_PASSWORD` (secret), `SEARXNG_EXTRA_HEADERS` (secret), `YDC_API_KEY` (secret), `SEARCH_RESULT_FIELDS` |

The registry verifies PyPI ownership through the `mcp-name` comment in the README, which PyPI shows as the package description:

```html
<!-- mcp-name: io.github.DasDigitaleMomentum/searxncrawl -->
```

The name in that comment and the `name` in `server.json` must match, and the release on PyPI must contain the comment.

## Publish a version

Publish after the release is on PyPI. The `io.github.DasDigitaleMomentum/` namespace requires a GitHub login by an **owner** of the DasDigitaleMomentum organisation; ordinary membership is not enough.

```bash
brew install mcp-publisher        # or download from github.com/modelcontextprotocol/registry/releases
mcp-publisher validate            # checks server.json against the registry schema
mcp-publisher login github        # device login in the browser
mcp-publisher publish
```

Check the result:

```bash
curl "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.DasDigitaleMomentum/searxncrawl"
```

## Keep versions in sync

- Keep `pyproject.toml`, both `server.json` version fields, `mcpb/manifest.json`, the bundle project version and its `searxncrawl==` pin synchronized.
- Move released changelog entries out of `Unreleased`.
- Keep registry and bundle environment mappings aligned with the released code. Extra headers can contain credentials and must be marked secret/sensitive.

`server.json` describes the published package release; keep its version and environment variables aligned when releasing.

## MCPB bundle

- `mcpb/pyproject.toml` pins the PyPI release; `mcpb/src/server.py` starts the server.
- The [MCPB](https://github.com/modelcontextprotocol/mcpb) manifest exposes optional SearXNG URL/basic auth/extra headers, You.com API key and result-field selection. Passwords, extra headers and API keys are sensitive fields.
- Extra-header values accept `@/absolute/path` or `@~/path` secret files. Invalid configuration disables only SearXNG; see [installation](usage/installation.md).
- Claude Desktop installs the `uv` bundle with a double click.

```bash
npx @anthropic-ai/mcpb validate mcpb/manifest.json
npx @anthropic-ai/mcpb pack mcpb searxncrawl-<version>.mcpb
gh release upload v<version> searxncrawl-<version>.mcpb
```

The release workflow fails if `mcpb/manifest.json` or the pin in `mcpb/pyproject.toml` does not match `pyproject.toml`.

## Glama releases

- Snapshot verified **28 October 2026**: [public listing](https://glama.ai/mcp/servers/DasDigitaleMomentum/searxNcrawl) build **0.33.1**, package **0.33.0**, GitHub `main` source `e8cc4d6`; automatic releases enabled.
- Glama build numbers and Python package releases are independent; do not change package release metadata to match a Glama build number.
- The listing builds the repository source; verify the selected commit and package version after each sync. A documentation-only main update can retain the same runtime release.

### Build configuration

| Setting | Value |
| --- | --- |
| Base image | `debian:trixie-slim` |
| Node.js | `24` |
| Python | `3.14` |
| Build step 1 | `uv sync --locked` |
| Build step 2 | `uv run --locked playwright install --with-deps chromium` |
| Start command | `mcp-proxy -- uv run --no-sync crawl-mcp` |
| Placeholder | `MCP_PORT=9555` only |

- `SEARXNG_URL` is optional, without a localhost default; set it only for a reachable SearXNG instance.
- Mark `SEARXNG_PASSWORD`, `SEARXNG_EXTRA_HEADERS` and `YDC_API_KEY` as secrets. Crawling does not require a search provider.

### Repeatable release check

1. Sync the intended GitHub `main` source in Glama; verify its commit, target package version and automatic-release setting.
2. Confirm the build configuration above; wait for dependency installation, Chromium installation and the complete build to succeed.
3. Verify the latest public Glama build and its underlying package version independently; a successful build alone does not prove publication.
4. Check the public tool schemas: `search`, `crawl` and `crawl_site`; `search` includes boolean `include_content`. Run configured-provider search and browser-crawl checks against that release before accepting those runtime paths.

## Smithery transition

- Status checked **28 October 2026**. Recheck the official notice before relying on the directory after shutdown.

- Smithery's [official transition notice](https://www.smithery.ai/future) schedules API, account/API key, CLI/SDK and proxy shutdown for **31 October 2026**.
- The public directory remains curated, with direct vendor MCP URLs.
- CLI `4.11.1` publishing currently returns HTTP `403`, `Updating servers has been removed`.
- No replacement publishing flow has been verified. The [existing listing](https://smithery.ai/servers/dasdigitalemomentum/searxncrawl) has not been updated to 0.33.0.
- Install directly from [PyPI](https://pypi.org/project/searxncrawl/0.33.0/) or use the [native 0.33.0 MCPB bundle](https://github.com/DasDigitaleMomentum/searxNcrawl/releases/download/v0.33.0/searxncrawl-0.33.0.mcpb).

```bash
uvx searxncrawl==0.33.0
```

### Legacy Smithery bundle (optional)

- [`mcpb/smithery_bundle.py`](../mcpb/smithery_bundle.py) retains the historical Python bundle format with tool input schemas and a pinned `uvx` command.
- Generation produces a local compatibility artifact; it does not publish to Smithery or update its listing.

```bash
uv run mcpb/smithery_bundle.py searxncrawl-0.33.0-smithery.mcpb
```

## PulseMCP submissions

- Snapshot checked **28 October 2026**: new submissions and listing changes are paused.
- Recheck [PulseMCP submission status](https://www.pulsemcp.com/submit) before attempting a submission; listing availability is separate from package/Registry publication.
