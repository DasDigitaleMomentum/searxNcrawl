---
type: planning
entity: phase
plan: "markdown-dedup-pipeline"
phase: 2
status: pending
created: "2026-02-28"
updated: "2026-02-28"
---

# Phase 2: Surface Area, Guards, Docs

> Part of [markdown-dedup-pipeline](../plan.md)

## Objective

Dedup kontrolliert nach außen verfügbar machen (CLI/MCP), Guardrails ergänzen und Dokumentation finalisieren.

## Scope

### Includes

- Option-Exponierung für Dedup-Modi (`off|exact`) in CLI/MCP.
- Guardrails (z. B. auffällige Removal-Rate als Warnsignal).
- Integrationstests für Parameterfluss und Ergebnis-Metadaten.
- Dokumentationsupdates in `docs/` für Verhalten, Grenzen, Defaults.

### Excludes (deferred to later phases)

- Cross-Dokument-Dedup.
- Aggressive/near-duplicate Modus als Default.

## Prerequisites

- [ ] Phase-1-Core ist implementiert und getestet.
- [ ] Metriken sind stabil verfügbar.

## Deliverables

- [ ] CLI-Parameter und MCP-Parameter für Dedup-Modus.
- [ ] Warn-/Guard-Mechanismen und dokumentierte Schwellwerte.
- [ ] Integrationstests für End-to-End-Ausgabe.
- [ ] Aktualisierte Feature-/Modul-Dokumentation.

## Acceptance Criteria

- [ ] Nutzer kann Dedup explizit deaktivieren (`off`) und aktivieren (`exact`).
- [ ] Default-Verhalten ist dokumentiert und reproduzierbar.
- [ ] Tests belegen, dass Flags korrekt bis in Ausgabedaten wirken.

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| 1 | blocked-by | Ohne Core/Tests aus Phase 1 keine stabile Exponierung. |

## Notes

- Fokus auf sicheren Rollout statt breiter Heuristik.
- Erweiterungen (fuzzy/cross-doc) nur bei nachgewiesenem Bedarf.
