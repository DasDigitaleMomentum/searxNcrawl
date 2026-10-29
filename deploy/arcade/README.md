# Optional Arcade worker adapter

- Standard installations use the [native MCP server](../../docs/usage/mcp-server.md) directly over STDIO or HTTP.
- Use this separate adapter when you need Arcade's shared authentication and gateway across multiple MCP servers.
- The adapter is installed and deployed separately; it is not part of the standard setup or release requirements.

- Uses the published `searxncrawl==0.33.0` package; does not change the package's MCP or CLI entrypoints.
- Exposes `Searxncrawl_Crawl`, `Searxncrawl_CrawlSite` and `Searxncrawl_Search` through Arcade's `MCPApp`.
- Reuses native crawling and search behavior, including `providers` and `include_content`.
- Runs each search in a separate native MCP process with that request's search configuration.

## Runtime requirements

- Python 3.12 or newer on a Playwright-supported host, with Chromium and its system dependencies installed.
- A reachable SearXNG instance and/or a You.com API key.
- An authenticated Arcade worker connection for production use.
- **Arcade Cloud deployment is currently unavailable for this adapter.** Its discovery endpoint advertises only a Python 3.12 `musllinux_1_2` runner; the package build fails because no compatible Playwright distribution is available. Do not remove browser dependencies to bypass this failure.
- Arcade documents [hybrid workers](https://docs.arcade.dev/en/operate/deploy/on-prem) for hosting outside Arcade Cloud. This repository does not provision a host or establish that connection.

## Install and verify locally

```bash
cd deploy/arcade
uv sync --locked --extra dev
uv run --locked playwright install --with-deps chromium
uv run --locked --extra dev pytest
```

## Container

```bash
cd deploy/arcade
docker build --tag searxncrawl-arcade:0.33.0 .
docker run --rm -i --network none searxncrawl-arcade:0.33.0 python - --arcade < ../../tests/container_smoke.py
```

- Debian-based Python 3.12 image, locked dependencies and preinstalled Chromium; runs as a non-root user.
- The build context allows only the Dockerfile, package metadata, lockfile and adapter source. Credentials and working files are excluded.
- Tini runs as PID 1 to reap orphaned Chromium children and forward shutdown signals; keep the image entrypoint when overriding commands. Custom entrypoints require `--init` (Compose `init: true`, Podman Quadlet `RunInit=true`).
- Starts over STDIO by default. For local MCP clients, use `docker run --rm -i --env SEARXNCRAWL_SEARCH_CONFIG searxncrawl-arcade:0.33.0` with the secret already set in the caller's environment.
- The offline smoke test uses real Chromium against a local JavaScript page and a local SearXNG protocol fixture, including `search(include_content=True)`; it does not establish live-provider acceptance.
- Building the image does not deploy or register it with Arcade. For hybrid HTTP operation, expose only the authenticated `/worker/` routes through the TLS proxy; the SDK's separate `/mcp` route needs its own resource-server authentication and must not be published unprotected.

## Search configuration

Store `SEARXNCRAWL_SEARCH_CONFIG` as an Arcade secret containing a JSON object. Allowed string fields:

| Field | Purpose |
| --- | --- |
| `SEARXNG_URL` | Reachable HTTP(S) URL without embedded credentials |
| `SEARXNG_USERNAME`, `SEARXNG_PASSWORD` | Optional basic authentication pair |
| `SEARXNG_EXTRA_HEADERS` | JSON-encoded extra headers; file references resolve on the worker |
| `YDC_API_KEY` | You.com API key |
| `SEARCH_RESULT_FIELDS` | Optional native result field selection |

- Configure at least one provider; missing providers remain disabled.
- Unknown fields and non-string values are rejected without echoing their values.
- All six provider variables are set explicitly in the child process; parent provider credentials are not inherited.
- Secret values belong in Arcade's secret store, not source files, tool arguments or deployment archives.
- For a local STDIO check, supply the same secret through the process environment and run `uv run --locked python server.py`.

## Connect an HTTP worker to Arcade

- Set a strong `ARCADE_WORKER_SECRET` in the host environment. Keep the worker listener private; publish it only through a TLS proxy.
- Run the container with `ARCADE_SERVER_TRANSPORT=http`, `ARCADE_SERVER_HOST=0.0.0.0`, `ARCADE_AUTH_DISABLED=false` and the worker secret. The default HTTP port is 8000.
- Allow only `GET /worker/health`, `GET /worker/tools` and `POST /worker/tools/invoke` through the proxy. Return 404 for every other path, including `/mcp` and `/docs`. Health is public; catalog and invocation require a signed worker token.
- Register an **Arcade** server using the proxy's HTTPS origin and the same worker secret. The tested Arcade Cloud settings are **timeout 60 seconds, retry 1**; its API rejects timeouts above 60 seconds. Keep each crawl workload within that transport limit.
- Store the search configuration in Arcade's secret management; the Engine supplies it with each invocation.
- Create an OAuth MCP gateway allowing only `Searxncrawl.Crawl`, `Searxncrawl.CrawlSite` and `Searxncrawl.Search`. Use a regular MCP OAuth client; a CLI login token is not accepted as a gateway OAuth token.
- Append `?arcade_tools=false` to the client's gateway URL to expose exactly those three tools. Arcade otherwise adds its own app and capability-request tools by default; this is independent of the selected worker tools. See [Private Registry controls](https://docs.arcade.dev/en/operate/governance/private-registry#turn-capability-requests-on-or-off).
- Verify gateway authentication, real provider searches, both crawl tools and `include_content` from an external MCP client. A healthy worker or successful Engine API call alone does not complete this check.
- Temporary tunnels are for acceptance tests. Production requires a stable host, persistent HTTPS endpoint and monitoring; this repository does not provision those resources.

## Deployment archive

- Stage only `server.py` and `pyproject.toml` in a separate directory. Exclude tests, credentials, plans and verification artifacts.
- Never run the deployment CLI from the repository root: its bundle can include unrelated non-hidden files.
- Follow Arcade's worker authentication setup before exposing a network listener. The local STDIO test does not prove hosted authentication or availability.
