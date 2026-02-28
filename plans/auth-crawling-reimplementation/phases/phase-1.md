---
type: planning
entity: phase
plan: "auth-crawling-reimplementation"
phase: 1
status: pending
created: "2026-02-28"
updated: "2026-02-28"
---

# Phase 1: Auth Core (Storage-State MVP)

> Part of [auth-crawling-reimplementation](../plan.md)

## Objective

Minimalen, robusten Auth-Core einführen, der `storage_state` sauber in Crawl-Laufpfade integriert, ohne bestehende Crawl-Konfiguration zu verändern.

## Scope

### Includes

- Auth-Konfigurationsmodell und Resolver (MVP-zentriert).
- API-Threading für Auth in zentralen Crawl-Funktionen.
- Klare Fehlerbehandlung für fehlende/ungültige State-Dateien.
- Unit-Tests für Resolver-/Validierungslogik.

### Excludes (deferred to later phases)

- CLI/MCP-Oberflächenarbeit und UX-Feinschliff.
- Session-Capture-UX.
- Profile-Management, Cookie/Header-Matrix als Default-MVP-Bestandteil.

## Prerequisites

- [ ] Guardrail-Checkliste aus Plan akzeptiert.
- [ ] Zielvertrag für Auth-Fehlerfälle abgestimmt.

## Deliverables

- [ ] Core-Auth-Modul mit validierter `storage_state`-Anbindung.
- [ ] API-Pfade mit Auth-Option und Tests.
- [ ] Dokumentierte Invarianten: keine Config-/Default-Drift.

## Acceptance Criteria

- [ ] Auth mit gültigem `storage_state` funktioniert in API-Pfaden reproduzierbar.
- [ ] Ungültiger/fehlender `storage_state` liefert klaren Fehlerpfad.
- [ ] Nicht-authentifizierte Aufrufe verhalten sich unverändert.

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| 2 | blocks | Surface-Integration setzt stabilen Core voraus. |
| 3 | blocks | Capture wird gegen Core-Vertrag implementiert. |

## Notes

- Fokus ist minimaler Kern, kein Surface-Overreach.
- Keine Änderungen an `crawler/config.py` in dieser Phase.
