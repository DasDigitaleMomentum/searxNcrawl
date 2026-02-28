# Review Remediation Plan (2026-02-28)

## Prioritized Findings

### P1

1. [x] **Aggressive default crawl behavior**
   - Problem: Global default uses JS reload and strict `wait_for` on `<main>`.
   - Goal: Make this behavior opt-in and keep a safe default for broad site compatibility.

2. [x] **Site crawl uses markdown profile instead of discovery profile**
   - Problem: `crawl_site_async` defaults to markdown run config.
   - Goal: Default site crawl to discovery-focused profile and keep SPA overrides compatible.

### P2

3. [x] **Multi-URL crawling opens one browser context per URL**
   - Problem: `crawl_pages_async` fan-out calls `crawl_page_async` repeatedly.
   - Goal: Use `AsyncWebCrawler.arun_many()` for batch efficiency and stability.

4. [x] **Filename collisions in multi-output mode**
   - Problem: output filenames ignore query/fragment and can overwrite each other.
   - Goal: Generate deterministic, collision-safe filenames.

5. [x] **`scripts/test-realworld.sh` can hide curl failures**
   - Problem: piping into `head` without `pipefail` can mask request errors.
   - Goal: make script fail reliably on curl/network/API errors.

6. [x] **Crawl4AI version drift risk**
   - Problem: dependency is open-ended (`>=0.7.4`).
   - Goal: pin to tested compatibility range and document upgrade policy.

7. [x] **BFS stream behavior assumption needs explicit handling**
   - Problem: code hard-forces `stream=False` with stale-sounding comment.
   - Goal: expose a controlled override and update rationale/tests accordingly.

8. [x] **Regression coverage misses real-world failing pages**
   - Problem: tests target mostly `example.com/httpbin`.
   - Goal: add configurable real-site regression runner for known failing domains (e.g. Mintlify pages).

### P3

9. [x] **No CI workflow**
   - Problem: no automated checks on push/PR.
   - Goal: add GitHub Actions workflow for unit tests + optional E2E job.

## Integration Requirement

10. [x] **Integrate `flitzrrr/searxNcrawl` PR #1**
   - Action: cherry-picked commits:
     - `a749aa75ac9b16737e46385f81bd674559f0327c`
     - `b5e0478a8b2a03c8d30a74fee97ab51c2ae517b2`

## Validation Gates

- [x] `pytest -q -m "not e2e"`
- [x] `pytest -q tests/test_e2e.py -m e2e` (best effort, with skips allowed)
- [x] `scripts/test-realworld.sh` static validation (syntax/behavior check)
- [x] Docs/README updated to reflect changed defaults and new options
