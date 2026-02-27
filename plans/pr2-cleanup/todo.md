---
type: planning
entity: todo
plan: pr2-cleanup
updated: 2026-02-27
---

# Todo: PR #2 Cleanup & Feature Completion

## Active Phase

### Phase 1: Review Cleanup

- **Scope**: [Phase 1](phases/phase-1.md)
- **Implementation**: [TBD](implementation/)
- **Handover**: [TBD](handovers/)

### Pending

- [ ] Delete `reviews/pr2-review.md`
- [ ] Remove `reviews/` directory if empty
- [ ] Check for dangling references to review file
- [ ] Verify all tests still pass

### In Progress

_(none)_

### Completed

_(none)_

### Blocked

_(none)_

---

## Upcoming Phases

### Phase 2: E2E Test Coverage
- [ ] Create `tests/test_e2e.py` with `@pytest.mark.e2e`
- [ ] Register `e2e` marker in `pyproject.toml`
- [ ] E2E: Auth crawling with cookies
- [ ] E2E: Auth crawling with storage-state
- [ ] E2E: SPA crawling with delay/wait-until
- [ ] E2E: CLI direct invocation (crawl + search)
- [ ] E2E: CLI capture-auth smoke test
- [ ] Verify all tests pass (unit + E2E)

### Phase 3: Search Parity
- [ ] Extract search logic into shared module
- [ ] Implement `search_async()` in Python API
- [ ] Implement `search()` sync wrapper
- [ ] Create `SearchResult` type
- [ ] Add `--pageno` to CLI search
- [ ] Wire MCP + CLI to shared search implementation
- [ ] Unit tests for search API
- [ ] E2E test for search API

### Phase 4: Documentation Update
- [ ] Update README: MCP tool parameter tables
- [ ] Update README: add auth section
- [ ] Update README: add capture-auth docs
- [ ] Update README: add SPA section
- [ ] Update README: Python API examples (auth + search)
- [ ] Update README: CLI arguments (all new flags)
- [ ] Update README: auth env vars
- [ ] Update docs/ via update-docs skill
- [ ] Update CHANGELOG.md

---

## Changelog

- **2026-02-27**: Todo created with 4 phases, Phase 1 active.
