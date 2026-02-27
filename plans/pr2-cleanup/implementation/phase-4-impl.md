---
type: planning
entity: implementation-plan
plan: pr2-cleanup
phase: 4
status: draft
created: 2026-02-27
updated: 2026-02-27
---

# Implementation Plan: Phase 4 — Documentation Update

> Implements [Phase 4](../phases/phase-4.md) of [pr2-cleanup](../plan.md)

## Approach

Update the three documentation layers — README.md (user-facing), docs/ (developer-facing), and CHANGELOG.md (release notes) — to accurately reflect the complete feature set after Phases 1-3.

Documentation updates are sequenced behind a hard guard: do not run final docs edits until Phase 3 API/CLI signatures are finalized. This phase documents shipped interfaces only (no speculative signatures).

The work divides into four streams:

1. **README.md rewrite**: The README is the primary user-facing document. It currently documents the original crawl/search features but is missing auth params on MCP tools, the `list_auth_profiles` tool, authenticated crawling concepts, `capture-auth` CLI, SPA rendering, Python API auth/search usage, CLI auth/SPA args, auth env vars, and the updated feature list. Additionally, Phase 3 adds `search_async()`/`search()` to the Python API and `--pageno` to the CLI — these must be documented.

2. **docs/ update**: After Phase 3, the search module gains a shared implementation (`crawler/search.py` or equivalent), `search_async`/`search` functions in `__init__.py`, and a `SearchResult` type. The docs must reflect these new exports, the refactored search data flow, and any new file in the module structure. Update via the `update-docs` skill.

3. **CHANGELOG.md**: Add entries for Phase 3's search parity additions (Python API search, CLI `--pageno`). The existing `[0.2.0]` entry covers auth features but does not include search parity.

4. **Cross-reference validation**: Verify all links between README, docs/overview.md, docs/features/, and docs/modules/ remain valid.

## Affected Modules

| Module/File | Change Type | Description |
|-------------|-------------|-------------|
| `README.md` | major update | Add auth, SPA, capture-auth, list_auth_profiles; update MCP tool param tables, Python API, CLI, env vars, feature list |
| `CHANGELOG.md` | append | Add search parity entries to `[0.2.0]` section |
| `docs/overview.md` | minor update | Update test count, verify env var table, update module description if search module added |
| `docs/modules/crawler-core.md` | update | Add `search_async`, `search`, `SearchResult` symbols; add `crawler/search.py` if Phase 3 created it; update `__all__` listing |
| `docs/features/searxng-search.md` | update | Add Python API row to implementation table; update "No pagination in CLI" note (Phase 3 adds `--pageno`); add `SearchResult` type |
| `docs/features/cli.md` | update | Add `--pageno` to search command arguments table |
| `docs/features/mcp-server.md` | minor update | Verify line numbers still accurate after Phase 3 refactor |
| `docs/features/web-crawling.md` | verify | No content changes expected, just verify cross-refs |
| `docs/features/authenticated-crawling.md` | verify | No content changes expected, just verify cross-refs |
| `docs/features/auth-capture.md` | verify | No content changes expected, just verify cross-refs |
| `docs/modules/tests.md` | update | Update test count to reflect new Phase 2 & 3 tests |

## Required Context

| File | Why |
|------|-----|
| `README.md` | Current state: 548 lines, missing auth/SPA/search-parity sections. Must identify every section to update. |
| `CHANGELOG.md` | Current state: 60 lines, `[0.2.0]` entry covers auth. Need to add search parity entries. |
| `crawler/mcp_server.py` | Source of truth for all MCP tool parameters (crawl: L229, crawl_site: L353, search: L508, list_auth_profiles: L461) |
| `crawler/__init__.py` | Source of truth for Python API exports. Phase 3 will add `search_async`, `search`, `SearchResult` to `__all__`. |
| `crawler/cli.py` | Source of truth for CLI arguments. Phase 3 will add `--pageno` to search parser. |
| `crawler/auth.py` | AuthConfig fields and env var loading — needed for documenting auth methods |
| `crawler/capture.py` | capture_auth_state params — needed for documenting capture-auth CLI |
| `docs/overview.md` | Cross-reference hub: module table, feature table, env var table |
| `docs/modules/crawler-core.md` | Module inventory: all symbols, structure, data flow sections |
| `docs/features/searxng-search.md` | Search feature doc: implementation table, parameter table, limitations |
| `docs/features/cli.md` | CLI feature doc: all argument tables |
| `plans/pr2-cleanup/phases/phase-3.md` | Phase 3 scope: defines what search_async/SearchResult will look like |

