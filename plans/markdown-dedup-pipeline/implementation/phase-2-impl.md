---
type: planning
entity: implementation-plan
plan: "markdown-dedup-pipeline"
phase: 2
status: draft
created: "2026-02-28"
updated: "2026-02-28"
---

# Implementation Plan: Phase 2 - Surface Area, Guards, Docs

> Implements [Phase 2](../phases/phase-2.md) of [markdown-dedup-pipeline](../plan.md)

## Approach

Expose the dedup mode as a controlled user-facing option in CLI and MCP (`off|exact`), propagate it through the package crawl entrypoints into the document builder pipeline, and add conservative rollout guardrails using Phase-1 dedup metrics. This phase is intentionally API-surface and safety focused: it must not alter Crawl4AI extraction configuration, selectors, or markdown-generator behavior.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| [crawler-cli](../../../docs/modules/crawler-cli.md) | modify | Add crawl CLI option for dedup mode (`off|exact`) and pass-through into crawl API calls; ensure help text and JSON output behavior remain stable. |
| [crawler-mcp-server](../../../docs/modules/crawler-mcp-server.md) | modify | Add MCP crawl/crawl_site parameter for dedup mode (`off|exact`) and propagate to package crawl APIs. |
| [crawler-document-pipeline](../../../docs/modules/crawler-document-pipeline.md) | modify | Add/complete guardrail signaling (warning metadata) based on dedup removal-rate metrics produced by Phase 1. |
| [crawler-config](../../../docs/modules/crawler-config.md) | no-change (guardrail) | Preserve `MAIN_SELECTORS`, `EXCLUDED_SELECTORS`, and run-config construction exactly as-is; no selector/extraction drift in this phase. |

## Required Context

| File | Why |
|------|-----|
| `plans/markdown-dedup-pipeline/plan.md` | Global requirements and non-functional constraints, including central pipeline behavior and `off|exact` target mode. |
| `plans/markdown-dedup-pipeline/phases/phase-1.md` | Defines prerequisite core + metrics this phase depends on. |
| `plans/markdown-dedup-pipeline/phases/phase-2.md` | Gated scope/acceptance for surface exposure, guardrails, and docs. |
| `plans/markdown-dedup-pipeline/todo.md` | Tracks active sequencing and phase handoff state. |
| `plans/markdown-dedup-pipeline/implementation/phase-1-impl.md` | Carries forward dedup-core assumptions and metadata contract from prior phase. |
| `crawler/__init__.py` | Public crawl entrypoints where dedup mode must be threaded without breaking existing callers. |
| `crawler/cli.py` | CLI argument surface and call sites for `crawl_page_async`, `crawl_pages_async`, and `crawl_site_async`. |
| `crawler/mcp_server.py` | MCP tool parameter contracts for `crawl` and `crawl_site`, plus formatting path. |
| `crawler/builder.py` | Document assembly/metadata location where guardrail metadata is attached. |
| `crawler/config.py` | Must remain unchanged for selectors/extraction defaults in this phase. |
| `docs/modules/crawler-cli.md` | Documentation baseline to update for new CLI dedup option/default behavior. |
| `docs/modules/crawler-mcp-server.md` | Documentation baseline to update for MCP dedup parameters and output expectations. |
| `docs/modules/crawler-document-pipeline.md` | Documentation baseline for pipeline/metadata updates and guardrail semantics. |
| `docs/modules/crawler-config.md` | Documentation baseline to explicitly note no config/selector changes in Phase 2 rollout. |

## Implementation Steps

### Step 1: Extend crawl API surface with explicit dedup mode pass-through

- **What**: Add an explicit dedup mode parameter (`off|exact`, default aligned to Phase-1 default) to package crawl entrypoints and wrappers, then thread it to the document-building path.
- **Where**: `crawler/__init__.py` (`crawl_page_async`, `crawl_page`, `crawl_pages_async`, `crawl_pages`, and the site crawl path through `crawl_site_async`).
- **Why**: CLI and MCP should share one canonical configuration path; package API propagation keeps behavior consistent and testable.
- **Considerations**: Preserve backward compatibility by keeping default behavior unchanged for callers that do not pass dedup mode.

### Step 2: Add CLI and MCP dedup mode options (`off|exact`) and wire them end-to-end

- **What**: Introduce a CLI flag for dedup mode and MCP tool parameters for dedup mode, validate allowed values, and pass through to crawl API calls.
- **Where**: `crawler/cli.py` (`_parse_crawl_args`, `_run_crawl_async`) and `crawler/mcp_server.py` (`crawl`, `crawl_site` tool signatures and internal dispatch).
- **Why**: Phase 2 acceptance requires users to explicitly disable (`off`) or enable (`exact`) dedup.
- **Considerations**: Keep output format behavior and existing options unchanged; invalid mode handling should be deterministic and clearly surfaced.

### Step 3: Add rollout guardrails based on dedup removal-rate metrics

- **What**: Add conservative guardrail logic that marks suspiciously high removal rates in metadata and/or logs warnings while preserving successful crawl output.
- **Where**: `crawler/builder.py` metadata enrichment path after dedup metrics are available (from Phase 1).
- **Why**: Phase 2 calls for safe rollout; warning signals reduce silent false-positive risk without introducing aggressive behavior changes.
- **Considerations**: Guardrail must be non-destructive (warn/annotate only), deterministic, and mode-aware (`off` should not emit removal-based warnings).

