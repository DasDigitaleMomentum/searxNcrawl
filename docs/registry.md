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

Publish after the release is on PyPI. The `io.github.DasDigitaleMomentum/` namespace requires a GitHub login by a member of the DasDigitaleMomentum organisation.

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

`server.json` describes the latest PyPI release, so its environment variables follow that release. The first release that ships the You.com provider must add `YDC_API_KEY` (secret, optional) and drop the `http://localhost:8888` default from the `SEARXNG_URL` description, since that default no longer exists on `main`.
