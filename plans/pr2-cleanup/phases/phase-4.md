---
type: planning
entity: phase
plan: pr2-cleanup
phase: 4
status: pending
created: 2026-02-27
updated: 2026-02-27
---

# Phase 4: Documentation Update

## Objective

Update README.md and docs/ to accurately reflect the complete feature set of the project after all code changes from Phases 1-3 are complete.

## Scope

### Includes

- **README.md** full update:
  - MCP tool parameter tables: add `cookies`, `headers`, `storage_state`, `auth_profile`, `delay`, `wait_until` to `crawl` and `crawl_site`
  - Add `list_auth_profiles` MCP tool documentation
  - Add authenticated crawling section (concepts, env vars, examples)
  - Add auth capture CLI documentation (`crawl capture-auth`)
  - Add SPA/JS rendering section (delay, wait-until)
  - Update Python API examples with `auth=` parameter and new `search()`/`search_async()`
  - Update CLI section with all new arguments (auth, SPA, --pageno)
  - Add auth-related env vars: `CRAWL_AUTH_STORAGE_STATE`, `CRAWL_AUTH_COOKIES_FILE`, `CRAWL_AUTH_PROFILE`
  - Update feature list in project description
- **docs/** update:
  - Update all module docs to reflect Phase 3 changes (search module, __init__.py exports)
  - Update feature docs for search parity
  - Verify cross-references remain valid
- **CHANGELOG.md**:
  - Ensure all changes are reflected

### Excludes

- Generating new docs from scratch (use update-docs skill)
- Translating documentation

## Prerequisites

- [ ] Phase 3 completed (all code changes finalized)
- [ ] Phase 3 API/CLI signatures are finalized and stable
- [ ] All tests passing

## Deliverables

- [ ] README.md updated with complete feature documentation
- [ ] docs/ updated via update-docs skill
- [ ] CHANGELOG.md reflects all changes
- [ ] No stale or inaccurate documentation remains

## Acceptance Criteria

- [ ] Every MCP tool parameter is documented in README
- [ ] Every CLI argument is documented in README
- [ ] Python API examples show auth and search usage
- [ ] Auth env vars documented in configuration section
- [ ] `capture-auth` subcommand documented with examples
- [ ] docs/ cross-references all valid
- [ ] `docs/modules/tests.md` stale claims (test count/coverage/E2E responsibility) are corrected
- [ ] Manual review: README examples match actual CLI/API behavior

## Dependencies on Other Phases

| Phase | Dependency Type | Description                                 |
| ----- | --------------- | ------------------------------------------- |
| 1     | Must complete   | Review file removed before final docs       |
| 2     | Must complete   | E2E test patterns documented                |
| 3     | Must complete   | Search parity code finalized before docs    |

## Notes

- Use the `update-docs` skill for docs/ updates.
- README should be the primary user-facing document — keep it comprehensive but readable.
- Consider adding a "Quick Start" section for authenticated crawling.
- Do not document speculative interfaces; document only finalized Phase 3 API/CLI signatures.
