# PR #2 Review: authenticated crawling + SPA support

## Scope reviewed
- Compared `upstream/main` (`f964455`) with `pr-2` (`49f8a78`).
- Diff size: 21 files changed, 3844 insertions, 132 deletions.

## Feature summary
PR #2 introduces a meaningful capability expansion centered on authenticated and JS-heavy crawling:

1. **Authentication layer**
   - Adds `AuthConfig` and browser config composition helpers for cookies, headers, storage state, and persistent profile contexts.
   - Adds env-var-based auth loading and profile discovery helpers.

2. **Interactive auth capture**
   - Adds `capture-auth` flow using headed Playwright to manually complete OAuth/SSO/MFA and export storage state.

3. **CLI support for auth + SPA timing**
   - Adds `--cookies`, `--header`, `--storage-state`, `--auth-profile`.
   - Adds SPA knobs: `--delay` and `--wait-until`.

4. **Python API threading**
   - Threads `auth` through `crawl_page(_async)`, `crawl_pages(_async)`, and site crawling.

5. **MCP tool updates**
   - Adds cookies/headers/storage-state params to `crawl` and `crawl_site`.
   - Adds `list_auth_profiles` MCP tool.

6. **Validation footprint**
   - Adds broad unit-test suite across auth/capture/CLI/MCP and core modules.

## Feature parity assessment

### What has good parity
- **Python API, CLI, MCP tooling** all support core auth primitives: cookies, headers, and storage-state.
- **Environment fallback** for auth is wired into CLI and MCP paths.

### Where parity is incomplete
1. **Persistent profile parity mismatch**
   - CLI supports `--auth-profile` (persistent context directory).
   - MCP tool signatures in PR #2 expose cookies/headers/storage_state, but not `auth_profile`/`user_data_dir`.
   - Result: same auth scenario can be done from CLI but not from MCP tool params.

2. **SPA controls parity mismatch**
   - CLI adds `--delay` and `--wait-until`.
   - MCP tools and public Python convenience APIs do not expose equivalent run-config overrides directly in the PR interface, so behavior differs by entrypoint.

3. **Claimed vs implemented parity in PR description**
   - PR text advertises composable auth methods including browser profile broadly, but only CLI appears to expose profile choice explicitly.

## Fit to project direction
Overall fit is **strong**:
- The project already positions itself as practical crawl/search tooling for real workflows.
- Authenticated crawling and SPA readiness are natural extensions and address real adoption blockers.

Potential fit concerns:
- The PR is very broad (new features + large test sweep + packaging/changelog edits), which increases review and regression risk in one shot.

## Architecture review

### Positive aspects
- **Separation of concerns**: introducing `crawler/auth.py` and `crawler/capture.py` keeps auth logic out of core crawl primitives.
- **Non-breaking style**: auth is optional and injected via `build_browser_config(auth)`; default behavior remains straightforward.
- **Composability**: auth source layering (explicit args > env) is pragmatic.

### Risks / design concerns
1. **CLI subcommand dispatch is hand-rolled**
   - `capture-auth` is detected before main parser setup instead of using argparse subparsers.
   - This is workable but tends to become harder to maintain as additional subcommands grow.

2. **Responsibility spread in CLI module**
   - `crawler/cli.py` continues accumulating config loading, formatting, auth parsing, crawl execution, and subcommand logic in one file.
   - Medium-term maintainability would improve by splitting auth argument parsing and command handlers into dedicated modules.

3. **Large all-at-once test introduction**
   - The test expansion is valuable, but bundling feature work and very large test scaffolding in one PR complicates pinpointing failures and review confidence.

## Recommendation
**Verdict: Request changes before merge if strict entrypoint parity is required.**

Recommended follow-ups:
1. Add MCP/Python parity for persistent profile auth (`auth_profile` / `user_data_dir`).
2. Expose SPA run-config overrides consistently across CLI/MCP/Python convenience APIs.
3. Consider moving to argparse subparsers for `capture-auth`.
4. Optionally split future large feature+test PRs into smaller stacked PRs.

---

## Implementation plan (for local follow-up)

This plan is intentionally sequenced so parity-critical gaps are fixed first and
the ergonomics refactor lands after functional parity is restored.

### Phase 1 — Restore auth parity across entrypoints (highest priority)

**Goal:** a user can choose all auth methods (including persistent profile) from
CLI, MCP tool params, and Python convenience APIs.

1. **Add MCP params for persistent profile auth**
   - Extend `crawl` and `crawl_site` MCP tool signatures to accept:
     - `auth_profile: Optional[str] = None`
     - `user_data_dir: Optional[str] = None` (if this is separately modeled)
   - Thread these through to the same auth-construction code path already used by
     CLI/API.
   - Update MCP docstrings/examples so expected precedence is explicit
     (explicit params > env defaults).

2. **Add Python convenience API parity**
   - Ensure high-level functions (`crawl_page(_async)`, `crawl_pages(_async)`,
     `crawl_site(_async)`) can receive profile-based auth inputs directly, not
     only low-level config objects.
   - Keep backward compatibility by adding optional args with defaults.

3. **Add regression tests for profile parity**
   - MCP tool tests: verify profile args are accepted and forwarded.
   - Python API tests: verify equivalent crawl config from CLI/MCP/API produces
     matching auth config semantics.

### Phase 2 — Restore SPA run-config parity