## Implementation Steps

### Step 1: Update README — Feature List

- **What**: Expand the Features section (README L9-32) to include authenticated crawling, auth capture, SPA/JS rendering, and the `list_auth_profiles` tool
- **Where**: `README.md` lines 9-32 (Features section)
- **Why**: The current feature list only covers basic crawling, search, CLI, and MCP. The auth features from v0.2.0 and Phase 3's search parity are not mentioned.
- **New content**:
  ```markdown
  ### Authenticated Crawling
  - **Cookies injection** - Pass session cookies directly
  - **Custom headers** - Add `Authorization: Bearer` or any headers
  - **Storage state** - Reuse Playwright browser state (cookies + localStorage)
  - **Persistent profiles** - Saved browser profiles across crawls
  - **Environment defaults** - Set auth via `CRAWL_AUTH_*` env vars

  ### Auth Session Capture
  - **Interactive login** - Opens a headed browser for manual login
  - **Storage state export** - Saves cookies + localStorage as JSON
  - **Auto-capture** - Optional URL-match trigger (`--wait-for-url`)
  - **Profile support** - Save to named persistent profiles

  ### SPA / JavaScript Rendering
  - **Page load delay** - Wait for JS content to render (`--delay`)
  - **Wait strategies** - `load`, `domcontentloaded`, `networkidle`, `commit`
  ```
- **Considerations**: Keep the existing Web Crawling, Web Search, CLI Tools, and MCP Server subsections. Add new subsections after Web Search. Update CLI Tools to mention `capture-auth`. Update MCP Server to mention `list_auth_profiles`.

### Step 2: Update README — MCP Tool Parameter Tables

- **What**: Add missing parameters to the `crawl` and `crawl_site` tables, and add the `list_auth_profiles` tool section
- **Where**: `README.md` lines 208-300 (MCP Tools section)
- **Why**: The current tables only show 4 params for `crawl` and 6 for `crawl_site`. Both tools have 10 params each in code. `list_auth_profiles` is not documented.
- **`crawl` table — add these rows**:

  | Parameter | Type | Default | Description |
  |-----------|------|---------|-------------|
  | `cookies` | `List[Dict[str,str]]` | `null` | Cookie dicts for auth (`name`, `value`, `domain`) |
  | `headers` | `Dict[str,str]` | `null` | Custom HTTP headers (e.g. `Authorization: Bearer xyz`) |
  | `storage_state` | `str` | `null` | Path to Playwright storage state JSON file |
  | `auth_profile` | `str` | `null` | Path to persistent browser profile directory |
  | `delay` | `float` | `null` | Seconds to wait after page load (SPA/JS) |
  | `wait_until` | `str` | `null` | Wait event: `load`, `domcontentloaded`, `networkidle`, `commit` |

- **`crawl_site` table — add same 6 rows** (identical params, same defaults)

- **Add `list_auth_profiles` section** after `crawl_site`:
  ```markdown
  #### `list_auth_profiles`

  List available persistent browser profiles for authenticated crawling.

  **Parameters:** None

  **Returns:** JSON string with list of profiles, each with `name`, `path`, and `modified` timestamp.

  **Example:**
  ```
  list_auth_profiles()
  ```
  ```

- **Update `crawl` and `crawl_site` examples** to show auth and SPA usage
- **Considerations**: Preserve existing examples, add new ones. Reference code: `mcp_server.py:229-299` (crawl docstring has excellent examples).

