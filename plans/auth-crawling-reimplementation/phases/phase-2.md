---
type: planning
entity: phase
plan: "auth-crawling-reimplementation"
phase: 2
status: pending
created: "2026-02-28"
updated: "2026-02-28"
---

# Phase 2: Surface Integration (CLI + MCP + Docs)

> Part of [auth-crawling-reimplementation](../plan.md)

## Objective

Auth-Core kontrolliert in CLI und MCP verfügbar machen, inklusive klarer Nutzerdokumentation und konsistenter Parametersemantik.

## Scope

### Includes

- CLI-Auth-Parameter im MVP-Umfang.
- MCP-Auth-Parameter im MVP-Umfang.
- Einheitliche Resolver-Nutzung (kein Surface-spezifischer Wildwuchs).
- README/Modul-Doku aktualisieren.
- Integrationstests für API/CLI/MCP-Parität.

### Excludes (deferred to later phases)

- Session-Capture-Implementierung.
- Erweiterte Profil- und Komfortfeatures über MVP hinaus.

## Prerequisites

- [ ] Phase 1 abgeschlossen und stabil.
- [ ] Fehlersignaturen und Validierungsregeln festgelegt.

## Deliverables

- [ ] CLI + MCP Parameter mit konsistenter Semantik.
- [ ] Dokumentierte Defaults/Beispiele.
- [ ] Integrationstests für Parameterfluss und Fehlerpfade.

## Acceptance Criteria

- [ ] Nutzer kann Auth in CLI + MCP reproduzierbar steuern.
- [ ] API/CLI/MCP verhalten sich semantisch gleich.
- [ ] Nicht-auth-Pfade bleiben stabil.

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| 1 | blocked-by | Surface benötigt stabilen Core-Vertrag. |
| 3 | blocks | Capture referenziert Surface-Semantik in Doku/Flows. |

## Notes

- Dokumentation muss explizit No-Drift-Invariante erwähnen.
