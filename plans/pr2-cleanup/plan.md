---
type: planning
entity: plan
plan: pr2-cleanup
status: active
created: 2026-02-27
updated: 2026-02-27
---

# Plan: PR #2 Cleanup & Feature Completion

## Objective

Finalize PR #2 (`feature/authenticated-crawling`) by resolving the stale review, adding missing real-world E2E tests, closing the Search parity gap (Python API), and updating all documentation (README + docs/) to reflect the full feature set.

## Motivation

PR #2 introduced authenticated crawling, SPA support, and auth capture. A review was conducted (`reviews/pr2-review.md`) but is now **stale** — the cited parity gaps (MCP auth_profile, SPA params, list_auth_profiles) have all been fixed within the PR. The review file should be removed to avoid confusion.

Additionally:
- **No real-world E2E tests** exist for auth crawling, auth capture, SPA rendering, or direct CLI invocation.
- **Search has no Python API** — it's only available via MCP and CLI, breaking the 3-interface parity pattern.
- **README and docs/** are stale — auth params, SPA params, capture-auth CLI, and auth env vars are undocumented.

## Requirements

### Functional

- [ ] Remove stale review file (`reviews/pr2-review.md`)
- [ ] Real-world E2E tests for auth crawling (at minimum: cookies, storage-state)
- [ ] Real-world E2E tests for SPA crawling (delay + wait-until on a JS-rendered page)
- [ ] Real-world E2E test for CLI commands (direct invocation, not only MCP HTTP)
- [ ] `search_async()` / `search()` convenience functions in Python API (`crawler/__init__.py`)
- [ ] CLI `--pageno` argument for search pagination
- [ ] Unit tests for new search Python API functions
- [ ] README documents all features: auth, SPA, capture-auth, list_auth_profiles, auth env vars
- [ ] `docs/` updated to match final code state

### Non-Functional

- [ ] Existing non-E2E test suite continues to pass with no regressions
- [ ] Real-world tests are pytest-marked (e.g., `@pytest.mark.e2e`) and skippable in CI
- [ ] Documentation is consistent across README, docs/, and code docstrings

## Scope

### In Scope

- Review cleanup (delete file, no GitHub review to update — no formal reviews exist)
- E2E test creation for untested features
- Search parity: Python API functions + CLI pageno
- README full rewrite of feature sections
- docs/ update via update-docs skill

### Out of Scope

- CLI architecture refactor (argparse subparsers) — deferred to separate PR
- New features beyond what PR #2 already implements
- CI/CD pipeline changes

## Definition of Done

- [ ] `reviews/pr2-review.md` deleted
- [ ] No `pr2-review` references remain outside `plans/`
- [ ] E2E tests exist and pass for: auth crawling, SPA crawling, CLI direct invocation
- [ ] `search_async()` available in Python API with full SearXNG parameter support
- [ ] CLI search has `--pageno` flag
- [ ] Existing non-E2E suite passes, new tests pass, and no test regressions are introduced
- [ ] README accurately documents every feature and parameter
- [ ] `docs/` reflects final code state
- [ ] PR #2 is merged (✅ done)

## Testing Strategy

- [ ] Regression baseline: `pytest tests/ -m "not e2e"` (existing non-E2E suite)
- [ ] New E2E tests: `pytest tests/ -m e2e` (requires running SearXNG + network)
- [ ] Shell E2E scripts: `scripts/test-realworld.sh`, `scripts/test-extended.sh`
- [ ] Manual verification: README examples are accurate

## Phases

| Phase | Title                      | Scope                                               | Status  |
| ----- | -------------------------- | --------------------------------------------------- | ------- |
| 1     | Review Cleanup             | Delete stale review file, verify no dangling refs    | pending |
| 2     | E2E Test Coverage          | Add real-world tests for auth, SPA, CLI              | pending |
| 3     | Search Parity              | Python API search functions + CLI pageno + tests     | pending |
| 4     | Documentation Update       | README rewrite + docs/ update                        | pending |

## Risks & Open Questions

| Risk                                        | Impact | Mitigation                                              |
| ------------------------------------------- | ------ | ------------------------------------------------------- |
| E2E tests need running SearXNG instance     | Low    | Local `.env` has `SEARXNG_URL` configured; skip guards for CI |
| External-network E2E targets can be flaky   | Medium | Add dependency probes + explicit skip guards; keep deterministic must-pass subset |
| Auth E2E needs a protected target           | Medium | Use httpbin.org (public) with probe + best-effort assertions |
| SPA E2E needs a JS-rendered page            | Low    | Use stable target + delay/wait-until pipeline checks, guarded when unavailable |
| Search Python API may need httpx dependency | None   | Already in dependencies for MCP search                   |

## Sequencing Guard

- [ ] Phase 4 documentation updates run only after Phase 3 API/CLI signatures are finalized and stable (no speculative interface docs)

## Environment Notes

- A **gitignored `.env`** exists in repo root with `SEARXNG_URL` and `MCP_PORT`. This file is not visible via `git ls-files` but is present on the filesystem.
- The CLI auto-loads `.env` via `_load_env_config()` (fallback chain: `CWD/.env` → `~/.config/searxncrawl/.env` → auto-create from `.env.example`).
- `.env.example` documents all supported env vars including auth: `CRAWL_AUTH_STORAGE_STATE`, `CRAWL_AUTH_COOKIES_FILE`, `CRAWL_AUTH_PROFILE`.
- E2E tests should work out of the box locally since `.env` provides `SEARXNG_URL`.
- `.gitignore` also ignores: `auth_state*.json`, `*_cookies.json`, `*_auth.json`, `profiles/`.

## Changelog

- **2026-02-27**: PR #2 merged into main. Plan updated: branch references corrected, `.env` notes added, risk table adjusted.
- **2026-02-27**: Plan created. Based on code audit of `feature/authenticated-crawling` branch (commit 2a08d7a). Review confirmed stale — all cited parity gaps already fixed.
