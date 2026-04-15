"""Tests for the shared env/config loading module (crawler.env)."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from crawler import env


class TestLoadConfigSearchOrder:
    """load_config should prefer CWD .env, then ~/.config/searxncrawl/.env."""

    def test_loads_cwd_env_when_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CWD .env should be loaded first, even if config-dir .env also exists."""
        cwd_env = tmp_path / "cwd" / ".env"
        cwd_env.parent.mkdir()
        cwd_env.write_text("SEARXNG_URL=http://from-cwd:9999\n")

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_env = config_dir / ".env"
        config_env.write_text("SEARXNG_URL=http://from-config:8888\n")

        monkeypatch.chdir(cwd_env.parent)
        monkeypatch.setattr(env, "CONFIG_ENV_FILE", config_env)

        # Clear any existing value so load_dotenv can set it
        monkeypatch.delenv("SEARXNG_URL", raising=False)
        env.load_config()

        assert os.environ["SEARXNG_URL"] == "http://from-cwd:9999"

    def test_falls_back_to_config_dir_when_no_cwd_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When CWD has no .env, ~/.config/searxncrawl/.env should be used."""
        # CWD without .env
        empty_cwd = tmp_path / "empty"
        empty_cwd.mkdir()

        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_env = config_dir / ".env"
        config_env.write_text("SEARXNG_URL=http://from-config:8888\n")

        monkeypatch.chdir(empty_cwd)
        monkeypatch.setattr(env, "CONFIG_ENV_FILE", config_env)
        monkeypatch.delenv("SEARXNG_URL", raising=False)

        env.load_config()

        assert os.environ["SEARXNG_URL"] == "http://from-config:8888"

    def test_auto_creates_config_from_env_example(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When no .env exists anywhere, .env.example should be copied to config dir."""
        empty_cwd = tmp_path / "empty"
        empty_cwd.mkdir()

        # Simulate package dir with .env.example
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / ".env.example").write_text("SEARXNG_URL=http://default:8888\n")

        config_dir = tmp_path / "config"
        config_env = config_dir / ".env"

        monkeypatch.chdir(empty_cwd)
        monkeypatch.setattr(env, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(env, "CONFIG_ENV_FILE", config_env)
        monkeypatch.delenv("SEARXNG_URL", raising=False)

        # Patch Path(__file__).parent.parent to point to our fake package_dir
        with patch.object(env, "load_config", wraps=env.load_config):
            # We need to patch the package_dir lookup inside load_config.
            # The function uses Path(__file__).parent.parent — we can't easily
            # patch that, so instead create the .env.example relative to the
            # actual package dir.
            actual_package_dir = Path(env.__file__).parent.parent
            example_file = actual_package_dir / ".env.example"
            example_existed = example_file.exists()
            if not example_existed:
                example_file.write_text("SEARXNG_URL=http://default:8888\n")

            try:
                env.load_config()
                assert config_env.is_file(), "Config .env should have been auto-created"
            finally:
                if not example_existed and example_file.exists():
                    example_file.unlink()

    def test_no_env_anywhere_still_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_config should not raise even if no .env files exist at all."""
        empty_cwd = tmp_path / "empty"
        empty_cwd.mkdir()

        config_env = tmp_path / "nonexistent" / ".env"

        monkeypatch.chdir(empty_cwd)
        monkeypatch.setattr(env, "CONFIG_ENV_FILE", config_env)
        monkeypatch.setattr(env, "CONFIG_DIR", tmp_path / "nonexistent")

        # Ensure no .env.example in actual package dir
        actual_example = Path(env.__file__).parent.parent / ".env.example"
        example_existed = actual_example.exists()
        if example_existed:
            actual_example.rename(actual_example.with_suffix(".bak"))

        try:
            # Should not raise
            env.load_config()
        finally:
            if example_existed:
                actual_example.with_suffix(".bak").rename(actual_example)


class TestMcpServerUsesSharedConfig:
    """Verify that mcp_server imports and uses the shared env loader."""

    def test_mcp_server_imports_load_config(self) -> None:
        """mcp_server.py should import load_config from crawler.env."""
        source = Path(__file__).parent.parent / "crawler" / "mcp_server.py"
        text = source.read_text()
        assert "from .env import load_config" in text
        assert "load_config()" in text

    def test_cli_imports_load_config(self) -> None:
        """cli.py should import load_config from crawler.env."""
        source = Path(__file__).parent.parent / "crawler" / "cli.py"
        text = source.read_text()
        assert "from .env import load_config" in text
        assert "load_config()" in text

    def test_mcp_server_does_not_use_bare_load_dotenv(self) -> None:
        """mcp_server.py should NOT call load_dotenv() directly anymore."""
        source = Path(__file__).parent.parent / "crawler" / "mcp_server.py"
        text = source.read_text()
        # Should not have a bare load_dotenv() call (the import may still exist
        # transitively, but the direct call should be gone)
        lines = text.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped == "load_dotenv()" or stripped == "load_dotenv()  ":
                pytest.fail(f"Found bare load_dotenv() in mcp_server.py: {line!r}")
