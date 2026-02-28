---
type: planning
entity: implementation-plan
plan: "auth-crawling-reimplementation"
phase: 2
status: draft
created: "2026-02-28"
updated: "2026-02-28"
---

# Implementation Plan: Phase 2 - Surface Integration (CLI + MCP + Docs)

> Implements [Phase 2](../phases/phase-2.md) of [auth-crawling-reimplementation](../plan.md)

## Approach

Expose Phase-1 auth core semantics on CLI and MCP in a thin pass-through way, keeping one canonical resolver path in package code and updating docs accordingly. This phase must not expand auth feature scope (no session capture, no profile system) and must preserve crawler extraction defaults unchanged.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| [crawler-cli](../../../docs/modules/crawler-cli.md) | modify | Add MVP auth flag(s) and pass-through to package crawl APIs with consistent error handling. |
| [crawler-mcp-server](../../../docs/modules/crawler-mcp-server.md) | modify | Add MVP auth tool parameter(s) for `crawl` and `crawl_site`, forwarding to package APIs. |
| [crawler-package-api](../../../docs/modules/crawler-package-api.md) | modify | Confirm and enforce resolver-based single-source auth semantics for all surfaces. |
| docs module pages + README | modify | Document usage, constraints, and parity guarantees for API/CLI/MCP auth semantics. |
| [crawler-config](../../../docs/modules/crawler-config.md) | no-change (guardrail) | Keep extraction selectors/waits/SPA/session defaults untouched. |

## Required Context

| File | Why |
|------|-----|
| `plans/auth-crawling-reimplementation/plan.md` | Initiative-wide constraints and no-drift guardrails. |
| `plans/auth-crawling-reimplementation/phases/phase-2.md` | Gated scope for CLI/MCP/docs integration work. |
| `plans/auth-crawling-reimplementation/implementation/phase-1-impl.md` | Upstream auth-core contract Phase 2 must reuse, not fork. |
| `plans/auth-crawling-reimplementation/todo.md` | Active-phase sequencing and expected deliverables. |
| `docs/modules/crawler-cli.md` | Existing CLI argument inventory and docs baseline. |
| `docs/modules/crawler-mcp-server.md` | Existing MCP tool contracts and docs baseline. |
| `docs/modules/crawler-package-api.md` | API threading baseline and symbol map. |
| `docs/modules/crawler-config.md` | Explicit no-drift config reference to preserve. |
| `crawler/cli.py` | CLI parser and crawl dispatch code paths. |
| `crawler/mcp_server.py` | MCP tool signatures and crawl dispatch paths. |
| `crawler/__init__.py` | Package API signatures used by both CLI and MCP. |

## Implementation Steps

### Step 1: Add CLI auth input in MVP scope

- **What**: Add one minimal auth option for crawl command (storage-state path) and thread it into crawl API calls without adding unrelated UX features.
- **Where**: `crawler/cli.py` in `_parse_crawl_args` and `_run_crawl_async`.
- **Why**: Phase objective requires user control of auth in CLI with parity to API semantics.
- **Considerations**: Keep defaults backward-compatible; no implicit auth from unrelated env vars.

### Step 2: Add MCP auth input in MVP scope

- **What**: Extend MCP `crawl` and `crawl_site` tools with the same storage-state parameter semantics and pass-through to package APIs.
- **Where**: `crawler/mcp_server.py` tool function signatures and internal calls.
- **Why**: Phase requires reproducible auth control in MCP with consistent semantics.
- **Considerations**: Keep response envelope stable (`markdown`/`json`); surface deterministic error messages from core resolver.

### Step 3: Enforce one resolver path for all surfaces

- **What**: Ensure CLI and MCP do not implement independent auth validation logic beyond basic argument parsing; centralize validation and precedence in package/core resolver.
- **Where**: Cross-check `crawler/cli.py`, `crawler/mcp_server.py`, and `crawler/__init__.py` integration.
- **Why**: Prevent semantic drift and inconsistent failure behavior between surfaces.
- **Considerations**: Reject duplicate/forked validation code in CLI/MCP beyond type/shape parsing.

### Step 4: Add integration tests for parity and error propagation

- **What**: Add tests proving CLI/MCP/API equivalence on auth pass-through and equivalent handling of missing/invalid storage-state inputs.
- **Where**: `tests/test_cli.py`, `tests/test_mcp_server.py`, and auth-core/package tests as needed.
- **Why**: Acceptance requires semantic parity and reproducibility.
- **Considerations**: Mock crawl internals; keep tests deterministic and offline.

### Step 5: Update user-facing docs for Phase-2 contract

- **What**: Update README and module docs with MVP auth usage examples, explicit boundaries (session capture not yet included), and no-drift statement.
- **Where**: `README.md` and docs module files referenced above.
- **Why**: Phase deliverables explicitly include docs updates.
- **Considerations**: Avoid documenting any Phase-3 capture flow in this phase.

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Integration/contract | CLI and MCP auth parameter pass-through to package resolver, parity with API semantics, and deterministic invalid/missing state errors. **Verify command:** `pytest -q tests/test_cli.py tests/test_mcp_server.py tests/test_init.py tests/test_auth_core.py` | Tests pass with equivalent auth behavior across API/CLI/MCP and no regression for non-auth crawl usage. |

## Rollback Strategy

If regressions appear, remove CLI/MCP auth parameter exposure while retaining Phase-1 core internals behind package API. This keeps non-auth users stable and allows reintroducing surface parameters once parity gaps are resolved.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| CLI auth flag naming | `--storage-state` vs `--auth-storage-state` | `--storage-state` | Minimal and aligned with Phase-1 MVP terminology. |
| MCP parameter naming | `storage_state` only vs nested `auth` object | `storage_state` | Keeps MCP schema simple for MVP while mapping to shared resolver internally. |
| Error channel for invalid state | mixed per-surface text vs shared core messages | Shared core messages | Required for semantic parity and lower maintenance risk. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/cli.py:226` | `_parse_crawl_args(...)` | Crawl CLI options defined here; current surface has no storage-state auth input. |
| `crawler/cli.py:321` | `_run_crawl_async(...)` | Central crawl dispatch point where auth args must be forwarded for single/multi/site modes. |
| `crawler/mcp_server.py:188` | `crawl(...)` MCP tool | Current tool contract has crawl controls but no storage-state auth parameter. |
| `crawler/mcp_server.py:262` | `crawl_site(...)` MCP tool | Site tool needs matching auth parameter semantics for parity. |
| `crawler/__init__.py:87` | `crawl_page_async(...)` | Package API entrypoint for single crawl where CLI/MCP both converge. |
| `crawler/__init__.py:223` | `crawl_site_async(...)` | Site API wrapper to keep auth semantics aligned with single/multi crawl flows. |
| `crawler/config.py:157` | `build_markdown_run_config(...)` | Confirms extraction defaults location that must remain untouched in this phase. |

### Mismatches / Notes

- Current repo already has dedup-related surface wiring, but **no auth-crawling surface parameters** in CLI/MCP/package API yet.
- Existing auth handling in CLI/MCP is only for SearXNG search basic-auth and must not be conflated with crawl-session auth.
- Scope guard reaffirmed: session capture and broader profile ergonomics are deferred to Phase 3+ and excluded here.