### Step 3: Update README — Authenticated Crawling Section

- **What**: Add a new top-level section "Authenticated Crawling" between Python API and CLI Usage
- **Where**: `README.md`, new section after line 436 (after Python API section)
- **Why**: Auth is a major v0.2.0 feature with no README documentation. Users need to understand concepts, methods, and examples.
- **New content**:
  ```markdown
  ## Authenticated Crawling

  Crawl pages behind login walls (OAuth, SSO, MFA) by providing authentication context.

  ### Auth Methods

  | Method | CLI Flag | MCP Param | Env Var | Description |
  |--------|----------|-----------|---------|-------------|
  | Cookies | `--cookies` | `cookies` | `CRAWL_AUTH_COOKIES_FILE` | JSON string, file path, or list of cookie dicts |
  | Headers | `--header` (repeat) | `headers` | -- | Custom HTTP headers |
  | Storage state | `--storage-state` | `storage_state` | `CRAWL_AUTH_STORAGE_STATE` | Playwright storage state JSON |
  | Browser profile | `--auth-profile` | `auth_profile` | `CRAWL_AUTH_PROFILE` | Persistent Chromium profile |

  ### Priority Order

  Explicit parameters (CLI/MCP/API) > Environment variables > No auth

  ### Python API

  ```python
  from crawler import crawl_page_async
  from crawler.auth import AuthConfig

  # With storage state
  auth = AuthConfig(storage_state="./auth_state.json")
  doc = await crawl_page_async("https://protected.example.com", auth=auth)

  # With cookies
  auth = AuthConfig(cookies=[{"name": "sid", "value": "abc", "domain": ".example.com"}])
  doc = await crawl_page_async("https://protected.example.com", auth=auth)

  # With headers
  auth = AuthConfig(headers={"Authorization": "Bearer xyz123"})
  doc = await crawl_page_async("https://api.example.com/docs", auth=auth)
  ```

  ### Quick Start

  ```bash
  # 1. Capture a login session interactively
  crawl capture-auth --url https://login.example.com

  # 2. Use the captured session for crawling
  crawl --storage-state auth_state.json https://protected.example.com

  # Or set as environment default for all crawls
  export CRAWL_AUTH_STORAGE_STATE=./auth_state.json
  crawl https://protected.example.com
  ```
  ```
- **Considerations**: Keep it concise — link to detailed auth-capture examples rather than duplicating.

### Step 4: Update README — Auth Capture CLI Section

- **What**: Add `capture-auth` documentation to the CLI Usage section
- **Where**: `README.md` CLI Usage section (after the `search` subsection, around line 492)
- **Why**: `capture-auth` is a subcommand of `crawl` but is not documented in the README at all
- **New content**:
  ```markdown
  ### capture-auth

  Capture a login session interactively for reuse with authenticated crawling.

  ```bash
  # Open browser for login, export storage state
  crawl capture-auth --url https://login.example.com

  # Export to specific file
  crawl capture-auth --url https://login.example.com --output my_auth.json

  # Use persistent browser profile
  crawl capture-auth --url https://login.example.com --profile my-site

  # Auto-capture when redirected to dashboard
  crawl capture-auth --url https://login.example.com --wait-for-url "/dashboard"

  # With custom timeout (default: 300s)
  crawl capture-auth --url https://login.example.com --timeout 600
  ```
  ```
- **Considerations**: Source of truth: `cli.py:421-487` (`_parse_capture_auth_args`). Include all 5 flags: `--url`, `--output`, `--wait-for-url`, `--timeout`, `--profile`.

### Step 5: Update README — SPA / JS Rendering Section