### Step 4: Add integration tests for parameter flow and metadata visibility

- **What**: Add tests that verify `off|exact` flow from CLI and MCP to output metadata, and that guardrail annotations appear only under expected metric conditions.
- **Where**: Integration-oriented test modules under `tests/` covering CLI argument parsing/execution path, MCP tool handlers, and builder metadata output contracts.
- **Why**: Phase 2 acceptance explicitly requires proof that flags/parameters reach output behavior and metadata.
- **Considerations**: Use mocks/fixtures to avoid network dependence; assert defaults explicitly to lock backward-compatible behavior.

### Step 5: Update module documentation for user-facing behavior and limits

- **What**: Update docs to describe dedup mode surface, defaults, guardrail semantics, and constraints/limits.
- **Where**: `docs/modules/crawler-cli.md`, `docs/modules/crawler-mcp-server.md`, `docs/modules/crawler-document-pipeline.md`, and `docs/modules/crawler-config.md` (explicitly documenting unchanged extraction/selectors in this phase).
- **Why**: Phase 2 deliverables include final documentation updates for behavior, boundaries, and defaults.
- **Considerations**: Keep docs aligned with implementation truth; do not imply fuzzy/cross-document dedup support.

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Integration/contract | CLI + MCP dedup mode pass-through (`off|exact`), builder guardrail metadata signaling, and stable default behavior. **Verify command:** `pytest -q tests/test_cli.py tests/test_mcp_server.py tests/test_builder.py tests/test_init.py` | Parameters are accepted/validated, propagated to output behavior and metadata, guardrails emit warnings/annotations only when thresholds are exceeded, and legacy invocation without dedup argument remains stable. |

## Rollback Strategy

If regressions appear, revert Phase-2 surface wiring and guardrail metadata additions while retaining the Phase-1 core dedup path. Specifically: remove new CLI/MCP parameters and API threading, disable guardrail warning annotation, and return to prior externally observable interfaces. No rollback in `crawler/config.py` is required because extraction configuration and selectors are intentionally untouched in this phase.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Default dedup mode exposure | `off` default, `exact` default matching Phase 1 | Keep default aligned with Phase-1 established default behavior | Preserves backward compatibility and avoids behavioral drift between internal and exposed configuration. |
| Guardrail emission channel | Metadata-only, logs-only, metadata+logs | Metadata+logs | Gives machine-readable signal in outputs and operator-visible runtime warning without hard-failing crawls. |
| Invalid mode handling | Silent fallback, explicit error, warning + fallback | Explicit validation with deterministic fallback policy documented in CLI/MCP help/tests | Prevents ambiguous behavior and improves reproducibility. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/cli.py:226` | `_parse_crawl_args` | Current crawl CLI arguments are defined here; dedup mode flag must be added here for user-facing surface. |
| `crawler/cli.py:314`-`crawler/cli.py:355` | `_run_crawl_async` dispatch to `crawl_page_async` / `crawl_pages_async` / `crawl_site_async` | Confirms current call path has no dedup-mode argument yet and identifies exact pass-through points. |
| `crawler/mcp_server.py:188`-`crawler/mcp_server.py:193` | `crawl` tool signature | Current MCP crawl contract lacks dedup mode; this is the surface extension point. |
| `crawler/mcp_server.py:255`-`crawler/mcp_server.py:262` | `crawl_site` tool signature | Site-crawl MCP contract similarly lacks dedup mode and needs aligned parameter exposure. |
| `crawler/__init__.py:85`-`crawler/__init__.py:89` | `crawl_page_async` signature | Public package API currently accepts only `url` and optional `config`; dedup mode threading starts here. |
| `crawler/__init__.py:127`-`crawler/__init__.py:132` | `crawl_pages_async` signature | Batch crawl path needs equivalent dedup mode support for parity with single-page and site flows. |
| `crawler/site.py:127` | `build_document_from_result(result)` call | Site crawl currently builds docs without dedup-mode input; this is the internal bridging point. |
| `crawler/builder.py:56`-`crawler/builder.py:60` | `cleaned_markdown` assignment + `metadata.update(...)` | Correct location for mode-aware guardrail metadata enrichment during document assembly. |
| `crawler/config.py:17`-`crawler/config.py:55` | `MAIN_SELECTORS` and `EXCLUDED_SELECTORS` | Extraction selector baseline that must remain exactly unchanged in Phase 2. |
| `crawler/config.py:157`-`crawler/config.py:208` | `build_markdown_run_config` and `build_discovery_run_config` | Confirms extraction/generator defaults are centralized and should not be altered in this phase. |

### Mismatches / Notes

- Phase 2 is blocked by Phase-1 completion in current repo state: `crawler/builder.py` does not yet expose dedup-mode control or dedup metrics fields required for guardrail thresholds.
- Current repository snapshot contains no checked-in `tests/test_cli.py`, `tests/test_mcp_server.py`, `tests/test_builder.py`, or `tests/test_init.py` source files (only `tests/__pycache__/`); integration tests listed in this phase must be created/restored during implementation.
- Hard constraint reaffirmed: **no changes to extraction configuration/selectors** in `crawler/config.py` (including `MAIN_SELECTORS`, `EXCLUDED_SELECTORS`, `target_elements`, `excluded_selector`, and markdown generator options) in Phase 2.
