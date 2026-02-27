---
type: planning
entity: phase
plan: pr2-cleanup
phase: 2
status: pending
created: 2026-02-27
updated: 2026-02-27
---

# Phase 2: E2E Test Coverage

## Objective

Add real-world end-to-end tests for features that currently only have mocked unit tests: authenticated crawling, SPA rendering, and direct CLI invocation.

## Scope

### Includes

- Create `tests/test_e2e.py` (or similar) with `@pytest.mark.e2e` marker
- Configure pytest marker in `pyproject.toml` so `e2e` is a registered marker
- E2E tests for:
  - **Auth crawling with cookies**: Crawl a basic-auth or cookie-protected page
  - **Auth crawling with storage-state**: Use a stored auth state file
  - **SPA crawling**: Crawl a JS-rendered page with `delay` and/or `wait-until`
  - **CLI direct invocation**: Run `python -m crawler` / CLI entry point directly, validate output
  - **CLI search**: Run search via CLI, validate output format
  - **CLI capture-auth**: Verify capture-auth subcommand starts (headless check or quick timeout)
- Update shell scripts if needed to cover new scenarios

### Excludes

- Auth capture interactive flow (requires headed browser + human interaction — not automatable in CI)
- Changes to existing mocked unit tests
- CI pipeline configuration

## Prerequisites

- [ ] Phase 1 completed (clean working state)
- [ ] Local `.env` with `SEARXNG_URL` configured (gitignored, already present in repo)
- [ ] Network access for real-world URL crawling

## Deliverables

- [ ] `tests/test_e2e.py` with `@pytest.mark.e2e` marker on all tests
- [ ] `pyproject.toml` updated with `e2e` marker registration
- [ ] Minimum 8 E2E tests covering the gaps identified in audit
- [ ] External-target E2E tests use dependency probes and explicit skip guards
- [ ] Deterministic must-pass subset defined for local/CI baseline (independent of flaky external targets)
- [ ] All E2E tests pass with `pytest tests/test_e2e.py -m e2e`

## Acceptance Criteria

- [ ] `pytest tests/ -m "not e2e"` — existing non-E2E suite still passes with no regressions
- [ ] `pytest tests/test_e2e.py -m e2e` — guarded E2E tests pass when dependencies are available
- [ ] External-target E2E cases are best-effort/skippable via probes (network, SearXNG, Playwright)
- [ ] Deterministic local/CI baseline remains passable even when external targets are unavailable
- [ ] Auth crawling test successfully retrieves protected content
- [ ] SPA test successfully renders JS content with delay/wait-until
- [ ] CLI tests validate actual command output (not just arg parsing)

## Dependencies on Other Phases

| Phase | Dependency Type | Description                                |
| ----- | --------------- | ------------------------------------------ |
| 1     | Must complete   | Clean state before adding new test files   |

## Notes

- A **gitignored `.env`** exists in repo root with `SEARXNG_URL` and `MCP_PORT`. The CLI auto-loads it. E2E tests should work out of the box locally.
- For auth testing, use `httpbin.org/cookies` for cookie echo (public, stable).
- For SPA testing, use `example.com` with `delay`/`wait-until` to validate the pipeline.
- All E2E tests MUST be skippable: `pytest.mark.skipif` when dependencies aren't available (network, SearXNG, Playwright).
- Keep `e2e` marker registration mandatory so deterministic baseline commands can exclude external tests cleanly.