- **What**: Add a section about crawling SPA/JS-rendered pages
- **Where**: `README.md`, new section between Authenticated Crawling and CLI Usage
- **Why**: The `delay` and `wait_until` parameters are on MCP tools and CLI but not explained anywhere in README
- **New content**:
  ```markdown
  ## SPA / JavaScript Rendering

  For single-page applications (SPAs) and JS-heavy sites, use the delay and wait strategy parameters:

  ```bash
  # CLI: Wait 3 seconds after page load
  crawl https://spa.example.com --delay 3

  # CLI: Wait for all network requests to finish
  crawl https://spa.example.com --wait-until networkidle

  # CLI: Combined (recommended for complex SPAs)
  crawl https://spa.example.com --delay 3 --wait-until networkidle
  ```

  ```python
  # Python API
  from crawler import crawl_page_async
  from crawler.config import build_markdown_run_config

  config = build_markdown_run_config()
  config.delay_before_return_html = 3.0
  config.wait_until = "networkidle"
  doc = await crawl_page_async("https://spa.example.com", config=config)
  ```

  | Wait Strategy | Description | Use When |
  |---------------|-------------|----------|
  | `load` | Default — waits for `load` event | Most static sites |
  | `domcontentloaded` | DOM parsed, stylesheets may still load | Fast initial render |
  | `networkidle` | No network activity for 500ms | SPAs that fetch data via API |
  | `commit` | First byte received | Fastest, for known-quick pages |
  ```
- **Considerations**: Reference code: `mcp_server.py:261-264` (delay/wait_until docstring), `cli.py:391-406` (SPA CLI group).

### Step 6: Update README — Python API Section (Auth + Search)

- **What**: Add auth examples to existing Python API section; add search API examples (Phase 3 deliverables)
- **Where**: `README.md` lines 375-436 (Python API section)
- **Why**: Python API examples currently show no auth usage and no search. Phase 3 adds `search_async()` / `search()`.
- **Add `auth=` parameter to existing examples** (add a brief note after each code block):
  ```python
  # All crawl functions accept an optional auth= parameter
  from crawler.auth import AuthConfig
  auth = AuthConfig(storage_state="./auth_state.json")
  doc = crawl_page("https://protected.example.com", auth=auth)
  ```
- **Add search section**:
  ```markdown
  ### Search

  ```python
  from crawler import search_async, search, SearchResult

  # Async search
  result: SearchResult = await search_async("python tutorials")
  print(result.query)
  print(f"Found {result.number_of_results} results")
  for r in result.results:
      print(f"  {r['title']} - {r['url']}")

  # Sync search
  result = search("python tutorials", language="de", max_results=5)

  # With pagination
  page2 = search("python tutorials", pageno=2)

  # All parameters
  result = await search_async(
      "AI news",
      language="en",
      time_range="week",
      categories=["news"],
      safesearch=1,
      pageno=1,
      max_results=20,
  )
  ```
  ```
- **Considerations**: The exact `SearchResult` type is defined by Phase 3. Per phase-3.md: `query`, `number_of_results`, `results[]`, `answers[]`, `suggestions[]`, `corrections[]`. Document based on that specification.

### Step 7: Update README — CLI Arguments (Auth + SPA + --pageno)

- **What**: Update crawl CLI examples to show auth and SPA flags; add `--pageno` to search CLI
- **Where**: `README.md` lines 438-493 (CLI Usage section)
- **Why**: CLI auth flags (`--cookies`, `--header`, `--storage-state`, `--auth-profile`), SPA flags (`--delay`, `--wait-until`), and `--pageno` are not shown
- **Add to crawl examples**:
  ```bash
  # Authenticated crawl with storage state
  crawl --storage-state auth_state.json https://protected.example.com

  # With custom headers
  crawl --header "Authorization: Bearer xyz" https://api.example.com/docs

  # SPA with auth combined
  crawl --storage-state auth.json --delay 3 --wait-until networkidle https://spa.example.com
  ```
- **Add to search examples**:
  ```bash
  # Page 2 of results
  search "python tutorials" --pageno 2
  ```
- **Considerations**: The crawl command help epilog at `cli.py:306-331` already has excellent examples to draw from.

### Step 8: Update README — Environment Variables Table

