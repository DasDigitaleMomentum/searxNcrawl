---
type: planning
entity: implementation-plan
plan: "http-host-origin-configuration"
phase: 1
status: completed
created: "2026-07-14"
updated: "2026-07-14"
---

# Implementation Plan: Phase 1 - Align HTTP Host and Origin Configuration

> Implements [Phase 1](../phases/phase-1.md) of [http-host-origin-configuration](../plan.md)

## Approach

Raise the declared FastMCP floor to the release that introduced the public Host/Origin request-guard controls, then extend `crawler.mcp_server.main` with one normalized comma-separated Host allowlist. Build HTTP `run_kwargs` conditionally so an omitted option leaves FastMCP's secure defaults and environment settings intact, while configured CORS origins are forwarded to both FastMCP's request guard and the existing Starlette response middleware. Keep the STDIO branch and Docker command unchanged. Cover the CLI-to-runtime wiring and the real FastMCP ASGI guard, then document exact-host configuration, the upstream JSON-list environment variable, and wildcard risk.

## Affected Modules

| Module | Change Type | Description |
|--------|-------------|-------------|
| [crawler-mcp-server](../../../docs/modules/crawler-mcp-server.md) | modify | Add HTTP Host CLI parsing and forward normalized Host/Origin allowlists through FastMCP's public runtime parameters. |
| [mcp-tools-and-transports](../../../docs/features/mcp-tools-and-transports.md) | modify | Document Host/Origin request protection, CORS separation, and HTTP-only configuration. |
| Project dependency metadata | modify | Require `fastmcp>=3.4.3`, the first release with the selected guard/runtime API. |
| MCP HTTP tests | modify | Extend focused CORS/runtime tests with Host forwarding, Origin forwarding, real guard behavior, defaults, wildcards, and STDIO isolation. |
| Public configuration docs | modify | Add safe CLI and `FASTMCP_HTTP_ALLOWED_HOSTS` examples without changing container defaults. |

## Required Context

| File | Why |
|------|-----|
| `plans/http-host-origin-configuration/plan.md` | Gated objective, requirements, exclusions, and Definition of Done. |
| `plans/http-host-origin-configuration/phases/phase-1.md` | Authoritative single-phase scope and acceptance criteria. |
| `crawler/mcp_server.py` | `main()` owns argument parsing, HTTP `run_kwargs`, CORS middleware construction, and the isolated STDIO branch. |
| `tests/test_cors.py` | Existing CLI/runtime and middleware coverage to preserve and strengthen. |
| `tests/test_mcp_server.py` | Existing MCP server tests and current logging/STDIO behavior that must remain unaffected. |
| `pyproject.toml` | Sole dependency declaration; there is no repository lockfile. |
| `README.md` | Public install, MCP HTTP, CORS, Docker, configuration, and dependency documentation. |
| `.env.example` | Auto-copied sample configuration and suitable location for a commented upstream environment example. |
| `docker-compose.yml` | Confirms HTTP binds to `0.0.0.0`, reads `.env`, and currently opts into no Host/Origin wildcard. |
| `docs/overview.md` | Curated architecture and entry-point inventory. |
| `docs/modules/crawler-mcp-server.md` | Curated `main`/runtime configuration inventory to update. |
| `docs/features/mcp-tools-and-transports.md` | Curated HTTP transport behavior and Docker configuration to update. |

## Implementation Steps

### Step 1: Declare the supported FastMCP API floor

- **What**: Change the project dependency and the README dependency reference from `fastmcp>=2.0.0` to `fastmcp>=3.4.3`.
- **Where**: `pyproject.toml` `[project].dependencies`; `README.md` Dependencies section.
- **Why**: `allowed_hosts` and `allowed_origins`, the corresponding settings, and the Host/Origin guard are public FastMCP 3.4.3 surfaces; retaining a 2.x floor would permit an incompatible installation.
- **Considerations**: Do not add an upper bound or generate a lockfile. This is an intentional minimum-version compatibility change already accepted by the gated phase.

### Step 2: Normalize HTTP allowlist input

- **What**: Add a small internal comma-separated-value normalizer and use it for both `--allowed-hosts` and the existing `--cors-origins`: trim surrounding whitespace, discard empty entries, preserve order and explicit `*`, and represent absent/effectively empty input as no override.
- **Where**: `crawler/mcp_server.py`, near the CLI entry-point helpers and `main()` argument declarations.
- **Why**: The Host acceptance criteria require non-empty normalized entries, and sharing normalization ensures the exact same Origin list reaches both guard and CORS layers.
- **Considerations**: Add `--allowed-hosts` with default `None` and HTTP-specific help text describing Host-header validation rather than bind addresses. Do not add or read an `ALLOWED_HOSTS` variable. Parsing the option in STDIO mode is acceptable only if it is never forwarded there.

### Step 3: Wire Host and Origin protection only into HTTP runtime arguments

