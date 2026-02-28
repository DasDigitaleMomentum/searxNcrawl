---
type: planning
entity: implementation-plan
plan: "markdown-dedup-pipeline"
phase: 1
status: draft
created: "2026-02-28"
updated: "2026-02-28"
---

# Implementation Plan: Phase 1 - Exact Intra-Doc Dedup Core

> Implements [Phase 1](../phases/phase-1.md) of [markdown-dedup-pipeline](../plan.md)

## Approach

Implement a conservative, deterministic post-processing dedup step in the document builder pipeline, directly after markdown selection and before `CrawledDocument` construction. The dedup algorithm will only remove **exact normalized duplicate sections** (first occurrence wins), and will publish per-document dedup metrics in metadata. This phase explicitly avoids any CLI/MCP surface changes and keeps existing Crawl4AI extraction configuration untouched.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| crawler-document-pipeline | modify | Add exact intra-document markdown dedup core, integrate in `build_document_from_result`, and emit dedup stats in metadata. |
| crawler-config | no-change (guardrail) | Preserve current selector/extraction behavior; no `target_elements`, `excluded_selector`, or markdown generator option changes in this phase. |

## Required Context

| File | Why |
|------|-----|
| `plans/markdown-dedup-pipeline/plan.md` | Defines global requirements (`off|exact` target state), non-functional constraints, and DoD boundaries. |
| `plans/markdown-dedup-pipeline/phases/phase-1.md` | Gated scope and acceptance for Exact Intra-Doc Dedup Core. |
| `plans/markdown-dedup-pipeline/phases/phase-2.md` | Confirms CLI/MCP parameter exposure is deferred and out-of-scope for this phase. |
| `plans/markdown-dedup-pipeline/todo.md` | Active tasks and sequencing for current phase. |
| `crawler/builder.py` | Current markdown selection flow and metadata population point where dedup hook must be added. |
| `crawler/document.py` | `CrawledDocument` metadata container that will carry dedup metrics. |
| `crawler/config.py` | Extraction/selectors config that must remain unchanged in Phase 1. |
| `docs/modules/crawler-document-pipeline.md` | Current documented symbol inventory and data flow for builder/references/doc model. |

## Implementation Steps

### Step 1: Add exact dedup core module for markdown sections

- **What**: Create a focused dedup core in `crawler/` (e.g., `crawler/markdown_dedup.py`) with functions for (a) section splitting, (b) normalization for fingerprint stability (line endings + whitespace normalization only), (c) exact fingerprint-based first-seen retention, and (d) idempotent markdown reconstruction preserving original section order of retained blocks.
- **Where**: New module under `crawler/` with an explicit API consumed by `crawler/builder.py`.
- **Why**: Keeps dedup behavior isolated/testable and avoids mixing algorithm details into `build_document_from_result`.
- **Considerations**: Keep false-positive risk low by deduplicating only exact normalized section matches; do not add fuzzy/near-duplicate logic in Phase 1.

### Step 2: Integrate dedup in builder pipeline after markdown selection

- **What**: In `build_document_from_result`, run dedup immediately after `primary_markdown`/`cleaned_markdown` are resolved, then assign deduped markdown to `CrawledDocument.markdown`.
- **Where**: `crawler/builder.py` in success path after markdown candidate selection and before `CrawledDocument(...)` return.
- **Why**: This is the shared pipeline path used by crawl APIs, therefore CLI and MCP outputs benefit automatically without additional surface changes.
- **Considerations**: Preserve fallback behavior from `_ensure_markdown`; keep `raw_markdown` semantics stable (raw remains source markdown while `markdown` becomes dedup-processed output).

### Step 3: Emit dedup metrics in metadata (Phase-1 internal exposure)

- **What**: Add metadata keys produced by dedup execution, e.g. `dedup_mode`, `dedup_sections_total`, `dedup_sections_removed`, `dedup_chars_removed`, `dedup_applied`.
- **Where**: `crawler/builder.py` metadata update sequence (alongside existing `raw_markdown_length` / `fit_markdown_length` enrichment from `_prepare_metadata`).
- **Why**: Phase 1 requires dedup metrics per document even before CLI/MCP controls are exposed.
- **Considerations**: Default mode for this phase is internal exact dedup on successful markdown flow; CLI/MCP toggles (`off|exact`) are deferred to Phase 2 and must not be introduced here.

### Step 4: Add unit tests for core behavior and idempotence

