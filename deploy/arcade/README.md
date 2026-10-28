# Arcade worker adapter

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

## Deployment archive

- Stage only `server.py` and `pyproject.toml` in a separate directory. Exclude tests, credentials, plans and verification artifacts.
- Never run the deployment CLI from the repository root: its bundle can include unrelated non-hidden files.
- Follow Arcade's worker authentication setup before exposing a network listener. The local STDIO test does not prove hosted authentication or availability.