- **What**: In `main()`'s HTTP branch, conditionally add `allowed_hosts` only when the normalized CLI Host list is non-empty. When normalized CORS origins are present, add that same list as `allowed_origins` and retain the existing `CORSMiddleware` using the identical list. Leave absent keys out of `run_kwargs` so FastMCP defaults or upstream environment settings can resolve them.
- **Where**: `crawler/mcp_server.py::main`, specifically HTTP `run_kwargs` construction and CORS middleware setup.
- **Why**: This admits explicitly trusted remote Host headers and lets trusted browser origins pass the upstream request guard before receiving CORS response headers.
- **Considerations**: Do not pass `host_origin_protection=False`. Do not infer trust from `--host 0.0.0.0`. Do not default either allowlist to `*`. Preserve `allow_credentials`, methods, headers, logging, host, and port behavior unless a test exposes a direct FastMCP 3.4.3 compatibility requirement within this scope.

### Step 4: Preserve and prove STDIO isolation and HTTP forwarding

- **What**: Refocus/extend the invocation-based tests around `mcp_server.main()` so mocked `mcp.run()` calls establish: absent Host/Origin options omit all allowlist/middleware overrides; Host values cover single, multiple, whitespace-padded/empty entries, and explicit wildcard cases; configured origins are identical in `allowed_origins` and `CORSMiddleware.allow_origins`; and STDIO forwards none of `host`, `port`, `allowed_hosts`, `allowed_origins`, or `middleware`, even when HTTP-only flags are supplied.
- **Where**: `tests/test_cors.py::TestCorsIntegration` and related argument-parsing coverage; add a clearly named Host-focused test class in the same file or a narrowly scoped companion test file if separation materially improves clarity.
- **Why**: These tests directly cover the repository-owned CLI normalization and `run_kwargs` boundary rather than reconstructing argparse or middleware logic independently.
- **Considerations**: Preserve the existing encoding-configuration tests and CORS middleware assertions. The current STDIO assertion must be corrected to include the already-existing `log_level` argument while still asserting HTTP-only keys are absent; this records current behavior rather than changing it. Avoid source-text/duplicated-parser tests as the primary proof of behavior.

### Step 5: Exercise the supported FastMCP guard at ASGI level

- **What**: Add focused `TestClient` requests against a FastMCP HTTP app to show an untrusted public Host is rejected with 421 by default, an untrusted browser Origin is rejected with 403, and explicitly configured exact Host/Origin values reach MCP routing/session handling. Include explicit wildcard admission without making wildcard a fixture/default.
- **Where**: Host/Origin-focused coverage alongside `tests/test_cors.py`, using the installed FastMCP 3.4.3 public `http_app()`/ASGI surface rather than importing guard internals.
- **Why**: Mocked `mcp.run()` assertions prove wiring but cannot detect upstream guard semantics or parameter incompatibility.
- **Considerations**: Use a valid MCP initialize request under the app lifespan when asserting successful admission, or assert that an allowed request passes the guard and reaches normal route validation if that is more stable. Keep tests in-process and deterministic; do not open a network port. Assert guard status codes specifically so failures cannot be hidden by unrelated protocol responses.

### Step 6: Document secure HTTP deployment configuration

- **What**: Document `--allowed-hosts`, exact-host examples, comma-separated normalization, and `FASTMCP_HTTP_ALLOWED_HOSTS` using FastMCP's JSON-list syntax. Explain that bind address, Host/Origin request protection, and CORS response headers are distinct; `--cors-origins` configures both Origin trust and CORS; omitted options retain secure defaults; and `*` is an explicit security trade-off suitable only when intentionally chosen. Add only a commented exact-host example to `.env.example` if including the setting there.
- **Where**: `README.md` MCP startup/configuration/CORS sections and dependency listing; `.env.example`; `docs/modules/crawler-mcp-server.md` Configuration; `docs/features/mcp-tools-and-transports.md` Configuration and edge cases.
- **Why**: Remote users need both CLI and upstream environment paths and must understand why CORS alone cannot bypass FastMCP's earlier request guard.
- **Considerations**: Name only `FASTMCP_HTTP_ALLOWED_HOSTS`; do not invent `ALLOWED_HOSTS`. Do not advertise protection disabling. Examples should prefer exact names such as `mcp.example.com`; clearly label wildcard Hosts and Origins as unsafe broad access. Do not add wildcard values or new command arguments to `docker-compose.yml`; its existing `env_file` already permits an operator-supplied upstream setting.

## Testing Plan

| Test Type | What to Test | Expected Outcome |
|-----------|-------------|-----------------|
| CLI/runtime integration | Absent, single, multiple, whitespace/empty, and wildcard Host input; matching Origin and middleware forwarding. | HTTP `mcp.run()` receives only normalized, explicitly configured overrides, and both Origin consumers receive the same list. |
| Transport isolation | Supply HTTP-only options while selecting STDIO. | Existing STDIO call shape and encoding setup remain intact; no HTTP-only runtime key is forwarded. |
| ASGI integration | Default rejection and configured exact/wildcard admission through FastMCP's public HTTP app. | Untrusted Host/Origin receive 421/403; explicitly trusted values pass the guard. |
| Regression | Existing MCP, CORS, CLI, crawl, search, and document tests. | Complete suite passes without disabled or weakened coverage. |

