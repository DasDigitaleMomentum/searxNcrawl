"""Tests for the auth configuration module."""

from __future__ import annotations

import json
import os
import tempfile
from unittest import mock

import pytest

from crawler.auth import (
    AuthConfig,
    build_browser_config,
    load_auth_from_env,
    load_auth_from_file,
)


class TestAuthConfig:
    """Tests for the AuthConfig dataclass."""

    def test_empty_config(self):
        auth = AuthConfig()
        assert auth.is_empty is True

    def test_cookies_not_empty(self):
        auth = AuthConfig(
            cookies=[{"name": "sid", "value": "abc", "domain": ".example.com"}]
        )
        assert auth.is_empty is False

    def test_headers_not_empty(self):
        auth = AuthConfig(headers={"Authorization": "Bearer xyz"})
        assert auth.is_empty is False

    def test_storage_state_not_empty(self):
        auth = AuthConfig(storage_state="./state.json")
        assert auth.is_empty is False

    def test_user_data_dir_enables_persistent_context(self):
        auth = AuthConfig(user_data_dir="/tmp/profile")
        assert auth.use_persistent_context is True

    def test_resolved_storage_state_from_data(self):
        state = {"cookies": [], "origins": []}
        auth = AuthConfig(storage_state_data=state)
        assert auth.resolved_storage_state() == state

    def test_resolved_storage_state_from_file(self):
        state = {"cookies": [{"name": "a", "value": "b"}], "origins": []}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fh:
            json.dump(state, fh)
            fh.flush()
            path = fh.name

        try:
            auth = AuthConfig(storage_state=path)
            result = auth.resolved_storage_state()
            assert result == state
        finally:
            os.unlink(path)

    def test_resolved_storage_state_file_not_found(self):
        auth = AuthConfig(storage_state="/nonexistent/path.json")
        with pytest.raises(FileNotFoundError):
            auth.resolved_storage_state()

    def test_resolved_storage_state_none(self):
        auth = AuthConfig()
        assert auth.resolved_storage_state() is None


class TestBuildBrowserConfig:
    """Tests for the build_browser_config function."""

    def test_none_auth_returns_default(self):
        cfg = build_browser_config(None)
        assert cfg.use_persistent_context is False

    def test_empty_auth_returns_default(self):
        cfg = build_browser_config(AuthConfig())
        assert cfg.use_persistent_context is False

    def test_cookies_passed_through(self):
        cookies = [{"name": "sid", "value": "abc", "domain": ".example.com"}]
        auth = AuthConfig(cookies=cookies)
        cfg = build_browser_config(auth)
        assert cfg.cookies == cookies

    def test_headers_passed_through(self):
        headers = {"Authorization": "Bearer xyz"}
        auth = AuthConfig(headers=headers)
        cfg = build_browser_config(auth)
        assert cfg.headers == headers

    def test_user_data_dir_enables_persistent(self):
        auth = AuthConfig(user_data_dir="/tmp/test-profile")
        cfg = build_browser_config(auth)
        assert cfg.use_persistent_context is True
        assert cfg.user_data_dir == "/tmp/test-profile"


class TestLoadAuthFromEnv:
    """Tests for loading auth from environment variables."""

    def test_no_env_vars_returns_none(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            result = load_auth_from_env()
            assert result is None

    def test_storage_state_env(self):
        with mock.patch.dict(
            os.environ, {"CRAWL_AUTH_STORAGE_STATE": "/path/to/state.json"}
        ):
            result = load_auth_from_env()
            assert result is not None
            assert result.storage_state == "/path/to/state.json"

    def test_profile_env(self):
        with mock.patch.dict(
            os.environ, {"CRAWL_AUTH_PROFILE": "/path/to/profile"}
        ):
            result = load_auth_from_env()
            assert result is not None
            assert result.user_data_dir == "/path/to/profile"

    def test_cookies_file_env(self):
        cookies = [{"name": "a", "value": "b", "domain": ".test.com"}]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fh:
            json.dump(cookies, fh)
            fh.flush()
            path = fh.name

        try:
            with mock.patch.dict(
                os.environ, {"CRAWL_AUTH_COOKIES_FILE": path}
            ):
                result = load_auth_from_env()
                assert result is not None
                assert result.cookies == cookies
        finally:
            os.unlink(path)


class TestLoadAuthFromFile:
    """Tests for loading auth from a config file."""

    def test_load_full_config(self):
        config = {
            "cookies": [{"name": "sid", "value": "abc", "domain": ".ex.com"}],
            "headers": {"X-Custom": "value"},
            "storage_state": "/path/to/state.json",
            "user_data_dir": "/path/to/profile",
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fh:
            json.dump(config, fh)
            fh.flush()
            path = fh.name

        try:
            result = load_auth_from_file(path)
            assert result.cookies == config["cookies"]
            assert result.headers == config["headers"]
            assert result.storage_state == config["storage_state"]
            assert result.user_data_dir == config["user_data_dir"]
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_auth_from_file("/nonexistent/config.json")