**Goal:** SPA behavior controls are consistently available regardless of entrypoint.

1. **Promote SPA knobs into shared config model**
   - Add/confirm shared runtime options for:
     - `delay`
     - `wait_until`
   - Ensure defaults remain unchanged where values are omitted.

2. **Expose knobs in MCP and convenience APIs**
   - Add optional args to MCP `crawl` and `crawl_site`.
   - Add matching optional args to Python convenience APIs.
   - Reuse one normalization/validation path to avoid divergent behavior.

3. **Add consistency tests**
   - Parameterized tests asserting CLI, MCP, and API all resolve equivalent
     runtime config given the same explicit inputs.

### Phase 3 — CLI maintainability cleanup (non-blocking but recommended)

**Goal:** reduce long-term CLI complexity before more commands are added.

1. **Move to argparse subparsers**
   - Introduce subcommands (e.g., `crawl`, `capture-auth`) using subparsers.
   - Preserve existing invocation compatibility if possible (deprecation warning
     if legacy forms are retained).

2. **Split CLI responsibilities**
   - Extract auth argument parsing + auth config assembly into dedicated module(s).
   - Extract command handlers from top-level parser/bootstrap code.

3. **Add smoke tests for subcommands**
   - Verify basic command dispatch and argument parsing paths.

---

## Definition of done for this PR update

Before considering the parity items closed, confirm all checks pass:

1. **Entrypoint parity matrix checked**
   - Persistent profile auth supported in CLI, MCP, and Python convenience APIs.
   - SPA controls supported in CLI, MCP, and Python convenience APIs.

2. **Behavioral consistency checked**
   - Equivalent inputs from each entrypoint produce equivalent effective crawl
     config (auth + SPA timing semantics).

3. **Docs updated**
   - README/API docs show auth and SPA options for each entrypoint.
   - Precedence rules (explicit > env) documented once and reused.

4. **Regression coverage present**
   - New tests guard MCP/API parity pathways and config normalization.

## Suggested local validation commands

Run these locally after implementing the plan:

```bash
# Unit tests
pytest -q

# CLI sanity checks (examples)
python -m crawler.cli --help
python -m crawler.cli capture-auth --help
python -m crawler.mcp_server --help

# Optional targeted test runs if suite is large
pytest -q -k "auth or mcp or cli"
```

---

## Re-check after latest PR #2 follow-up updates

This section records a fresh status check against the parity and implementation
expectations documented above.

### Current status snapshot

1. **Auth feature surface is still not present in active entrypoints**
   - `crawler/cli.py` currently exposes crawl/search arguments, but does not
     expose auth-focused options from the review goals (`--cookies`,
     `--header`, `--storage-state`, `--auth-profile`).
   - `crawler/mcp_server.py` `crawl`/`crawl_site` tools currently do not accept
     auth params (cookies/headers/storage state/profile).
   - `crawler/__init__.py` convenience APIs currently expose `config` and
     `concurrency`, but not profile/cookie/header/storage-state convenience
     inputs.

2. **SPA parity remains open**
   - CLI does not currently expose `--delay` / `--wait-until` knobs in the
     parser.
   - MCP tools do not expose `delay` / `wait_until`.
   - Python convenience API does not expose delay/wait overrides directly.

3. **Capture-auth / auth-profile operational path is still open**
   - No active `capture-auth` subcommand is currently wired in CLI.
   - No MCP tool for auth profile discovery is currently wired.

### Open points requiring action (detailed)

1. **Re-introduce/complete auth model + loaders (blocking)**
   - Add or restore explicit auth config model (cookies, headers,
     storage_state, auth_profile/user_data_dir).
   - Implement one normalization path for precedence:
     explicit args > profile > environment defaults.
   - Ensure config assembly is reusable by CLI, MCP, and Python API.

2. **Restore CLI parity (blocking)**
   - Extend `crawler/cli.py` crawl parser with auth args:
     `--cookies`, repeated `--header`, `--storage-state`, `--auth-profile`
     (and `--user-data-dir` if separately modeled).
   - Add SPA args: `--delay`, `--wait-until`.
   - Thread parsed values into shared config builder before crawl execution.

3. **Restore MCP parity (blocking)**
   - Extend `crawler/mcp_server.py` `crawl` and `crawl_site` signatures with
     auth and SPA params.
   - Forward these params into the same shared normalization path used by CLI.
   - Update tool docstrings/examples to document argument semantics and
     precedence.

4. **Restore Python convenience API parity (blocking)**
   - Extend `crawl_page(_async)`, `crawl_pages(_async)`, and `crawl_site(_async)`
     with optional auth + SPA convenience args.
   - Preserve backward compatibility by keeping existing args optional and
     defaults unchanged.

5. **Re-enable interactive auth workflow (high priority)**
   - Re-introduce `capture-auth` CLI flow for login-state capture.
   - Add profile listing utility (CLI and/or MCP) to discover saved auth
     profiles.

6. **Add regression coverage focused on parity contracts (high priority)**
   - CLI parsing tests for new auth + SPA args.
   - MCP tests validating signature acceptance and forwarding behavior.
   - API tests validating equivalent effective config across CLI/MCP/API inputs.

7. **Update end-user documentation (required before close)**
   - README sections for CLI, Python API, and MCP parameters must each include
     auth + SPA usage examples.
   - Add one shared precedence note (explicit > profile > env) referenced from
     all entrypoint docs.
