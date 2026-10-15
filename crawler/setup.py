"""``searxncrawl setup``: register the MCP server with installed coding agents.

Agents that ship an ``mcp add``/``mcp remove`` CLI (Claude Code, Codex,
Gemini CLI) are configured through that CLI. Cursor, VS Code and Claude
Desktop have no such CLI, so their JSON config is edited directly. Every file
is backed up before it changes, and nothing is applied without confirmation
unless ``--yes`` is given.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SERVER_NAME = "searxncrawl"


@dataclass(frozen=True)
class Agent:
    key: str
    name: str
    config: Path  # file the agent reads; backed up before every change
    cli: str | None = None  # resolved executable, or None to edit `config` directly
    servers_key: str = "mcpServers"


def _app_config_dir() -> Path:
    """Per-user application config dir (where Claude Desktop and VS Code keep theirs)."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def detect_agents() -> list[Agent]:
    """Return the agents that look installed for the current user."""
    home = Path.home()
    app = _app_config_dir()
    agents = []
    for key, name, exe, config in (
        (
            "claude-code",
            "Claude Code",
            "claude",
            Path(os.environ.get("CLAUDE_CONFIG_DIR") or home) / ".claude.json",
        ),
        (
            "codex",
            "Codex",
            "codex",
            Path(os.environ.get("CODEX_HOME") or home / ".codex") / "config.toml",
        ),
        ("gemini", "Gemini CLI", "gemini", home / ".gemini" / "settings.json"),
    ):
        path = shutil.which(exe)
        if path:
            agents.append(Agent(key, name, config, cli=path))
    for key, name, config, servers_key in (
        ("cursor", "Cursor", home / ".cursor" / "mcp.json", "mcpServers"),
        ("vscode", "VS Code", app / "Code" / "User" / "mcp.json", "servers"),
        (
            "claude-desktop",
            "Claude Desktop",
            app / "Claude" / "claude_desktop_config.json",
            "mcpServers",
        ),
    ):
        if config.parent.is_dir():
            agents.append(Agent(key, name, config, servers_key=servers_key))
    return agents


AGENT_KEYS = (
    "claude-code",
    "codex",
    "gemini",
    "cursor",
    "vscode",
    "claude-desktop",
)


def _launch() -> list[str]:
    # Absolute path: GUI apps such as Claude Desktop start without the shell's PATH.
    return [shutil.which("uvx") or "uvx", SERVER_NAME]


def cli_commands(agent: Agent, env: dict[str, str], remove: bool) -> list[list[str]]:
    """Commands that apply the change through the agent's own CLI."""
    exe = agent.cli
    assert exe
    pairs = [f"{k}={v}" for k, v in env.items()]
    if agent.key == "claude-code":
        scope = ["--scope", "user"]
        drop = [exe, "mcp", "remove", *scope, SERVER_NAME]
        flags = [a for p in pairs for a in ("-e", p)]
        add = [exe, "mcp", "add", *scope, SERVER_NAME, *flags, "--", *_launch()]
    elif agent.key == "codex":
        drop = [exe, "mcp", "remove", SERVER_NAME]
        flags = [a for p in pairs for a in ("--env", p)]
        add = [exe, "mcp", "add", SERVER_NAME, *flags, "--", *_launch()]
    else:  # gemini
        scope = ["--scope", "user"]
        drop = [exe, "mcp", "remove", *scope, SERVER_NAME]
        flags = [a for p in pairs for a in ("-e", p)]
        add = [exe, "mcp", "add", *scope, SERVER_NAME, *_launch(), *flags]
    # `claude mcp add` refuses to overwrite, so re-runs remove first.
    return [drop] if remove else [drop, add]


def json_change(
    agent: Agent, env: dict[str, str], remove: bool
) -> tuple[str, str] | None:
    """Return (old_text, new_text) for a JSON config, or None if nothing changes.

    Raises ValueError when the existing file cannot be edited safely.
    """
    old_text = agent.config.read_text(encoding="utf-8") if agent.config.exists() else ""
    try:
        data = json.loads(old_text) if old_text.strip() else {}
    except json.JSONDecodeError as exc:
        # JSONC comments or trailing commas: rewriting would drop them.
        raise ValueError(f"{agent.config} is not plain JSON ({exc})") from exc
    if not isinstance(data, dict) or not isinstance(
        data.get(agent.servers_key, {}), dict
    ):
        raise ValueError(f"{agent.config} has an unexpected structure")
    servers = data.setdefault(agent.servers_key, {})
    command, *args = _launch()
    entry: dict[str, object] = {"command": command, "args": args}
    if agent.key == "vscode":
        entry = {"type": "stdio", **entry}
    if env:
        entry["env"] = env
    if remove:
        if SERVER_NAME not in servers:
            return None
        del servers[SERVER_NAME]
    elif servers.get(SERVER_NAME) == entry:
        return None
    else:
        servers[SERVER_NAME] = entry
    return old_text, json.dumps(data, indent=2) + "\n"


