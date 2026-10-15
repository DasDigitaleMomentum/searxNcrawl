from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from crawler import mcp_server, setup

UVX = "/opt/uv/uvx"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Isolated HOME with no agents installed; CLI calls are recorded, not run."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    for var in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "SEARXNG_URL"):
        monkeypatch.delenv(var, raising=False)

    state = SimpleNamespace(home=tmp_path, path={"uvx": UVX}, calls=[], rc=0)
    monkeypatch.setattr(setup.shutil, "which", lambda exe: state.path.get(exe))

    def fake_run(cmd, **kwargs):
        state.calls.append(cmd)
        return SimpleNamespace(returncode=state.rc, stdout="", stderr="")

    monkeypatch.setattr(setup.subprocess, "run", fake_run)
    monkeypatch.setattr(
        "builtins.input", lambda prompt="": pytest.fail(f"unexpected prompt {prompt}")
    )
    return state


def _cursor(state: SimpleNamespace) -> Path:
    path = state.home / ".cursor" / "mcp.json"
    path.parent.mkdir()
    return path


def _backups(path: Path) -> list[Path]:
    return sorted(path.parent.glob(f"{path.name}.searxncrawl-backup-*"))


def test_detects_nothing_in_empty_home(env):
    assert setup.detect_agents() == []
    assert setup.main(["--yes"]) == 1


def test_detects_cli_and_config_dir_agents(env):
    env.path["claude"] = "/bin/claude"
    env.path["codex"] = "/bin/codex"
    (env.home / ".cursor").mkdir()
    (setup._app_config_dir() / "Code" / "User").mkdir(parents=True)
    (setup._app_config_dir() / "Claude").mkdir(parents=True)

    agents = {a.key: a for a in setup.detect_agents()}

    assert set(agents) == {"claude-code", "codex", "cursor", "vscode", "claude-desktop"}
    assert set(agents) <= set(setup.AGENT_KEYS)
    assert agents["claude-code"].config == env.home / ".claude.json"
    assert agents["codex"].config == env.home / ".codex" / "config.toml"
    assert agents["vscode"].servers_key == "servers"


def test_cli_agent_dirs_follow_env_overrides(env, monkeypatch):
    env.path["claude"] = "/bin/claude"
    env.path["codex"] = "/bin/codex"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(env.home / "cc"))
    monkeypatch.setenv("CODEX_HOME", str(env.home / "cx"))

    configs = {a.key: a.config for a in setup.detect_agents()}

    assert configs["claude-code"] == env.home / "cc" / ".claude.json"
    assert configs["codex"] == env.home / "cx" / "config.toml"


def test_writes_json_config_and_keeps_other_servers(env):
    path = _cursor(env)
    path.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}, "k": 1}))

    assert setup.main(["--yes", "--searxng-url", "http://s:8888"]) == 0

    data = json.loads(path.read_text())
    assert data["k"] == 1
    assert data["mcpServers"]["other"] == {"command": "x"}
    assert data["mcpServers"]["searxncrawl"] == {
        "command": UVX,
        "args": ["searxncrawl"],
        "env": {"SEARXNG_URL": "http://s:8888"},
    }


def test_creates_missing_file_without_backup(env):
    path = _cursor(env)

    assert setup.main(["--yes"]) == 0

    # No URL given and none in the environment: no env block is written.
    assert json.loads(path.read_text())["mcpServers"]["searxncrawl"] == {
        "command": UVX,
        "args": ["searxncrawl"],
    }
    assert _backups(path) == []


def test_vscode_uses_servers_key_with_stdio_type(env):
    user_dir = setup._app_config_dir() / "Code" / "User"
    user_dir.mkdir(parents=True)

    assert setup.main(["--yes", "--searxng-url", "http://s"]) == 0

    entry = json.loads((user_dir / "mcp.json").read_text())["servers"]["searxncrawl"]
    assert entry["type"] == "stdio"
    assert entry["command"] == UVX


