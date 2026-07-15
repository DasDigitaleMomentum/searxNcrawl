---
type: planning
entity: plan
plan: "http-host-origin-configuration"
status: completed
created: "2026-07-14"
updated: "2026-07-14"
---

# Plan: HTTP Host and Origin Configuration

## Objective

Restore intentional remote access to the Streamable HTTP MCP transport after FastMCP 3.4.3 introduced Host and Origin protection, while preserving that protection by default and exposing clear configuration for trusted hosts and browser origins.

## Motivation

Issue [#25](https://github.com/DasDigitaleMomentum/searxNcrawl/issues/25) reports that HTTP deployments bound to `0.0.0.0`, including the repository's Docker Compose setup, reject non-loopback requests with HTTP 421. FastMCP 3.4.3 added the guard responsible for this behavior. searxNcrawl needs to expose the upstream allowlist controls without silently enabling wildcard access, and its existing CORS option must also satisfy FastMCP's earlier Origin guard.

## Requirements

### Functional

- [x] HTTP users can provide a comma-separated Host-header allowlist through a `--allowed-hosts` CLI option.
- [x] Parsed allowed hosts are passed to FastMCP only for the HTTP transport.
- [x] FastMCP's existing `FASTMCP_HTTP_ALLOWED_HOSTS` environment configuration is documented as the environment-based alternative; no duplicate searxNcrawl-specific environment variable is introduced.
- [x] Existing `--cors-origins` values are passed both to Starlette CORS middleware and FastMCP's `allowed_origins` request guard.
- [x] Wildcard host and origin values remain explicit opt-ins and are not enabled by default in Docker Compose.
- [x] STDIO behavior remains unchanged.

### Non-Functional

- [x] The FastMCP dependency floor guarantees support for `allowed_hosts` and `allowed_origins` runtime parameters.
- [x] Help text and user documentation distinguish Host/Origin request protection from CORS response headers.
- [x] The change uses FastMCP's public configuration surface rather than replacing or bypassing its guard.
- [x] Existing MCP and CORS tests continue to pass.

## Scope

### In Scope

- FastMCP dependency minimum required by the selected API.
- MCP server CLI and HTTP runtime wiring for allowed hosts and origins.
- Focused automated tests for parsing, HTTP forwarding, wildcard handling, and STDIO isolation.
- README/configuration documentation for CLI and `FASTMCP_HTTP_ALLOWED_HOSTS` usage.
- Updates to existing curated MCP transport documentation after implementation.

### Out of Scope

- Disabling FastMCP Host/Origin protection by default.
- Automatically trusting every Host when binding to `0.0.0.0`.
- Adding MCP authentication or authorization.
- Introducing a second `ALLOWED_HOSTS` environment variable.
- Reverse-proxy discovery or automatic inference of externally visible hostnames.
- General redesign of the HTTP transport or CORS subsystem.

## Definition of Done

- [x] A remote HTTP deployment can admit configured Host headers without receiving FastMCP's 421 response.
- [x] Browser origins configured through `--cors-origins` reach the CORS middleware instead of being rejected by FastMCP's Origin guard.
- [x] Omitting both options retains FastMCP's secure defaults.
- [x] Wildcards work only when explicitly configured.
- [x] STDIO calls do not receive HTTP-only arguments.
- [x] The declared FastMCP minimum supports every forwarded runtime argument.
- [x] Focused tests exercise the changed behavior and the complete test suite passes.
- [x] README and curated MCP transport docs describe the final configuration accurately.

## Testing Strategy

- [x] Add CLI/runtime integration tests that inspect the arguments forwarded to `mcp.run()` for absent, single, multiple, whitespace-padded, and wildcard host values.
- [x] Extend CORS integration tests to verify matching `allowed_origins` forwarding.
- [x] Verify STDIO ignores Host and Origin HTTP configuration.
- [x] Exercise FastMCP's actual Host/Origin guard with ASGI requests showing rejection by default and admission when configured.
- [x] Run the complete pytest suite after the focused tests pass.

## Phases

| Phase | Title | Scope | Status |
|-------|-------|-------|--------|
| 1 | Align HTTP Host and Origin Configuration | [Detail](phases/phase-1.md) | completed |

## Risks & Open Questions

| Risk/Question | Impact | Mitigation/Answer |
|---------------|--------|-------------------|
| Raising the dependency from FastMCP 2.x to 3.4.3 is a breaking compatibility change for users pinning older releases. | Dependency resolution or upgrade behavior may change. | The new public parameters and reported guard both belong to 3.4.3; declare the real supported floor rather than keep a misleading range. |
| `allowed_hosts=["*"]` permits any Host header. | It weakens DNS-rebinding protection and broadens exposure of unauthenticated deployments. | Keep wildcard access explicit, document the risk, and do not add it to Docker defaults. |
| CORS and FastMCP Origin protection are separate controls. | Configuring only one can still leave browser clients blocked or unable to read responses. | Forward configured origins to both controls and document their distinct roles. |
| Unit tests that only mock `mcp.run()` could miss upstream guard semantics. | Wiring may pass while real requests still fail. | Include a focused ASGI-level guard test if it is stable with the supported FastMCP API. |

## Changelog

### 2026-07-14

- Plan created from Issue #25 analysis.
- Scope confirmed as the upstream-aligned fix: FastMCP >=3.4.3, CLI host allowlist, upstream environment variable documentation, Origin/CORS alignment, and focused coverage.
- Phase 1 completed: runtime wiring, dependency floor, regression coverage, and public and curated documentation are aligned.
- Verification passed in an isolated development environment: 17 focused tests and 99 full-suite tests.
- Plan completed.
