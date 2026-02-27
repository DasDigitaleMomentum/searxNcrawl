---
type: documentation
entity: module
module: "scripts"
version: 1.0
---

# Module: scripts

> Part of [searxNcrawl](../overview.md)

## Overview

Shell helper scripts for Docker image building and integration testing. These scripts are not part of the Python package but support development and CI workflows.

### Responsibility

- **IS** responsible for: Docker image building, real-world integration tests against the Docker-deployed MCP server, extended feature tests.
- **IS NOT** responsible for: unit tests (those are in `tests/`), application logic, or Python packaging.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| Docker / Docker Compose | external | Container build and orchestration |
| curl | external | HTTP requests for MCP tool invocation in tests |
| `.env` | config | Required by test scripts for `SEARXNG_URL` and `MCP_PORT` |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `scripts/` | dir | Shell scripts directory |
| `scripts/build.sh` | file | Build Docker image (`searxncrawl:latest`) |
| `scripts/test-realworld.sh` | file | Integration test: starts Docker Compose, initialises MCP session, calls crawl/crawl_site/search tools |
| `scripts/test-extended.sh` | file | Extended integration tests (remove_links, Unicode, schema validation) |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `IMAGE_NAME` | env var | internal | `scripts/build.sh:4` | Docker image name (default: `searxncrawl`) |
| `IMAGE_TAG` | env var | internal | `scripts/build.sh:5` | Docker image tag (default: `latest`) |
| `call_tool` | function | internal | `scripts/test-realworld.sh:48` | Helper to invoke MCP tools via curl against the HTTP endpoint |

## Data Flow

1. `build.sh`: runs `docker build` with configurable image name/tag.
2. `test-realworld.sh`:
   - Reads `MCP_PORT` from `.env` (default 9555).
   - `docker compose up --build -d` starts the MCP server container.
   - Sends an `initialize` JSON-RPC request to establish an MCP session.
   - Calls `crawl`, `crawl_site`, and `search` tools via JSON-RPC over HTTP.
   - Tears down Docker Compose on exit (trap cleanup).

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_PORT` | `9555` | Port used by test scripts to reach the MCP HTTP server |
| `IMAGE_NAME` | `searxncrawl` | Docker image name for build script |
| `IMAGE_TAG` | `latest` | Docker image tag for build script |

## Inventory Notes

- **Coverage**: full
- **Notes**: All 3 shell scripts documented. `test-extended.sh` was not fully read but is referenced in the README; it runs additional integration tests.
