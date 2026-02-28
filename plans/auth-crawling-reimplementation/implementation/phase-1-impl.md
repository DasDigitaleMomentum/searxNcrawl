---
type: planning
entity: implementation-plan
plan: "auth-crawling-reimplementation"
phase: 1
status: draft
created: "2026-02-28"
updated: "2026-02-28"
---

# Implementation Plan: Phase 1 - Auth Core (Storage-State MVP)

> Implements [Phase 1](../phases/phase-1.md) of [auth-crawling-reimplementation](../plan.md)

## Approach

Introduce a minimal auth core centered on `storage_state` with strict validation and deterministic error semantics, then thread it only through package API crawl entrypoints. Keep this phase internal (no CLI/MCP UX expansion) and preserve all existing extraction defaults in `crawler/config.py`.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| [crawler-package-api](../../../docs/modules/crawler-package-api.md) | modify | Add optional auth parameter threading in package crawl APIs (`crawl_page*`, `crawl_pages*`, `crawl_site*`). |
| crawler-auth-core (new internal module) | create | Add `storage_state` config model + resolver + validation/error normalization helpers. |
| [crawler-site-crawl](../../../docs/modules/crawler-site-crawl.md) | modify | Reuse the same auth-core contract in site crawl runtime path. |
| [crawler-config](../../../docs/modules/crawler-config.md) | no-change (guardrail) | Preserve selectors, waits, JS snippet, SPA/full-page settings, and run-config defaults exactly. |

## Required Context

| File | Why |
|------|-----|
| `plans/auth-crawling-reimplementation/plan.md` | Defines No-Drift guardrails and out-of-scope boundaries. |
| `plans/auth-crawling-reimplementation/phases/phase-1.md` | Gated Phase-1 scope and acceptance criteria. |
| `plans/auth-crawling-reimplementation/todo.md` | Current phase tracking + sequencing context. |
| `docs/modules/crawler-package-api.md` | Baseline API threading map for crawl entrypoints. |
| `docs/modules/crawler-site-crawl.md` | Site crawl runtime anchor that must align with API auth threading. |
| `docs/modules/crawler-config.md` | Guardrail baseline for extraction defaults that must remain unchanged. |
| `crawler/__init__.py` | Package crawl function signatures and call chain entrypoint. |
| `crawler/site.py` | Site crawler runtime construction path (`BrowserConfig`, `AsyncWebCrawler`). |
| `crawler/config.py` | Must remain untouched in this phase per no-drift constraint. |

## Implementation Steps

### Step 1: Add a minimal auth core for `storage_state`

- **What**: Create a dedicated internal module (e.g., `crawler/auth.py`) with a small dataclass/model for auth input and a resolver that canonicalizes path input, checks existence/type, and produces a validated runtime value.
- **Where**: New module under `crawler/`, consumed by package API and site runtime code.
- **Why**: Keeps auth semantics centralized so all call surfaces share one contract.
- **Considerations**: MVP supports only `storage_state`; defer profile/header/cookie matrix to later phases.

### Step 2: Define deterministic auth error contract

- **What**: Implement explicit exceptions (or structured `ValueError` messages) for missing file, unreadable file, malformed JSON, and unsupported auth combinations.
- **Where**: Same auth core module and package API integration points.
- **Why**: Phase acceptance requires reproducible and clear failure paths.
- **Considerations**: Do not convert failures into silent fallbacks; non-auth calls remain unchanged.

### Step 3: Thread auth through package crawl APIs only

- **What**: Add optional auth parameter(s) to `crawl_page_async`, `crawl_pages_async`, and `crawl_site_async` plus sync wrappers, then apply resolver output when constructing crawler runtime context.
- **Where**: `crawler/__init__.py` and `crawler/site.py`.
- **Why**: This is the minimal Phase-1 threading scope that blocks Phase 2.
- **Considerations**: No CLI flags and no MCP tool-parameter changes in Phase 1.

### Step 4: Add focused unit tests for resolver + error semantics

- **What**: Add tests for happy path (`storage_state` accepted), missing file, invalid JSON, and no-auth backward compatibility.
- **Where**: `tests/` (new phase-focused test module, e.g., `tests/test_auth_core.py`).
- **Why**: Validates phase deliverables while keeping test surface narrow.
- **Considerations**: Use temp files/mocks; avoid live crawling network dependency.

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Unit/contract | Auth resolver + API threading for storage-state MVP, including missing/invalid state errors and non-auth backward compatibility. **Verify command:** `pytest -q tests/test_auth_core.py` | Tests pass with deterministic error messages and unchanged behavior for calls without auth input. |

## Rollback Strategy

If regressions occur, remove auth parameter threading and resolver usage from package/site crawl entrypoints while retaining the prior no-auth behavior. Because `crawler/config.py` remains untouched in this phase, rollback is limited to auth-core and API/runtime wiring changes.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Auth parameter shape in API | single `storage_state` arg vs nested auth object | Nested auth object with MVP field `storage_state` | Extensible without expanding Phase-1 scope beyond storage-state. |
| Error transport | broad generic error vs explicit auth-specific messages | Explicit auth-specific messages | Needed for reproducible negative tests and cross-surface consistency later. |
| Resolver strictness | permissive fallback vs strict validation | Strict validation | Prevents hidden auth misconfiguration and unstable runtime behavior. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/__init__.py:87` | `crawl_page_async(...)` | Main async single-page entrypoint currently has no auth parameters. |
| `crawler/__init__.py:161` | `crawl_pages_async(...)` | Batch path needs same auth threading contract as single-page path. |
| `crawler/__init__.py:223` | `crawl_site_async(...)` | Site wrapper boundary where auth input should stay semantically consistent. |
| `crawler/site.py:121` | `BrowserConfig(use_persistent_context=False)` | Concrete runtime browser configuration point for applying resolved auth state without touching extraction defaults. |
| `crawler/site.py:123` | `AsyncWebCrawler(config=browser_cfg)` | Confirms site path has explicit browser config injection location. |
| `crawler/config.py:157` | `build_markdown_run_config(...)` | Defines stabilized wait/SPA/full-page defaults that must not drift in this plan. |
| `crawler/config.py:185` | `build_discovery_run_config(...)` | Secondary config factory also guarded from changes in this initiative. |

### Mismatches / Notes

- Current codebase has **no auth-crawling runtime contract** yet (`storage_state` is not present in crawler API symbols).
- Existing auth mentions in code are SearXNG basic-auth for search (`crawler/cli.py:527`, `crawler/mcp_server.py:344`) and are unrelated to crawling-session auth.
- Guardrail reaffirmed: do **not** modify selector defaults, `wait_for`, `js_code`, `scan_full_page`, or persistent-session defaults in `crawler/config.py` during this phase.
