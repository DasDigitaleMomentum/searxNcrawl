---
type: planning
entity: plan
plan: "auth-crawling-reimplementation"
status: active
created: "2026-02-28"
updated: "2026-02-28"
---

# Plan: auth-crawling-reimplementation

## Objective

Authenticated Crawling sauber neu implementieren (ohne PR-Slop), mit klarer Scope-Begrenzung und striktem Schutz der stabilisierten Crawl-Pipeline.

## Motivation

Ein früherer Branch enthielt wertvolle Auth-Ideen, aber auch zu breite Eingriffe (u. a. Waits/SPA/Persistent-Session-Verhalten), die bestehende Funktionalität destabilisiert haben. Ziel ist ein kontrollierter Rebuild mit minimalen, nachvollziehbaren Änderungen.

## Requirements

### Functional

- [ ] Auth-Crawling wird über einen klaren, kleinen Kern eingeführt (MVP: `storage_state`-basiert).
- [ ] Python API, CLI und MCP erhalten konsistente Auth-Parameterführung.
- [ ] Session-Capture für manuelles Login wird als separater Schritt geplant (nicht in Core vermischt).
- [ ] Fehlerfälle (fehlende/ungültige Auth-States) liefern reproduzierbare, eindeutige Ergebnisse.

### Non-Functional

- [ ] **No-Drift-Guard:** Bestehende Crawl-Konfiguration bleibt unverändert, außer explizit und separat gegatete Mini-Änderungen.
- [ ] Keine "optimistischen" Änderungen an Wait-/SPA-/Persistent-Session-Defaults.
- [ ] Rückwärtskompatibles Verhalten für nicht-authentifiziertes Crawling.
- [ ] Klare Dokumentation für Nutzersteuerung und Grenzen.

## Scope

### In Scope

- Neuimplementierung Auth-Core (Konfig-Objekt + Resolver + Laufzeitanbindung).
- Parameterdurchreichung für Auth in API/CLI/MCP.
- Geplante Session-Capture-Funktion als separater Phase-Block.
- Tests für Auth-Parameterfluss und reale Nutzungspfade.

### Out of Scope

- Genereller Umbau der Crawl-Extraktionspipeline.
- Änderung von `MAIN_SELECTORS`, `EXCLUDED_SELECTORS`, `wait_for`, `js_code`, `scan_full_page`, SPA/Delay-Defaults oder Persistent-Session-Strategien als Nebeneffekt.
- Cross-Doc-Dedup und weitere nicht-authentifizierte Feature-Erweiterungen.

## Hard Guardrails (Stability)

- `crawler/config.py` bleibt in dieser Initiative **unangetastet**, sofern nicht ein separat gegateter, evidenzbasierter Mini-Fix erforderlich wird.
- Keine impliziten Default-Änderungen für bestehende Crawl-Laufpfade.
- **Security/Operations Guardrail:** IRL-Auth-Validierung bleibt ein **manueller Prozess**; keine Credentials, keine `storage_state`-Artefakte und keine sensiblen Auth-URLs werden in ein öffentliches Repo committed.
- Jede Änderung an Wait-/SPA-/Session-Verhalten benötigt:
  1) reproduzierbaren Defekt,
  2) isolierten Patch,
  3) dedizierte Regressionstests,
  4) explizite Plan-Freigabe.

## Definition of Done

- [ ] Auth-MVP ist auf Stabilitäts-Branch implementiert und getestet, ohne Drift an bestehender Crawl-Konfiguration.
- [ ] CLI + MCP + Python API bieten konsistente Auth-Nutzung.
- [ ] Session-Capture ist robust dokumentiert und getestet (inkl. Timeout/Redirect-Kanten).
- [ ] Regressionstests zeigen: bestehende (nicht-auth) Crawl-Funktionalität bleibt intakt.
- [ ] README/Modul-Doku erklären die Auth-Steuerung klar.

## Testing Strategy

- [ ] Unit-Tests für Auth-Resolver/Validierung/Precedence.
- [ ] Integrationstests für API-/CLI-/MCP-Parameterfluss.
- [ ] Reale Smoke-Tests gegen mindestens einen authentifizierten Zielpfad mit `storage_state` (lokal/manuell, nicht in CI).
- [ ] Negative Tests: ungültiger/abgelaufener State, fehlende Datei, Zugriff verweigert.
- [ ] Anti-Drift-Checks: keine unbeabsichtigten Änderungen an Crawl-Config-Defaults.

## Phases

| Phase | Title | Scope | Status |
|-------|-------|-------|--------|
| 1 | Auth Core (Storage-State MVP) | [Detail](phases/phase-1.md) | pending |
| 2 | Surface Integration (CLI + MCP + Docs) | [Detail](phases/phase-2.md) | pending |
| 3 | Session Capture (Isolated) | [Detail](phases/phase-3.md) | pending |

## Risks & Open Questions

| Risk/Question | Impact | Mitigation/Answer |
|---------------|--------|-------------------|
| Zu breite Auth-Oberfläche im MVP | Hohe Komplexität/Regressionen | MVP strikt auf `storage_state` fokussieren; weitere Parameter nachgelagert. |
| Verwechslung `auth_profile` vs. `storage_state` Semantik | Falsche Erwartungen, fragile Laufzeit | Profil nur als optionalen Komfortpfad später und explizit dokumentieren. |
| Drift durch Nebenänderungen an Wait/SPA/Session | Stabilitätsverlust | Hard Guardrails + gesondertes Gate pro Abweichung. |
| Unterschiedliche Fehlerbehandlung in API/CLI/MCP | Inkonsistente UX | Einheitlichen Fehlervertrag definieren und testen. |

## Changelog

### 2026-02-28

- Plan erstellt für saubere Neuimplementierung von Auth-Crawling
- Stabilitäts-Guardrails gegen Config-/Runtime-Drift ergänzt
