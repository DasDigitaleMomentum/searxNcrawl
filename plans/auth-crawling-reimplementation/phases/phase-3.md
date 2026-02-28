---
type: planning
entity: phase
plan: "auth-crawling-reimplementation"
phase: 3
status: pending
created: "2026-02-28"
updated: "2026-02-28"
---

# Phase 3: Session Capture (Isolated)

> Part of [auth-crawling-reimplementation](../plan.md)

## Objective

Isolierte Session-Capture-Funktion bereitstellen, mit robusten Completion-/Timeout-Regeln und ohne Seiteneffekte auf Crawl-Defaults.

## Scope

### Includes

- Capture-Command/Flow für manuelles Login.
- Saubere Speicherung von `storage_state`.
- Robuste Bedingungen für Erfolg/Abbruch (z. B. URL-Match, Timeout, Browser-Closed).
- Tests für Redirect-/Timeout-Kanten.

### Excludes (deferred to later phases)

- Breite Profilverwaltung und Discoverability-Features.
- Persistente Runtime-Session-Strategien als Standardmodus.

## Prerequisites

- [ ] Phase 1 und 2 abgeschlossen.
- [ ] Erwartetes Capture-Verhalten und UX-Text finalisiert.

## Deliverables

- [ ] Capture-Laufpfad mit klaren Zuständen (success/timeout/abort).
- [ ] Dokumentation für sichere Nutzung und typische Fehler.
- [ ] Regressionstests für kritische Capture-Kanten.

## Acceptance Criteria

- [ ] Nutzer kann einen validen `storage_state` reproduzierbar erzeugen.
- [ ] Timeout/Fehlerfälle sind klar und deterministisch.
- [ ] Keine Änderungen an allgemeinen Crawl-Defaults nötig.

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| 1 | blocked-by | Core-Vertrag ist Voraussetzung. |
| 2 | blocked-by | Surface-Semantik und Doku müssen vorhanden sein. |

## Notes

- Capture bleibt bewusst isoliert, um Runtime-Crawl-Pfade stabil zu halten.