def test_rerun_is_idempotent_and_updates(env):
    path = _cursor(env)
    path.write_text("{}")

    setup.main(["--yes", "--searxng-url", "http://a"])
    first = path.read_text()
    assert len(_backups(path)) == 1

    setup.main(["--yes", "--searxng-url", "http://a"])
    assert path.read_text() == first
    assert len(_backups(path)) == 1  # unchanged config: no write, no backup

    setup.main(["--yes", "--searxng-url", "http://b"])
    servers = json.loads(path.read_text())["mcpServers"]
    assert list(servers) == ["searxncrawl"]
    assert servers["searxncrawl"]["env"] == {"SEARXNG_URL": "http://b"}


def test_backup_keeps_original_content(env):
    path = _cursor(env)
    original = '{"mcpServers": {}, "note": "mine"}'
    path.write_text(original)

    setup.main(["--yes"])

    (saved,) = _backups(path)
    assert saved.read_text() == original
    assert setup.backup(path) != saved  # same-second backups never overwrite


def test_remove_drops_only_our_entry(env):
    path = _cursor(env)
    path.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
    setup.main(["--yes"])

    assert setup.main(["--yes", "--remove"]) == 0
    assert json.loads(path.read_text()) == {"mcpServers": {"other": {"command": "x"}}}

    before = len(_backups(path))
    assert setup.main(["--yes", "--remove"]) == 0  # nothing left to remove
    assert len(_backups(path)) == before


def test_unparseable_json_is_left_untouched(env):
    path = _cursor(env)
    path.write_text('{\n  // comment\n  "mcpServers": {}\n}')

    assert setup.main(["--yes"]) == 1
    assert "// comment" in path.read_text()
    assert _backups(path) == []


def test_declined_prompt_changes_nothing(env, monkeypatch):
    path = _cursor(env)
    answers = iter(["http://typed", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    assert setup.main([]) == 0
    assert not path.exists()


def test_prompt_reuses_env_url(env, monkeypatch):
    path = _cursor(env)
    monkeypatch.setenv("SEARXNG_URL", "http://from-env")
    answers = iter(["", "y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    assert setup.main([]) == 0
    entry = json.loads(path.read_text())["mcpServers"]["searxncrawl"]
    assert entry["env"] == {"SEARXNG_URL": "http://from-env"}


def test_cli_agents_use_their_own_cli(env):
    env.path.update(claude="/bin/claude", codex="/bin/codex", gemini="/bin/gemini")
    claude_json = env.home / ".claude.json"
    claude_json.write_text('{"mcpServers": {}}')

    assert setup.main(["--yes", "--searxng-url", "http://s"]) == 0

    launch = [UVX, "searxncrawl"]
    assert env.calls == [
        ["/bin/claude", "mcp", "remove", "--scope", "user", "searxncrawl"],
        ["/bin/claude", "mcp", "add", "--scope", "user", "searxncrawl",
         "-e", "SEARXNG_URL=http://s", "--", *launch],
        ["/bin/codex", "mcp", "remove", "searxncrawl"],
        ["/bin/codex", "mcp", "add", "searxncrawl",
         "--env", "SEARXNG_URL=http://s", "--", *launch],
        ["/bin/gemini", "mcp", "remove", "--scope", "user", "searxncrawl"],
        ["/bin/gemini", "mcp", "add", "--scope", "user", "searxncrawl",
         *launch, "-e", "SEARXNG_URL=http://s"],
    ]  # fmt: skip
    assert [p.read_text() for p in _backups(claude_json)] == ['{"mcpServers": {}}']


def test_cli_remove_and_agent_filter(env):
    env.path.update(claude="/bin/claude", codex="/bin/codex")

    assert setup.main(["--yes", "--remove", "--agent", "codex"]) == 0
    assert env.calls == [["/bin/codex", "mcp", "remove", "searxncrawl"]]


def test_cli_add_failure_is_reported(env):
    env.path["codex"] = "/bin/codex"
    env.rc = 1

    assert setup.main(["--yes"]) == 1


def test_mcp_server_entry_point_dispatches_setup(monkeypatch):
    seen = {}
    monkeypatch.setattr(sys, "argv", ["searxncrawl", "setup", "--yes"])
    monkeypatch.setattr(setup, "main", lambda argv: seen.setdefault("argv", argv) and 0)

    with pytest.raises(SystemExit) as exit_info:
        mcp_server.main()

    assert seen["argv"] == ["--yes"]
    assert exit_info.value.code == 0
