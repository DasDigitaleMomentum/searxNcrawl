# Installation

searxNcrawl runs as an MCP server, a set of CLI tools and a Python package. Pick the setup that fits; the `search` tool needs at least one [search provider](#search-providers), while crawling works without one.

## uvx (no clone)

Run the MCP server from [PyPI](https://pypi.org/project/searxncrawl/), no clone or virtualenv. Chromium is downloaded automatically on the first crawl.

```bash
SEARXNG_URL=http://your-searxng:8888 uvx searxncrawl
```

The latest development version runs straight from GitHub with `uvx --from git+https://github.com/DasDigitaleMomentum/searxNcrawl searxncrawl`.

## Docker Compose

The Compose stack includes searxNcrawl + Playwright/Chromium. Search providers (a SearXNG instance and/or a You.com API key) are configured separately.

```bash
cp .env.example .env
# Edit .env: set SEARXNG_URL and/or YDC_API_KEY
docker compose up --build
```

| Variable    | Default                   | Description                                                   |
| ----------- | ------------------------- | ------------------------------------------------------------- |
| `MCP_PORT`                  | `9555`                    | MCP server HTTP port                                          |
| `LOG_LEVEL`                 | `INFO`                    | MCP server log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `PLAYWRIGHT_AUTO_INSTALL`   | `true`                    | Download Playwright's Chromium automatically before the first browser launch if it is missing. Set to `false` where browsers are provisioned separately |
| `FASTMCP_HTTP_ALLOWED_HOSTS` | (FastMCP secure defaults) | JSON list of trusted HTTP Host headers, for example `["mcp.example.com"]` |

The MCP server is available at `http://localhost:9555/mcp`.

## pip

```bash
cd searxNcrawl
python -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

## uv

```bash
cd searxNcrawl
uv sync
uv run playwright install chromium
```

## What you get

| Feature                 | Docker Compose | pip / uv  |
| ----------------------- | -------------- | --------- |
| MCP Server (STDIO)      | —              | ✅        |
| MCP Server (HTTP)       | ✅             | ✅        |
| Web Crawl               | ✅             | ✅        |
| Web Search              | ✅¹            | ✅¹       |
| CLI Tools               | via `exec`²    | ✅        |
| Python API              | —              | ✅        |
| CORS (HTTP)             | ✅             | ✅        |

¹ Requires at least one search provider (SearXNG instance and/or You.com API key). ² `docker compose exec searxncrawl crawl ...`

## Search providers

`search` (MCP tool and CLI command) queries every configured provider in parallel. A provider is active only when it is configured; with none configured, search returns an error naming `SEARXNG_URL` and `YDC_API_KEY`.

- **SearXNG** — active when `SEARXNG_URL` is a valid http(s) URL without embedded credentials. There is no default URL. The instance needs **JSON output enabled** (`search.formats` in `settings.yml`); self-hosting is recommended over public instances (rate limits). Basic auth credentials are optional: set both or neither.
- **You.com** — active when `YDC_API_KEY` is set (non-empty). Requests send the key in the `X-API-Key` header and the User-Agent `youdotcom-integration/dasdigitalemomentum-searxncrawl`. You.com queries go to You.com in the US.

### Run SearXNG locally

If you have no instance yet, this starts one on port 8888 with JSON output enabled:

```bash
mkdir -p searxng && cat > searxng/settings.yml <<EOF
use_default_settings: true
server:
  secret_key: "$(openssl rand -hex 32)"
search:
  formats: [html, json]
EOF
docker run -d --name searxng -p 8888:8080 -v "$PWD/searxng:/etc/searxng" searxng/searxng
```

Check it with `curl "http://localhost:8888/search?q=test&format=json"`. Which engines answer depends on your network: some engines rate-limit or show CAPTCHAs, so enable or disable engines in `settings.yml` as needed. See the [SearXNG Docker guide](https://docs.searxng.org/admin/installation-docker.html) for a production setup.

**How results are combined:**

- `providers` (MCP, e.g. `["searxng"]`) or `--providers searxng,youcom` (CLI) narrows a call to a subset of the configured providers; unknown or unconfigured names return an error. Default: all configured providers.
- Results are merged round-robin with conservative URL dedup. Results returned by several providers come first, and every result lists its sources in `providers`. The list is capped at `max_results` (1–50).
- `language`, `time_range`, `safesearch` and `pageno` apply to both providers; `categories` and `engines` are SearXNG only. For You.com, `language` is mapped to its supported codes (e.g. `en-us` → `EN`; unsupported codes such as `zh` search without a language filter), and pages beyond 10 return no You.com results.
- If some providers fail, the results of the others are returned (the failure is logged as a warning). If all selected providers fail, search returns an error with a short reason per provider (no secrets, URLs or response bodies), e.g. `youcom: API key rejected, check YDC_API_KEY`.

**Environment variables:**

| Variable               | Example / Recommended                          | Description                                                                                                  |
| ---------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `SEARXNG_URL`          | (none)                                         | SearXNG instance URL, e.g. `http://localhost:8888`; enables SearXNG                                          |
| `SEARXNG_USERNAME`     | (none)                                         | Optional basic auth user (set both or neither)                                                               |
| `SEARXNG_PASSWORD`     | (none)                                         | Optional basic auth pass (set both or neither)                                                               |
| `SEARXNG_EXTRA_HEADERS`| (none)                                         | JSON object of extra SearXNG headers; see Cloudflare Access below. |
| `YDC_API_KEY`          | (none)                                         | You.com API key; enables You.com (queries go to You.com, US)                                                 |
| `SEARCH_RESULT_FIELDS` | `title,url,content,publishedDate,providers`    | Comma-separated result fields. Unset = all fields. Available: title, url, content, publishedDate, providers  |

**SearXNG behind Cloudflare Access:**

- Set extra headers for CLI and MCP search; they are never sent to You.com.
- Header names must be HTTP tokens; values must be ASCII strings without control characters.
- Values starting with `@` load UTF-8 files using absolute or `~/` paths. Surrounding file whitespace is stripped; relative paths are rejected.
- Invalid JSON, invalid headers or unreadable files disable SearXNG with a value-free warning. A configured You.com provider remains available.
- `Accept` and `Content-Type` remain `application/json`, regardless of header-name casing.
- Set `User-Agent` if your Cloudflare policy rejects the default Python client.

```bash
SEARXNG_EXTRA_HEADERS={"User-Agent":"searxncrawl","CF-Access-Client-Id":"@~/.config/searxncrawl/cf_id","CF-Access-Client-Secret":"@~/.config/searxncrawl/cf_secret"}
```

Example `.env`:
```bash
SEARXNG_URL=http://localhost:8888
# YDC_API_KEY=your-you.com-api-key
SEARCH_RESULT_FIELDS=title,url,content,publishedDate,providers
LOG_LEVEL=INFO
```

**Config file search order** (CLI tools only):

1. `./.env` — current directory
2. `~/.config/searxncrawl/.env` — user config

If no `.env` exists, `.env.example` is auto-copied to the user config path.

