---
type: planning
entity: implementation-plan
plan: "auth-crawling-reimplementation"
phase: 3
status: draft
created: "2026-02-28"
updated: "2026-02-28"
---

# Implementation Plan: Phase 3 - Session Capture (Isolated)

> Implements [Phase 3](../phases/phase-3.md) of [auth-crawling-reimplementation](../plan.md)

## Approach

Add an isolated session-capture flow that produces a valid `storage_state` file through manual login, with explicit completion and timeout states. Keep capture runtime separate from normal crawl execution paths and avoid any modification to crawl extraction defaults or persistent-session behavior in `crawler/config.py`.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| crawler-session-capture (new module/command path) | create | Add isolated capture workflow, completion criteria handling, timeout handling, and file persistence. |
| [crawler-cli](../../../docs/modules/crawler-cli.md) | modify | Add dedicated capture command/flow (not mixed into normal crawl invocation). |
| [crawler-mcp-server](../../../docs/modules/crawler-mcp-server.md) | modify | Optionally expose capture as separate tool/action with explicit status outcomes. |
| [crawler-package-api](../../../docs/modules/crawler-package-api.md) | modify | Add optional helper entrypoint(s) for capture orchestration if needed by CLI/MCP. |
| docs/README | modify | Document safe usage, boundaries, and error/timeout semantics for capture. |
| [crawler-config](../../../docs/modules/crawler-config.md) | no-change (guardrail) | No edits to extraction defaults/selectors/wait/SPA/session defaults. |

## Required Context

| File | Why |
|------|-----|
| `plans/auth-crawling-reimplementation/plan.md` | Defines guardrails and out-of-scope changes to avoid during capture rollout. |
| `plans/auth-crawling-reimplementation/phases/phase-3.md` | Gated scope and acceptance criteria for isolated session capture. |
| `plans/auth-crawling-reimplementation/implementation/phase-1-impl.md` | Storage-state contract and auth-core semantics capture output must satisfy. |
| `plans/auth-crawling-reimplementation/implementation/phase-2-impl.md` | Surface semantics and docs parity constraints to align with capture docs/usage. |
| `plans/auth-crawling-reimplementation/todo.md` | Sequencing and deliverables tracking. |
| `docs/modules/crawler-cli.md` | Existing command surface that capture command should extend without scope bleed. |
| `docs/modules/crawler-mcp-server.md` | MCP tool contract baseline for adding isolated capture action if included. |
| `docs/modules/crawler-config.md` | No-drift baseline for extraction defaults and config guardrails. |
| `crawler/cli.py` | Current CLI command split (`crawl`, `search`) and where capture command can be added cleanly. |
| `crawler/mcp_server.py` | Current MCP tools (`crawl`, `crawl_site`, `search`) and extension point for isolated capture tool. |
| `crawler/__init__.py` | Package public exports where capture helpers may be surfaced. |
| `crawler/site.py` | Existing runtime use of browser config, useful anchor to avoid coupling capture with site crawl path. |

## Implementation Steps

### Step 1: Implement isolated capture runtime with explicit states

- **What**: Create capture runtime that launches browser/session for manual login and emits one of: `success` (state saved), `timeout`, `abort` (user/browser closed), or explicit `error`.
- **Where**: New module under `crawler/` (e.g., `crawler/session_capture.py`).
- **Why**: Phase objective requires robust and deterministic capture-state transitions.
- **Considerations**: Keep capture state machine separate from crawl run-config builders and normal crawl APIs.

### Step 2: Persist validated `storage_state` output safely

- **What**: Save captured state to a user-specified path with path checks, parent-directory handling, and overwrite policy.
- **Where**: Capture runtime module and thin wrappers.
- **Why**: Acceptance requires reproducible generation of valid storage-state files.
- **Considerations**: Avoid hidden defaults that could overwrite unrelated files.

### Step 3: Add completion criteria and timeout controls

- **What**: Support explicit capture completion rules (e.g., URL match and/or user confirmation), timeout duration, and deterministic timeout error text.
- **Where**: Capture runtime orchestration + surface-level argument schema.
- **Why**: Phase includes redirect/timeout edge behavior as first-class deliverables.
- **Considerations**: Completion signals should be easy to test and document.

### Step 4: Expose capture as separate CLI/MCP surface

- **What**: Add dedicated CLI command/subcommand and, if applicable, separate MCP tool for capture (not an option bolted into regular crawl command).
- **Where**: `crawler/cli.py`, `crawler/mcp_server.py`, and optional package exports in `crawler/__init__.py`.
- **Why**: Isolation reduces risk of regression on core crawl paths.
- **Considerations**: Reuse Phase-1/2 auth-core contract for output compatibility.

### Step 5: Add targeted tests and docs for edge cases

- **What**: Add tests for success, timeout, and abort/close behavior, plus documentation for secure operation and common failure modes.
- **Where**: `tests/` capture test module(s), README, module docs.
- **Why**: Acceptance criteria explicitly require deterministic timeout/error behavior and guidance.
- **Considerations**: Use mocks/fakes for browser events to avoid flaky live-browser CI dependencies where possible.

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Integration/behavior | Isolated session-capture flow for success/timeout/abort states and valid storage-state persistence without affecting crawl defaults. **Verify command:** `pytest -q tests/test_session_capture.py` | Tests pass with deterministic state transitions, validated output files, and no regressions in normal crawl configuration paths. |

## Rollback Strategy

If capture rollout causes instability, disable/remove capture command/tool wiring while keeping Phase-1/2 auth consumption paths for pre-existing storage-state files intact. This preserves authenticated crawling via existing state files without requiring capture availability.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Capture completion rule | URL-match only, manual confirm only, or hybrid | Hybrid (URL-match and optional manual confirm) | Balances automation with operator control for diverse auth flows. |
| Output overwrite behavior | always overwrite, never overwrite, opt-in overwrite | Opt-in overwrite flag | Safer default for credential-bearing files. |
| MCP exposure timing | CLI-only first vs CLI+MCP in same phase | CLI+MCP in same phase if implementation remains isolated | Maintains surface parity while honoring isolation guardrail. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/cli.py:226` | `_parse_crawl_args(...)` | Current CLI parser only supports crawl/search options; no capture command flow yet. |
| `crawler/cli.py:410` | `_parse_search_args(...)` | Confirms current CLI architecture uses separate command parsers, supporting isolated capture addition. |
| `crawler/mcp_server.py:188` | `crawl(...)` tool | Existing crawl tool should remain untouched by capture-specific logic. |
| `crawler/mcp_server.py:361` | `search(...)` tool | Confirms current MCP tool boundaries and where capture would be introduced separately. |
| `crawler/__init__.py:49` | `__all__` export surface | Public API exports currently exclude any capture helper; new symbols must be intentionally added. |
| `crawler/site.py:121` | `BrowserConfig(use_persistent_context=False)` | Existing crawl runtime explicitly avoids persistent context; capture must not alter this default behavior for normal crawling. |
| `crawler/config.py:157` | `build_markdown_run_config(...)` | Capture phase must not modify extraction defaults (wait/selectors/js/full-page). |

### Mismatches / Notes

- No session-capture implementation exists yet in current repo (`crawler/` has no capture module/command/tool path).
- Existing runtime already has explicit anti-persistent behavior for site crawling (`use_persistent_context=False`), reinforcing the need to keep capture isolated.
- Phase scope guard: avoid broad profile/discoverability systems; keep deliverable to isolated state capture with deterministic completion/timeout handling.
