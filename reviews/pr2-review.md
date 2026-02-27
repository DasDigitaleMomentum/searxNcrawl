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
**Verdict: Approve with follow-up requests (or request changes if strict parity is required before merge).**

Recommended follow-ups:
1. Add MCP/Python parity for persistent profile auth (`auth_profile` / `user_data_dir`).
2. Expose SPA run-config overrides consistently across CLI/MCP/Python convenience APIs.
3. Consider moving to argparse subparsers for `capture-auth`.
4. Optionally split future large feature+test PRs into smaller stacked PRs.

