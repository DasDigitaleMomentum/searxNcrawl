---
type: planning
entity: phase
plan: "http-host-origin-configuration"
phase: 1
status: completed
created: "2026-07-14"
updated: "2026-07-14"
---

# Phase 1: Align HTTP Host and Origin Configuration

> Part of [HTTP Host and Origin Configuration](../plan.md)

## Objective

Make remote HTTP access configurable through FastMCP's supported Host and Origin allowlists, preserve secure defaults, and ensure the existing browser CORS option remains functional with FastMCP 3.4.3's request guard.

## Scope

### Includes

- Declare the FastMCP version floor required for Host and Origin configuration.
- Add and document the HTTP-only Host allowlist CLI surface.
- Align configured CORS origins with FastMCP's Origin guard.
- Add focused regression and transport-isolation tests.
- Update public and curated MCP transport documentation.

### Excludes (deferred to later phases)

- Authentication for remotely exposed MCP servers.
- Automatic Host discovery and reverse-proxy configuration.
- Any default wildcard allowlist.
- Unrelated HTTP transport refactoring.

## Prerequisites

- [x] Issue #25 and its proposed workaround have been analyzed against FastMCP 3.4.3.
- [x] The upstream-aligned scope has been selected.
- [x] A grounded Phase 1 implementation plan has been authored and verified against the current source and tests.

## Deliverables

- [x] Updated dependency declaration and HTTP CLI/runtime configuration.
- [x] Regression coverage for Host allowlists, Origin forwarding, wildcards, defaults, and STDIO isolation.
- [x] Updated README and curated MCP transport documentation.
- [x] Passing focused and complete test suites.

## Acceptance Criteria

- [x] `--allowed-hosts` accepts comma-separated values, trims surrounding whitespace, and forwards non-empty entries to FastMCP in HTTP mode.
- [x] No `allowed_hosts` override is passed when the CLI option is absent, allowing FastMCP defaults or `FASTMCP_HTTP_ALLOWED_HOSTS` to apply.
- [x] `--cors-origins` continues to configure CORS middleware and also forwards the same normalized values as FastMCP `allowed_origins`.
- [x] Explicit `*` values are preserved without becoming defaults.
- [x] STDIO invocation remains free of HTTP-only Host, Origin, and middleware arguments.
- [x] Documentation provides safe exact-host examples and labels wildcard use as an explicit security trade-off.
- [x] The supported FastMCP range cannot resolve to a version lacking the forwarded parameters.
- [x] Changed behavior is covered by focused tests and the full existing suite passes.

## Dependencies on Other Phases

| Phase | Relationship | Notes |
|-------|-------------|-------|
| None | standalone | This single phase delivers the complete Issue #25 fix. |

## Notes

- FastMCP's Host/Origin guard executes before routing and before Starlette CORS middleware.
- `FASTMCP_HTTP_ALLOWED_HOSTS` expects FastMCP's JSON-list environment format.
- Binding Uvicorn to `0.0.0.0` does not identify the externally visible Host header and must not imply wildcard trust.
- Completed with 17 focused tests and 99 full-suite tests passing in an isolated uv environment.