def backup(path: Path) -> Path | None:
    """Copy ``path`` next to itself with a timestamp suffix; never overwrites."""
    if not path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(f"{path.name}.{SERVER_NAME}-backup-{stamp}")
    n = 1
    while dest.exists():
        dest = path.with_name(f"{path.name}.{SERVER_NAME}-backup-{stamp}-{n}")
        n += 1
    shutil.copy2(path, dest)
    return dest


def _confirm(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def _apply(agent: Agent, env: dict[str, str], args: argparse.Namespace) -> bool:
    """Show, confirm, back up and apply the change for one agent. False on failure."""
    verb = "Remove from" if args.remove else "Register with"
    print(f"\n== {agent.name} ({agent.config})")
    if agent.cli:
        commands = cli_commands(agent, env, args.remove)
        for cmd in commands:
            print(f"  $ {shlex.join(cmd)}")
        if not _confirm(f"{verb} {agent.name}?", args.yes):
            print("  skipped")
            return True
        saved = backup(agent.config)
        if saved:
            print(f"  backup: {saved}")
        result = None
        for cmd in commands:
            result = subprocess.run(cmd, capture_output=True, text=True)
        assert result is not None
        output = (result.stdout + result.stderr).strip()
        if output:
            print("  " + output.replace("\n", "\n  "))
        return result.returncode == 0 or args.remove

    try:
        change = json_change(agent, env, args.remove)
    except ValueError as exc:
        print(f"  cannot edit safely, skipped: {exc}")
        return False
    if change is None:
        print("  already up to date")
        return True
    old, new = change
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"{agent.config} (current)",
        tofile=f"{agent.config} (new)",
    )
    print("".join(diff), end="")
    if not _confirm(f"{verb} {agent.name}?", args.yes):
        print("  skipped")
        return True
    saved = backup(agent.config)
    if saved:
        print(f"  backup: {saved}")
    agent.config.parent.mkdir(parents=True, exist_ok=True)
    tmp = agent.config.with_name(agent.config.name + ".tmp")
    tmp.write_text(new, encoding="utf-8")
    os.replace(tmp, agent.config)
    print("  done")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="searxncrawl setup",
        description=(
            "Register the searxNcrawl MCP server with the coding agents installed "
            "on this machine (Claude Code, Codex, Gemini CLI, Cursor, VS Code, "
            "Claude Desktop). Shows each change and asks before applying it."
        ),
    )
    parser.add_argument(
        "--searxng-url",
        help="SearXNG URL to store in the agent configs (default: ask, "
        "suggesting $SEARXNG_URL)",
    )
    parser.add_argument(
        "--agent",
        action="append",
        choices=AGENT_KEYS,
        help="Only configure this agent (repeatable; default: every detected one)",
    )
    parser.add_argument(
        "--remove", action="store_true", help="Remove the registration instead"
    )
    parser.add_argument("-y", "--yes", action="store_true", help="Apply without asking")
    args = parser.parse_args(argv)

    agents = [a for a in detect_agents() if not args.agent or a.key in args.agent]
    if not agents:
        print("No supported coding agent found.")
        return 1
    print("Detected: " + ", ".join(a.name for a in agents))

    env: dict[str, str] = {}
    if not args.remove:
        url = args.searxng_url
        if url is None:
            url = os.environ.get("SEARXNG_URL", "")
            if not args.yes:
                try:
                    url = input(f"SearXNG URL [{url or 'none'}]: ").strip() or url
                except EOFError:
                    pass
        if url:
            env["SEARXNG_URL"] = url
        if not shutil.which("uvx"):
            print("warning: uvx not found on PATH; install uv so agents can start it")

    ok = all([_apply(agent, env, args) for agent in agents])
    if not args.remove:
        print("\nRestart your agents to load searxncrawl.")
    return 0 if ok else 1
