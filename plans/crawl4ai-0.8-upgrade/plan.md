# Crawl4AI 0.8.x Upgrade Branch Plan (2026-02-28)

## Goal

Upgrade from `crawl4ai>=0.7.4,<0.8.0` to a tested `0.8.x` range with no functional regressions in:
- single-page crawl
- multi-URL batch crawl (`arun_many`)
- site crawl (BFS, discovery profile, stream override)
- CLI + MCP interfaces

## Scope

### 1) Dependency & Environment Baseline
- [ ] bump dependency range in `pyproject.toml` to `crawl4ai>=0.8.0,<0.9.0`
- [ ] recreate virtualenv and install dependencies cleanly
- [ ] capture baseline failures from:
  - [ ] `pytest -q -m "not e2e"`
  - [ ] `pytest -q tests/test_e2e.py -m e2e`

### 2) API/Behavior Compatibility
- [ ] validate `CrawlerRunConfig` compatibility for used fields (`wait_until`, `delay_before_return_html`, `stream`, `deep_crawl_strategy`, selectors)
- [ ] validate `AsyncWebCrawler.arun` and `arun_many` return-shape assumptions
- [ ] validate `BFSDeepCrawlStrategy` + `DomainFilter` behavior
- [ ] validate auth path compatibility (cookies/storage_state/profile)

### 3) Code Adaptation
- [ ] patch incompatibilities in:
  - [ ] `crawler/config.py`
  - [ ] `crawler/__init__.py`
  - [ ] `crawler/site.py`
  - [ ] `crawler/cli.py`
  - [ ] `crawler/mcp_server.py`
- [ ] keep aggressive SPA mode opt-in only
- [ ] keep discovery profile as site-crawl default

### 4) Tests & Regression Coverage
- [ ] update/add tests for changed 0.8 behavior
- [ ] run full unit suite and fix regressions
- [ ] run E2E suite (best effort)
- [ ] run `scripts/test-regression.sh` against configured URL set

### 5) Documentation & Release Safety
- [ ] update README/docs for final supported 0.8.x range
- [ ] add upgrade notes/changelog entry with known caveats
- [ ] include before/after validation evidence in PR

## Exit Criteria

- [ ] `pytest -q -m "not e2e"` green
- [ ] `pytest -q tests/test_e2e.py -m e2e` green/skips only due external dependencies
- [ ] no known regressions on regression URL list
- [ ] docs updated for final version range
