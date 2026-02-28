---
type: planning
entity: phase
plan: "markdown-dedup-pipeline"
phase: 1
status: pending
created: "2026-02-28"
updated: "2026-02-28"
---

# Phase 1: Exact Intra-Doc Dedup Core

> Part of [markdown-dedup-pipeline](../plan.md)

## Objective

Einen konservativen, deterministischen Exact-Dedup-Kern für einzelne Markdown-Dokumente implementieren und in die Builder-Pipeline integrieren.

## Scope

### Includes

- Implementierung einer Section-/Block-basierten Exact-Dedup-Logik.
- Normalisierung für stabile Fingerprints (Whitespace/line-endings).
- Hook in der Dokument-Pipeline nach Markdown-Auswahl.
- Dedup-Metriken im `CrawledDocument.metadata` (oder äquivalent) ergänzen.
- Unit-Tests für Kernlogik + Idempotenz.

### Excludes (deferred to later phases)

- CLI/MCP-Flags und UX-Surface (Phase 2).
- Near-duplicate/fuzzy Dedup.
- Cross-Dokument-Dedup.

## Prerequisites

- [ ] Referenzpfad in `crawler/builder.py` für Hook-Integration final festgelegt.
- [ ] Agno-Reprofall und erwartetes Verhalten als Regression-Fall dokumentiert.

## Deliverables

- [ ] Dedup-Core-Modul/Funktionen in `crawler/`.
- [ ] Pipeline-Integration in Builder.
- [ ] Metadatenfelder für Dedup-Stats.
- [ ] Unit-Tests für Exact-Dedup und Idempotenz.

## Acceptance Criteria

- [ ] Agno-Fall enthält keine doppelt wiederholten Kernsektionen mehr.
- [ ] `dedup(dedup(md)) == dedup(md)` für repräsentative Fixtures.
- [ ] Bei Dokumenten ohne Duplikate bleibt Inhalt unverändert (bis auf neutrale Normalisierung).

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| 2 | blocks | Phase 2 setzt Core + Metriken aus Phase 1 voraus. |

## Notes

- Analyse zeigte: Crawl4AI `target_elements`-Zusammenführung kann Overlap-Duplikate erzeugen (Parent+Child).
- Interne Crawl4AI-Dedup-Helfer sind nicht der verlässliche Fixpfad für diese Pipeline.
