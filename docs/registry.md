# MCP Registry

searxNcrawl is described for the [official MCP Registry](https://registry.modelcontextprotocol.io/) by [`server.json`](../server.json) in the repository root:

| Field | Value |
| --- | --- |
| Name | `io.github.DasDigitaleMomentum/searxncrawl` |
| Package | PyPI `searxncrawl`, STDIO transport |
| Environment | `SEARXNG_URL`, `SEARXNG_USERNAME`, `SEARXNG_PASSWORD` (secret), `SEARCH_RESULT_FIELDS` |

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

`server.json` has two version fields, the server `version` and `packages[0].version`. Both must equal the `version` in `pyproject.toml`; the release workflow fails if they differ. Bump all three in the release PR.

`server.json` describes the latest PyPI release, so its environment variables follow that release.

## MCPB bundle

`mcpb/` is the source of an [MCPB](https://github.com/modelcontextprotocol/mcpb) bundle with the `uv` server type: `mcpb/pyproject.toml` pins the PyPI release, `mcpb/src/server.py` starts the MCP server, and `mcpb/manifest.json` asks for `SEARXNG_URL` and the optional `YDC_API_KEY`. Claude Desktop installs it with a double click. Smithery lists local STDIO servers from a bundle too, but its CLI only accepts `python`, `node`, `bun` and `binary` bundles and needs each tool's input schema, so `mcpb/smithery_bundle.py` builds a Smithery variant that runs `uvx searxncrawl==<version>`.

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
