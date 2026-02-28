---
type: planning
entity: plan
plan: "markdown-dedup-pipeline"
status: active
created: "2026-02-28"
updated: "2026-02-28"
---

# Plan: markdown-dedup-pipeline

## Objective

Post-processing Markdown-Dedup (Variante B) implementieren, um intra-dokumentäre Inhaltsduplikate robust zu entfernen, unabhängig von website-spezifischen `target_elements`-Überlappungen.

## Motivation

Dieses Repo wird über eine große Bandbreite realer Seiten eingesetzt. Selector-Tuning kann nie universell korrekt sein. Daher wird ein stabiler, nachgelagerter Dedup-Schritt in der eigenen Pipeline benötigt, der Crawl4AI-Verhaltensänderungen abfedert.

## Requirements

### Functional

- [ ] Exakte Duplikate innerhalb eines Markdown-Dokuments werden deterministisch entfernt (erste Instanz bleibt erhalten).
- [ ] Dedup läuft zentral in der Dokument-Pipeline, sodass CLI und MCP gleichermaßen profitieren.
- [ ] Dedup-Metriken (z. B. entfernte Sections/Chars) werden pro Dokument verfügbar gemacht.
- [ ] Konfigurierbarer Modus mindestens `off|exact` ist verfügbar.

### Non-Functional

- [ ] Verhalten ist deterministisch und idempotent (`dedup(dedup(x)) == dedup(x)`).
- [ ] Minimal-invasive Änderung ohne invasive Selector-Neuabstimmung.
- [ ] Geringes False-Positive-Risiko im Default-Modus (`exact`).
- [ ] Rückwärtskompatibilität für bestehende Aufrufer (Default bleibt stabil dokumentiert).

## Scope

### In Scope

- Intra-Dokument-Dedup (ein Dokument enthält doppelte Blöcke/Abschnitte).
- Integration in `crawler/builder.py`-Pipeline (nach Markdown-Auswahl).
- Exponieren von Dedup-Optionen und Metriken über CLI/MCP.
- Dokumentation und Rollout-Guards.

### Out of Scope

- Cross-Dokument-Dedup über mehrere Seiten hinweg (Site-Crawl-Set).
- Umfassendes Selector-Redesign in Crawl4AI-Konfig.
- Aggressive/near-duplicate fuzzy Verfahren im ersten Schritt.

## Definition of Done

- [ ] Reproduzierbarer Problemfall (`https://docs.agno.com/introduction`) zeigt keine doppelten Kernabschnitte mehr im Default-Dedup-Modus.
- [ ] Standardfälle verlieren keine offensichtlichen legitimen Inhaltsblöcke.
- [ ] Dedup-Metriken sind in Ergebnis-Metadaten dokumentiert und nachvollziehbar.
- [ ] CLI/MCP bieten steuerbare Flags/Parameter (`off|exact`) inkl. Doku.
- [ ] Relevante Tests bestehen und neue Tests decken Idempotenz + Problemfall ab.

## Testing Strategy

- [ ] Unit-Tests für Section-Splitting, Fingerprint-Logik, Idempotenz.
- [ ] Regressions-Test für Agno-Dup-Fall.
- [ ] Integrationstests für CLI/MCP-Optionen und Metadaten-Propagation.
- [ ] Smoke-Checks auf mehreren Doku-Stacks (kein massiver Inhaltsverlust).

## Phases

| Phase | Title | Scope | Status |
|-------|-------|-------|--------|
| 1 | Exact Intra-Doc Dedup Core | [Detail](phases/phase-1.md) | pending |
| 2 | Surface Area, Guards, Docs | [Detail](phases/phase-2.md) | pending |

## Risks & Open Questions

| Risk/Question | Impact | Mitigation/Answer |
|---------------|--------|-------------------|
| Crawl4AI hat interne Dedup-Logik – reicht das bereits? | Falsche Annahme könnte Fix verzögern | Verifiziert: Die genutzte `target_elements`-Assembly dedupliziert Overlaps nicht; interne Utility-Dedup läuft nicht verlässlich auf diesem Pfad. Eigene Pipeline-Dedup bleibt erforderlich. |
| False Positives bei Dedup | Möglicher Inhaltsverlust | Start mit konservativem `exact`-Modus, Metriken/Guards, Regressionstests auf mehreren Sites. |
| Unterschiedliche Markdown-Strukturen je Site | Instabile Heuristik | Section-basierte Normalisierung + klar dokumentierte Grenzen; zunächst nur exakte Duplikate. |

## Changelog

### 2026-02-28

- Plan created
- Scope auf Variante B fokussiert, ohne Cross-Dokument-Phase
