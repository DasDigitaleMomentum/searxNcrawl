"""PyPI, the MCP Registry and the MCPB bundle name the same project website."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = "https://www.searxncrawl.io/"


def test_every_package_names_the_project_website() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    server = json.loads((ROOT / "server.json").read_text())
    bundle = json.loads((ROOT / "mcpb" / "manifest.json").read_text())

    assert project["urls"]["Homepage"] == WEBSITE
    assert server["websiteUrl"] == WEBSITE
    assert bundle["homepage"] == WEBSITE