**Verify:** `pytest -q tests/test_cors.py && pytest -q`

### Test Integrity Constraints

- `tests/test_cors.py` is intentionally affected: retain its assertions that CORS middleware is omitted by default and constructed with the configured values, but extend assertions to include `allowed_origins` and replace duplicated-parser/source-presence checks with behavior through `main()` where practical.
- `tests/test_cors.py::TestCorsIntegration::test_stdio_transport_ignores_cors` currently omits the source's existing `log_level` keyword. Update only that stale expectation, then explicitly prove all HTTP-only keys remain absent; do not remove the STDIO isolation assertion.
- `tests/test_cors.py` encoding tests and `tests/test_mcp_server.py` logging/encoding tests cover unchanged behavior and must remain enabled and passing.
- No existing tests may be deleted, skipped, marked expected-failure, or relaxed to accept 421/403 where configured admission is required.
- ASGI admission tests must distinguish passing the Host/Origin guard from merely receiving an arbitrary non-success response; use a successful initialize exchange where stable, otherwise assert the expected downstream protocol status while separately excluding guard responses.
- The full pre-existing suite must pass after the focused tests; failures outside the changed behavior must be investigated rather than hidden by narrowing discovery.

## Rollback Strategy

Revert the dependency floor, CLI/helper/runtime wiring, focused tests, and documentation as one phase change. Because no persisted data, schema, Docker default, or environment-variable alias is introduced, rollback requires no migration. Do not retain documentation or tests for runtime parameters if the dependency/runtime wiring is rolled back.

## Open Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Host environment configuration | New project variable vs upstream setting | `FASTMCP_HTTP_ALLOWED_HOSTS` only | Gated scope requires the public upstream surface and forbids `ALLOWED_HOSTS`. |
| Wildcard defaults | Implicit wildcard vs explicit opt-in | Explicit opt-in only | Preserves FastMCP protection and existing Docker defaults. |
| Origin handling | Guard only, CORS only, or both | Same normalized list to both | The guard executes before CORS, while CORS separately controls browser-readable responses. |

## Reality Check

### Code Anchors Used

| File | Symbol/Area | Why it matters |
|------|-------------|----------------|
| `crawler/mcp_server.py` | `main()` argument parser and HTTP/STDIO branches | HTTP currently forwards host/port/middleware/log level; STDIO has a separate fixed call and encoding setup. |
| `crawler/mcp_server.py` | `args.cors_origins` normalization and `run_kwargs` | Current code trims origins only for middleware and does not filter empty entries or pass `allowed_origins`. |
| `tests/test_cors.py` | `TestCorsIntegration` | Existing mocks expose the exact `mcp.run()` keyword boundary and middleware internals. |
| `tests/test_cors.py` | `test_stdio_transport_ignores_cors` | Existing expected call predates the current `log_level` keyword and needs a non-behavioral expectation correction. |
| `pyproject.toml` | `[project].dependencies` | Current `fastmcp>=2.0.0` floor does not guarantee the 3.4.3 API. |
| `README.md` | MCP Server, CORS, Configuration, Dependencies | Current public docs describe CORS but not Host/Origin guard configuration. |
| `.env.example` / `docker-compose.yml` | sample env, `env_file`, and HTTP command | Compose binds `0.0.0.0` and forwards `.env`, but defines no wildcard or allowlist default; this must stay unchanged. |
| FastMCP 3.4.3 public HTTP API/settings | `FastMCP.run`, `FastMCP.http_app`, `FASTMCP_HTTP_ALLOWED_HOSTS` | Upstream 3.4.3 exposes `allowed_hosts`/`allowed_origins`, defaults protection on, and expects environment lists in JSON format. |

### Mismatches / Notes

- The repository has no dependency lockfile, so the required floor change is confined to `pyproject.toml` plus the README's dependency statement.
- `tests/test_cors.py` contains parser/middleware reconstructions and unused inspection imports; behavior-level invocation tests are the reliable acceptance boundary, but existing coverage must be replaced only where the stronger test proves the same behavior.
- The current STDIO source passes `log_level=LOG_LEVEL_STR`, while one CORS test expects only `transport="stdio"`. The implementation must not remove logging to satisfy that stale assertion.
- Local verification was not executable in the inspection environment because the project package and runtime dependencies are not installed for the system `pytest`; this is an environment limitation, not a discovered source mismatch. The implementation verify command assumes the project development dependencies are installed.
- No scope mismatch or unresolved design choice requiring primary judgment was found.
- Implementation followed the planned approach without scope deviations. Because the system Python lacked project dependencies, final verification used an isolated uv environment without creating a lockfile: `uv run --isolated --no-project --with-editable '.[dev]' pytest -q tests/test_cors.py && uv run --isolated --no-project --with-editable '.[dev]' pytest -q` (17 focused and 99 full-suite tests passed).