- **What**: Add auth-related env vars to the Environment Variables table
- **Where**: `README.md` lines 70-75 (Environment Variables table)
- **Why**: Only 3 SearXNG vars are documented. The 3 `CRAWL_AUTH_*` vars and `MCP_PORT` are missing.
- **Add rows**:

  | Variable | Default | Description |
  |----------|---------|-------------|
  | `CRAWL_AUTH_STORAGE_STATE` | (none) | Default Playwright storage state JSON path |
  | `CRAWL_AUTH_COOKIES_FILE` | (none) | Default cookies JSON file path |
  | `CRAWL_AUTH_PROFILE` | (none) | Default persistent browser profile directory |
  | `MCP_PORT` | `9555` | HTTP port for Docker deployment |

- **Considerations**: `docs/overview.md` already has these vars (L155-158). Align README to match. Source of truth: `mcp_server.py:24-27` (module docstring), `auth.py:147+` (`load_auth_from_env`).

### Step 9: Update CHANGELOG.md

- **What**: Add Phase 3 search parity entries to the `[0.2.0]` section
- **Where**: `CHANGELOG.md` lines 8-27 (`[0.2.0]` section)
- **Why**: Phase 3 adds new features (Python API search, CLI `--pageno`) that belong in the same release changelog
- **Add to `### Added` block** (after existing entries, before the `---`):
  ```markdown
  - **Python API search** - `search_async()` and `search()` convenience functions
    - Full SearXNG parameter support (query, language, time_range, categories, engines, safesearch, pageno, max_results)
    - Returns structured `SearchResult` dataclass
  - **CLI `--pageno`** - Pagination support for the `search` command
  - **Shared search module** - Unified search implementation across MCP, CLI, and Python API
  ```
- **Also add a `### Changed` block** if Phase 3 refactored search out of `mcp_server.py`:
  ```markdown
  ### Changed
  - Search logic extracted from `mcp_server.py` into shared module to eliminate duplication
  ```
- **Considerations**: Follow the existing Keep a Changelog format. Entries should describe user-visible features, not implementation details.

### Step 10: Update docs/ via update-docs Skill

- **What**: Update `docs/` to reflect Phase 3 changes using the update-docs skill, only after Phase 3 signatures are frozen
- **Where**: Multiple docs/ files (see Affected Modules table)
- **Why**: Phase 3 adds new symbols (`search_async`, `search`, `SearchResult`), possibly a new file (`crawler/search.py`), a new CLI arg (`--pageno`), and removes duplication from `mcp_server.py` and `cli.py`
- **Specific updates needed**:

  **`docs/modules/crawler-core.md`:**
  - Structure table: add `crawler/search.py` row if it exists
  - `crawler/__init__.py` symbols: add `search_async`, `search`, `SearchResult` to key symbols table
  - `crawler/search.py` symbols: add section with shared search function(s)
  - `crawler/cli.py` symbols: verify `_parse_search_args` includes `--pageno`
  - Data Flow > Search: update to describe the new shared flow (Python API -> shared module <- MCP <- CLI)

  **`docs/features/searxng-search.md`:**
  - Implementation table: add row for Python API (`search_async`, `search` in `__init__.py`)
  - Add row for shared search module if created
  - Parameter table: add `pageno` to CLI Flag column (currently listed as N/A under "No pagination in CLI")
  - Edge Cases: remove or update "No pagination in CLI" note
  - Update line numbers if search tool moved from `mcp_server.py`

  **`docs/features/cli.md`:**
  - Search Command Arguments table: add `--pageno` row:
    | `--pageno` | int | 1 | Page number for results |

  **`docs/features/mcp-server.md`:**
  - Verify line number references (Phase 3 may have changed MCP tool line positions if search was extracted)

  **`docs/overview.md`:**
  - Replace stale fixed-count wording in Modules table with non-brittle baseline/regression wording
  - Verify module table entries are still accurate

  **`docs/modules/tests.md`:**
  - Update test counts and add entries for new Phase 2/3 test files

