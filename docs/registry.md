# MCP Registry

searxNcrawl is described for the [official MCP Registry](https://registry.modelcontextprotocol.io/) by [`server.json`](../server.json) in the repository root:

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

`server.json` describes the latest PyPI release, so its environment variables follow that release.

## MCPB bundle

- `mcpb/pyproject.toml` pins the PyPI release; `mcpb/src/server.py` starts the server.
- The [MCPB](https://github.com/modelcontextprotocol/mcpb) manifest exposes optional SearXNG URL/basic auth/extra headers, You.com API key and result-field selection. Passwords, extra headers and API keys are sensitive fields.
- Extra-header values accept `@/absolute/path` or `@~/path` secret files. Invalid configuration disables only SearXNG; see [installation](usage/installation.md).
- Claude Desktop installs the `uv` bundle with a double click.
- Smithery requires a `python`/`node`/`bun`/`binary` bundle and tool input schemas. `mcpb/smithery_bundle.py` builds its variant from the published version and runs `uvx searxncrawl==<version>`.

```bash
npx @anthropic-ai/mcpb validate mcpb/manifest.json
npx @anthropic-ai/mcpb pack mcpb searxncrawl-<version>.mcpb
gh release upload v<version> searxncrawl-<version>.mcpb
uv run mcpb/smithery_bundle.py searxncrawl-<version>-smithery.mcpb
npx @smithery/cli auth login
npx @smithery/cli mcp publish searxncrawl-<version>-smithery.mcpb -n dasdigitalemomentum/searxncrawl
```

The Smithery listing is [dasdigitalemomentum/searxncrawl](https://smithery.ai/servers/dasdigitalemomentum/searxncrawl).

The release workflow fails if `mcpb/manifest.json` or the pin in `mcpb/pyproject.toml` does not match `pyproject.toml`.
