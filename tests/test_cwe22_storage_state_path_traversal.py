"""Tests for CWE-22 path traversal in storage_state parameter.

Validates that resolve_auth() rejects paths outside the allowed
storage-state directory when restrict_paths=True (MCP context).
"""

from __future__ import annotations

import json
import os

import pytest

from crawler.auth import AuthConfigError, resolve_auth


class TestStorageStatePathTraversal:
    """Ensure storage_state paths are confined to the allowed directory."""

    def test_reject_absolute_path_outside_allowed_dir(self, tmp_path):
        """An absolute path outside the allowed dir must be rejected."""
        # Create a valid JSON file outside the allowed directory
        evil_file = tmp_path / "outside" / "evil.json"
        evil_file.parent.mkdir(parents=True, exist_ok=True)
        evil_file.write_text(json.dumps({"cookies": []}), encoding="utf-8")

        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        with pytest.raises(AuthConfigError, match="outside.*allowed"):
            resolve_auth(
                {"storage_state": str(evil_file)},
                restrict_paths=True,
                storage_state_dir=str(allowed_dir),
            )

    def test_reject_dotdot_traversal(self, tmp_path):
        """Paths with '..' components escaping the allowed dir must be rejected."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        # Create file that exists but is outside allowed dir via traversal
        evil_file = tmp_path / "secret.json"
        evil_file.write_text(json.dumps({"cookies": []}), encoding="utf-8")

        traversal_path = str(allowed_dir / ".." / "secret.json")

        with pytest.raises(AuthConfigError, match="outside.*allowed"):
            resolve_auth(
                {"storage_state": traversal_path},
                restrict_paths=True,
                storage_state_dir=str(allowed_dir),
            )

    def test_reject_symlink_escape(self, tmp_path):
        """Symlinks pointing outside the allowed dir must be rejected."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        external_file = tmp_path / "external.json"
        external_file.write_text(json.dumps({"cookies": []}), encoding="utf-8")

        symlink = allowed_dir / "link.json"
        symlink.symlink_to(external_file)

        with pytest.raises(AuthConfigError, match="outside.*allowed"):
            resolve_auth(
                {"storage_state": str(symlink)},
                restrict_paths=True,
                storage_state_dir=str(allowed_dir),
            )

    def test_accept_valid_path_inside_allowed_dir(self, tmp_path):
        """A valid storage_state file inside the allowed dir is accepted."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        state_file = allowed_dir / "state.json"
        state_file.write_text(
            json.dumps({"cookies": [], "origins": []}), encoding="utf-8"
        )

        result = resolve_auth(
            {"storage_state": str(state_file)},
            restrict_paths=True,
            storage_state_dir=str(allowed_dir),
        )

        assert result is not None
        assert result.storage_state == str(state_file.resolve())

    def test_accept_valid_path_in_subdirectory(self, tmp_path):
        """A storage_state file in a subdirectory of allowed dir is accepted."""
        allowed_dir = tmp_path / "allowed"
        sub_dir = allowed_dir / "profiles" / "user1"
        sub_dir.mkdir(parents=True)

        state_file = sub_dir / "state.json"
        state_file.write_text(json.dumps({"cookies": []}), encoding="utf-8")

        result = resolve_auth(
            {"storage_state": str(state_file)},
            restrict_paths=True,
            storage_state_dir=str(allowed_dir),
        )

        assert result is not None
        assert result.storage_state == str(state_file.resolve())

    def test_unrestricted_mode_allows_any_path(self, tmp_path):
        """When restrict_paths=False (CLI), any valid path is accepted."""
        state_file = tmp_path / "anywhere" / "state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"cookies": []}), encoding="utf-8")

        result = resolve_auth(
            {"storage_state": str(state_file)},
            restrict_paths=False,
        )

        assert result is not None
        assert result.storage_state == str(state_file.resolve())

    def test_default_is_unrestricted_for_backward_compat(self, tmp_path):
        """Default behavior (no restrict_paths) allows any valid path."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"cookies": []}), encoding="utf-8")

        result = resolve_auth({"storage_state": str(state_file)})

        assert result is not None
        assert result.storage_state == str(state_file.resolve())

    def test_restrict_with_no_dir_configured_rejects(self, tmp_path):
        """If restrict_paths=True but no dir given, reject with clear error."""
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"cookies": []}), encoding="utf-8")

        with pytest.raises(AuthConfigError, match="not allowed"):
            resolve_auth(
                {"storage_state": str(state_file)},
                restrict_paths=True,
                storage_state_dir=None,
            )

    @pytest.mark.asyncio
    async def test_mcp_crawl_tool_rejects_arbitrary_path(
        self, monkeypatch, tmp_path
    ):
        """The MCP crawl tool must reject storage_state outside STORAGE_STATE_DIR."""
        from crawler import mcp_server

        # Set up a confined directory
        allowed_dir = tmp_path / "states"
        allowed_dir.mkdir()
        monkeypatch.setattr(mcp_server, "STORAGE_STATE_DIR", str(allowed_dir))

        # Create a valid JSON file OUTSIDE the allowed dir
        evil_file = tmp_path / "evil.json"
        evil_file.write_text(json.dumps({"cookies": []}), encoding="utf-8")

        # The MCP tool should raise AuthConfigError before reaching the crawler
        with pytest.raises(AuthConfigError, match="outside.*allowed"):
            await mcp_server.crawl(
                urls=["https://example.com"],
                storage_state=str(evil_file),
            )

    @pytest.mark.asyncio
    async def test_mcp_crawl_site_tool_rejects_arbitrary_path(
        self, monkeypatch, tmp_path
    ):
        """crawl_site MCP tool also rejects traversal paths."""
        from crawler import mcp_server

        allowed_dir = tmp_path / "states"
        allowed_dir.mkdir()
        monkeypatch.setattr(mcp_server, "STORAGE_STATE_DIR", str(allowed_dir))

        evil_file = tmp_path / "evil.json"
        evil_file.write_text(json.dumps({"cookies": []}), encoding="utf-8")

        with pytest.raises(AuthConfigError, match="outside.*allowed"):
            await mcp_server.crawl_site(
                url="https://example.com",
                storage_state=str(evil_file),
            )

    @pytest.mark.asyncio
    async def test_mcp_crawl_tool_accepts_valid_storage_state(
        self, monkeypatch, tmp_path
    ):
        """MCP crawl tool accepts a storage_state inside STORAGE_STATE_DIR."""
        from types import SimpleNamespace

        import crawler
        from crawler import mcp_server

        # Set up a confined directory with a valid state file
        allowed_dir = tmp_path / "states"
        allowed_dir.mkdir()
        state_file = allowed_dir / "my_state.json"
        state_file.write_text(
            json.dumps({"cookies": [], "origins": []}), encoding="utf-8"
        )
        monkeypatch.setattr(mcp_server, "STORAGE_STATE_DIR", str(allowed_dir))

        captured = {}

        async def fake_crawl_page_async(
            url, *, dedup_mode="exact", auth=None, timeout=None
        ):
            captured["auth"] = auth
            return SimpleNamespace(
                request_url=url,
                final_url=url,
                status="success",
                markdown="# test",
                error_message=None,
                metadata={},
                references=[],
            )

        monkeypatch.setattr(crawler, "crawl_page_async", fake_crawl_page_async)

        await mcp_server.crawl(
            urls=["https://example.com"],
            storage_state=str(state_file),
        )

        assert captured["auth"] == {"storage_state": str(state_file)}