- **Considerations**: Use the update-docs skill for systematic updates. Re-read source files after Phase 3 completion to get accurate line numbers and symbol names. Do NOT guess — Phase 3 implementation details (file names, exact signatures) must be verified from code.

### Step 11: Correct stale test-module documentation claims

- **What**: Explicitly update `docs/modules/tests.md` to remove stale claims about total test count, coverage wording, and E2E responsibility/scope
- **Where**: `docs/modules/tests.md`
- **Why**: Current planning artifacts already flag test-count drift and stale test-doc assertions; this must be corrected as part of Phase 4 acceptance
- **Considerations**: Keep wording non-brittle where possible (avoid fixed counts unless generated directly from current test inventory)

### Step 12: Cross-Reference Validation

- **What**: Verify all inter-document links work correctly
- **Where**: All `docs/` files and README.md
- **Why**: Phase 3 code changes may shift line numbers; new files may need linking
- **Checks**:
  1. Every `[Detail](...)` link in `docs/overview.md` resolves to an existing file
  2. Every `[crawler-core](../modules/crawler-core.md)` link in feature docs works
  3. Every `[Feature](../features/...)` cross-link in Related Features sections works
  4. Line numbers in module docs (e.g. `mcp_server.py:508`) are still accurate post-Phase 3
  5. README internal section links (if any) are valid
- **Considerations**: Line-number references in docs may need bulk updating. Consider whether to keep exact line numbers or switch to symbol-only references for maintainability.

## Verify Command

```bash
# Verify all documentation files exist and are non-empty
for f in README.md CHANGELOG.md docs/overview.md docs/modules/crawler-core.md docs/features/searxng-search.md docs/features/cli.md docs/features/mcp-server.md; do
  test -s "$f" || echo "MISSING or EMPTY: $f"
done

# Verify no broken relative links in docs/ (basic check)
grep -roh '\[.*\](\.\.\/[^)]*)\|(\.\./[^)]*)' docs/ | grep -oP '\.\./[^)]+' | sort -u | while read link; do
  base="docs/features"
  target="$base/$link"
  test -f "$target" || echo "BROKEN LINK: $link (from docs/features/)"
done

# Verify README mentions key features
grep -q "list_auth_profiles" README.md && echo "OK: list_auth_profiles documented" || echo "MISSING: list_auth_profiles"
grep -q "capture-auth" README.md && echo "OK: capture-auth documented" || echo "MISSING: capture-auth"
grep -q "CRAWL_AUTH_STORAGE_STATE" README.md && echo "OK: auth env vars documented" || echo "MISSING: auth env vars"
grep -q "search_async\|search()" README.md && echo "OK: Python API search documented" || echo "MISSING: Python search API"
grep -q "\-\-pageno" README.md && echo "OK: --pageno documented" || echo "MISSING: --pageno"
grep -q "networkidle" README.md && echo "OK: SPA documented" || echo "MISSING: SPA section"

# Run existing tests to ensure no doc-related breakage
pytest tests/ -q
```

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Content verification | `grep -c "cookies" README.md` in MCP tool tables | > 0 — param is documented |
| Content verification | `grep -c "list_auth_profiles" README.md` | > 0 — tool is documented |
| Content verification | `grep -c "capture-auth" README.md` | > 0 — subcommand is documented |
| Content verification | `grep -c "CRAWL_AUTH_STORAGE_STATE" README.md` | > 0 — env var is documented |
| Content verification | `grep -c "search_async" README.md` | > 0 — Python API search is documented |
| Content verification | `grep -c "pageno" README.md` | > 0 — pagination is documented |
| Content verification | `grep -c "networkidle" README.md` | > 0 — SPA wait strategy is documented |
| CHANGELOG format | Manual review of `[0.2.0]` section | Follows Keep a Changelog format |
| Cross-references | All `[Detail](...)` links in docs/overview.md | Resolve to existing files |
| Line numbers | Line refs in docs/modules/crawler-core.md | Match actual source file positions |
| Existing tests | `pytest tests/ -q` | All tests pass (no regressions from doc changes) |
| Manual review | README examples match actual CLI/API behavior | Examples are copy-pasteable and correct |

