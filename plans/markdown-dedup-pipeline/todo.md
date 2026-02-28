---
type: planning
entity: todo
plan: "markdown-dedup-pipeline"
updated: "2026-02-28"
---

# Todo: markdown-dedup-pipeline

> Tracking [markdown-dedup-pipeline](plan.md)

## Active Phase: 1 - Exact Intra-Doc Dedup Core

### Phase Context

- **Scope**: [Phase 1](phases/phase-1.md)
- **Implementation**: [Phase 1 Plan](implementation/phase-1-impl.md)
- **Latest Handover**: _pending_
- **Relevant Docs**:
  - [Project Overview](../docs/overview.md)
  - [crawler-document-pipeline](../docs/modules/crawler-document-pipeline.md)
  - [crawler-config](../docs/modules/crawler-config.md)
  - [crawler-cli](../docs/modules/crawler-cli.md)
  - [crawler-mcp-server](../docs/modules/crawler-mcp-server.md)

### Pending

- [ ] Dedup-Core API entwerfen (Section split, normalize, exact fingerprint) <!-- added: 2026-02-28 -->
- [ ] Hook-Point in `crawler/builder.py` final festlegen <!-- added: 2026-02-28 -->
- [ ] Dedup-Metriken in Metadatenmodell spezifizieren <!-- added: 2026-02-28 -->
- [ ] Unit-Tests (inkl. Idempotenz) hinzufügen <!-- added: 2026-02-28 -->
- [ ] Regressionsfall `docs.agno.com/introduction` als Testfall/Fixture absichern <!-- added: 2026-02-28 -->

### In Progress

- [ ] _none_

### Completed

- [x] Plan und Phasenartefakte initial erstellt <!-- completed: 2026-02-28 -->
- [x] Vorabprüfung: Crawl4AI interne Dedup-Pfade für target_elements-Overlap nicht ausreichend <!-- completed: 2026-02-28 -->

### Blocked

- [ ] _none_

## Changelog

### 2026-02-28

- Todo initialisiert für Phase 1
- Scope gemäß Nutzerentscheidung auf Variante B ohne Cross-Dokument-Phase gesetzt
