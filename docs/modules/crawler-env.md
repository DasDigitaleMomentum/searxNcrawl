---
type: documentation
entity: module
module: "crawler-env"
version: 1.0
---

# Module: crawler-env

> Part of [searxNcrawl](../overview.md)

## Overview

`crawler/env.py` provides a shared `.env` configuration loader used by both the CLI (`crawler.cli`) and the MCP server (`crawler.mcp_server`).

### Responsibility

- Load environment variables from `.env` files with a defined search order.
- Fall back to the user config directory (`~/.config/searxncrawl/.env`) when no local `.env` exists.
- Auto-create the config file from `.env.example` for first-time setup.

### Dependencies

| Dependency | Type | Purpose |
|-----------|------|---------|
| `python-dotenv` | library | `load_dotenv()` for parsing `.env` files. |

## Structure

| Path | Type | Purpose |
|------|------|---------|
| `crawler/env.py` | file | Shared config loading with CWD → user-config fallback. |

## Key Symbols

| Symbol | Kind | Visibility | Location | Purpose |
|--------|------|------------|----------|---------|
| `CONFIG_DIR` | const | public | `crawler/env.py:24` | Path to `~/.config/searxncrawl/`. |
| `CONFIG_ENV_FILE` | const | public | `crawler/env.py:25` | Path to `~/.config/searxncrawl/.env`. |
| `load_config` | function | public | `crawler/env.py:28` | Load `.env` with CWD-first, config-dir fallback, auto-create from `.env.example`. |

## Data Flow

1. Caller imports and invokes `load_config()` at module level.
2. Function checks CWD for `.env` → loads if found.
3. Falls back to `~/.config/searxncrawl/.env` → loads if found.
4. If neither exists, copies `.env.example` from package root to config dir and loads it.
5. Environment variables (`SEARXNG_URL`, etc.) are now available via `os.getenv()`.

## Configuration

- Search order:
  1. `./.env` (current working directory)
  2. `~/.config/searxncrawl/.env`
  3. Auto-copy from `.env.example` when available

## Consumers

- `crawler/cli.py` — invokes `load_config()` at import time.
- `crawler/mcp_server.py` — invokes `load_config()` before reading env vars.

## Inventory Notes

- **Coverage**: full
- **Notes**: Extracted from `crawler/cli.py` (Issue #17) to ensure both CLI and MCP server share the same config resolution.