- **What**: Add tests covering exact duplicate removal, no-op on unique documents, stable deterministic output order, and idempotence (`dedup(dedup(x)) == dedup(x)`). Include a regression-oriented fixture approximating the Agno repeated-section pattern.
- **Where**: New tests under `tests/` (e.g., `tests/test_markdown_dedup.py`) targeting the new dedup module and builder integration entrypoint.
- **Why**: Acceptance criteria explicitly require idempotence and safe behavior when no duplicates exist.
- **Considerations**: Keep tests independent from live network calls; fixture-driven markdown strings are sufficient for Phase 1.

## Acceptance Alignment

| Phase 1 Acceptance Criterion | Implementation Alignment |
|---|---|
| Agno-Fall enthält keine doppelt wiederholten Kernsektionen mehr. | Step 1 + Step 4 add exact section fingerprint dedup and regression fixture coverage for repeated-core-section patterns. |
| `dedup(dedup(md)) == dedup(md)` für repräsentative Fixtures. | Step 1 defines deterministic first-seen retention; Step 4 adds explicit idempotence assertions. |
| Bei Dokumenten ohne Duplikate bleibt Inhalt unverändert (bis auf neutrale Normalisierung). | Step 1 normalization is intentionally minimal and scoped; Step 4 includes no-duplicate no-op expectations. |

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| Unit/Integration (local) | Dedup core + builder metadata integration + idempotence fixture suite. **Verify command:** `pytest -q tests/test_markdown_dedup.py` | Tests pass; duplicate sections removed exactly once; metadata contains dedup counters; idempotence assertions hold. |

## Rollback Strategy

If Phase 1 introduces regressions, remove the builder hook to the dedup core and keep current `cleaned_markdown = primary_markdown` behavior as before. Because no selector/config changes are introduced in this phase, rollback is constrained to document-pipeline code paths (`crawler/builder.py` + new dedup module + tests) and does not require crawl configuration restoration.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Dedup section boundary strategy | Paragraph split, heading-aware split, blank-line block split | Blank-line-delimited block sections (with conservative normalization) | Lowest implementation risk and straightforward idempotence for exact duplicates in Phase 1. |
| Where to store dedup metrics | New dataclass fields vs metadata keys | Metadata keys in `CrawledDocument.metadata` | Minimally invasive and compatible with existing CLI/MCP JSON serialization of metadata. |
| Phase-1 mode control exposure | Add CLI/MCP flag now vs defer | Defer external mode toggles to Phase 2 | Matches gated phase scope; avoids expanding user-facing API in core phase. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/builder.py:15` | `build_document_from_result` | Single canonical transformation path where markdown is selected and returned; correct hook point for Phase 1 dedup. |
| `crawler/builder.py:47`-`crawler/builder.py:57` | `primary_markdown` selection and `cleaned_markdown` assignment | Confirms dedup should run after variant selection (`fit`/citations/raw) and before output object creation. |
| `crawler/builder.py:59` | `metadata.update(_prepare_metadata(...))` | Existing metadata enrichment point where dedup stats can be added without schema breakage. |
| `crawler/document.py:19`-`crawler/document.py:31` | `CrawledDocument` dataclass (`metadata: Dict[str, Any]`) | Confirms per-document dedup metrics can be stored now without changing public type surface. |
| `crawler/__init__.py:115` | `crawl_page_async` returns `build_document_from_result(first_result)` | Verifies builder integration automatically affects package API callers. |
| `crawler/mcp_server.py:251` and `crawler/mcp_server.py:324` | MCP `crawl` / `crawl_site` format output from built docs | Confirms Phase 1 core changes propagate to MCP outputs without adding MCP parameters yet. |
| `crawler/cli.py:347` and `crawler/cli.py:352` | CLI crawl flow calls `crawl_page_async` / `crawl_pages_async` | Confirms CLI receives deduped markdown via existing path with no CLI argument changes in this phase. |
| `crawler/config.py:157`-`crawler/config.py:208` | `build_markdown_run_config` / `build_discovery_run_config` | Confirms extraction selectors and markdown-generator settings are defined here and can be explicitly preserved unchanged in Phase 1. |

### Mismatches / Notes

- Current repository has no committed test modules under `tests/` (project docs note only cache artifacts). Phase 1 therefore must introduce initial dedup-focused tests as part of deliverables.
- Gated phase intent requires metrics now but user-facing mode toggles later: implement internal exact dedup + metadata in Phase 1, and defer CLI/MCP `off|exact` flags to Phase 2 per phase boundary.
- Constraint reaffirmed: **no selector or extraction config changes** in `crawler/config.py` during this phase.
