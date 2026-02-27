---
type: planning
entity: implementation-plan
plan: pr2-cleanup
phase: 1
status: draft
created: 2026-02-27
updated: 2026-02-27
---

# Implementation Plan: Phase 1 — Review Cleanup

> Implements [Phase 1](../phases/phase-1.md) of [pr2-cleanup](../plan.md)

## Approach

Delete the stale review file `reviews/pr2-review.md` and remove the now-empty `reviews/` directory from the repository. Before committing, verify that no source files (Python, shell, config, README) reference the review file — only the plan artifacts themselves mention it (which is expected and correct). Confirm the existing test suite still passes after the deletion.

This is a pure file-deletion change with no code modifications. The only references to `pr2-review` in the repo are inside `plans/pr2-cleanup/` (the plan, phase, and todo files that *describe* this cleanup task) — these are intentional and should **not** be modified as part of this phase.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| reviews (standalone) | delete | Remove `reviews/pr2-review.md` and the `reviews/` directory entirely |

## Required Context

| File | Why |
|------|-----|
| `reviews/pr2-review.md` | The file to be deleted — confirm it exists (verified: yes, 11460 bytes) |
| `plans/pr2-cleanup/phases/phase-1.md` | Acceptance criteria that must be satisfied |

## Implementation Steps

### Step 1: Delete the review file

- **What**: Remove `reviews/pr2-review.md` from the working tree and stage the deletion
- **Where**: `reviews/pr2-review.md`
- **Why**: The review is stale — all parity gaps it cited have been fixed. Its presence causes confusion.
- **Considerations**: The file is the only entry in `reviews/`. Git will automatically drop the directory when the last file is removed.

### Step 2: Verify no dangling references outside plan artifacts

- **What**: Run `grep -r "pr2-review" . --include='*.py' --include='*.sh' --include='*.md' --include='*.yml' --include='*.yaml' --include='*.toml' --include='*.json' --include='*.cfg' --exclude-dir=.git --exclude-dir=plans` to confirm zero hits outside `plans/` (intentional plan references are excluded by design)
- **Where**: Repository root
- **Why**: Acceptance criterion requires `grep -r "pr2-review" .` returns no results (excluding `.git`). References inside `plans/pr2-cleanup/` are expected (they describe this task) and do not constitute dangling references to a consumed artifact.
- **Considerations**: The README does not mention the review file (verified). No Python, shell, YAML, TOML, or JSON files reference it (verified).

### Step 3: Commit the deletion

- **What**: Create a single commit removing the review file: `git rm reviews/pr2-review.md && git commit -m "chore: remove stale PR #2 review file"`
- **Where**: Git index
- **Why**: Clean atomic commit for the deletion, easily revertable
- **Considerations**: Must be on `main` branch (PR #2 merged) with a clean working tree.

### Step 4: Run the test suite

- **What**: Execute `pytest tests/` and confirm all tests pass
- **Where**: Existing test suite (baseline)
- **Why**: Acceptance criterion: "All existing tests still pass". Since no code was changed, this is a sanity check.
- **Considerations**: The review file is not imported or referenced by any test. Expect 100% pass rate.

## Verify Command

```bash
# Single compound verification (all three acceptance criteria)
! test -d reviews/ && ! grep -r "pr2-review" . --exclude-dir=.git --exclude-dir=plans --include='*.py' --include='*.sh' --include='*.md' --include='*.yml' --include='*.yaml' --include='*.toml' --include='*.json' --include='*.cfg' && pytest tests/ -q
```

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Filesystem | `ls reviews/` | Error — directory does not exist |
| Reference scan | `grep -r "pr2-review" . --exclude-dir=.git --exclude-dir=plans` | Zero matches outside `plans/` |
| Existing tests | `pytest tests/` | Baseline suite passes (no regressions) |

## Rollback Strategy

Restore the deleted file from git history:

```bash
git revert HEAD   # if already committed
# or
git checkout HEAD~1 -- reviews/pr2-review.md   # restore just the file
```

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Treat plan-internal refs as "dangling" | (a) Also edit plan.md/phase-1.md/todo.md to remove mentions, (b) Leave them as-is | (b) Leave as-is | Plan artifacts describe the task intent; they should reference what they're cleaning up. Editing them is out of scope for this phase. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `reviews/pr2-review.md` | Entire file (11460 bytes) | Confirmed: exists, is the sole file in `reviews/` |
| `reviews/` | Directory listing | Confirmed: contains only `pr2-review.md` — safe to delete entire directory |
| `README.md` | Full text | Confirmed: no mention of `pr2-review` or `reviews/` |
| `*.py`, `*.sh`, `*.yml`, `*.toml`, `*.json` | Codebase-wide search | Confirmed: zero references to `pr2-review` or `reviews/` in any source/config file |
| `plans/pr2-cleanup/{plan,phases/phase-1,todo}.md` | Plan artifacts | Confirmed: 11 references exist — all are intentional (they describe this cleanup task) |

### Mismatches / Notes

- **Branch resolved**: PR #2 has been merged into `main`. All work proceeds on `main`. The phase-1 prerequisite "On `feature/authenticated-crawling` branch" is superseded — `main` now contains all PR #2 code.
- **Acceptance criterion resolved**: Treat dangling-reference checks as repo-wide **excluding** `plans/` and `.git`. Remaining `pr2-review` references inside `plans/pr2-cleanup/` are intentional planning context and do not block phase completion.