## Rollback Strategy

Documentation changes are low-risk and fully reversible:

```bash
# Revert all documentation changes
git checkout HEAD~1 -- README.md CHANGELOG.md docs/

# Or revert the entire commit
git revert HEAD
```

Since Phase 4 is documentation-only (no code changes), there is zero risk of breaking functionality. The worst case is inaccurate documentation, which can be incrementally corrected.

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `README.md` (548 lines) | Full content | Identifies all sections needing update: Features (L9-32), Env Vars (L70-75), MCP Tools crawl table (L215-220), crawl_site table (L245-250), search table (L273-281), Python API (L375-436), CLI Usage (L438-493) |
| `CHANGELOG.md` (60 lines) | `[0.2.0]` section (L8-27) | Confirms auth features are documented; search parity entries are missing |
| `crawler/mcp_server.py:229` | `crawl()` signature | 10 params: urls, output_format, concurrency, remove_links, cookies, headers, storage_state, auth_profile, delay, wait_until — README only shows first 4 |
| `crawler/mcp_server.py:353` | `crawl_site()` signature | 12 params (url, max_depth, max_pages, include_subdomains + same 8) — README only shows first 6 |
| `crawler/mcp_server.py:461` | `list_auth_profiles()` | Exists in code, completely absent from README |
| `crawler/mcp_server.py:508` | `search()` signature | 8 params, all documented in README — no changes needed for this tool |
| `crawler/cli.py:265-293` | `_add_auth_args()` | Defines 4 auth CLI flags: --cookies, --header, --storage-state, --auth-profile — not in README |
| `crawler/cli.py:391-406` | SPA arg group | Defines --delay, --wait-until CLI flags — not in README |
| `crawler/cli.py:421-487` | `_parse_capture_auth_args()` | Defines capture-auth subcommand flags — not in README |
| `crawler/cli.py:634-722` | `_parse_search_args()` | Currently has NO `--pageno` — Phase 3 will add it |
| `crawler/__init__.py:54-76` | `__all__` | Currently has NO `search_async`/`search`/`SearchResult` — Phase 3 will add them |
| `docs/overview.md:155-158` | Auth env vars | Already documented in overview, need to align README |
| `docs/features/searxng-search.md:84` | "No pagination in CLI" note | Will be outdated after Phase 3 adds `--pageno` |
| `docs/features/cli.md:137-150` | Search Command Arguments table | Missing `--pageno` — Phase 3 will add |

### Mismatches / Notes

- **Phase 3 dependency**: Steps 6, 7, 9, and 10 depend on Phase 3 being complete. The exact names of `SearchResult` fields, the location of the shared search module (if extracted to `crawler/search.py`), and the `--pageno` flag must be verified from the actual Phase 3 implementation before writing documentation. Do NOT document speculative APIs — wait for Phase 3 completion.
- **README restructuring**: The new sections (Authenticated Crawling, SPA, capture-auth) significantly expand the README. Consider the insertion order carefully to maintain logical flow: Installation > MCP Server > MCP Tools > Python API > **Authenticated Crawling** > **SPA** > CLI Usage (with **capture-auth** subsection) > CrawledDocument > Configuration > Dependencies.
- **Test count drift**: Docs/plans may contain stale fixed test counts. The implementer must avoid hardcoding totals and rely on regression checks (`pytest tests/ -m "not e2e"`, `pytest tests/`) plus refreshed docs wording.
- **Line number fragility**: Multiple docs files reference source code line numbers (e.g., `mcp_server.py:508`). If Phase 3 extracts search logic into a separate module, ALL line numbers in docs may shift. The implementer should update these via grep after all code changes are final.
- **`docs/modules/tests.md`**: Not read in this analysis but will need updating for new test file entries from Phases 2 and 3.
