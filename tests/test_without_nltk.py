"""searxNcrawl must work without nltk, which pyproject.toml excludes (GHSA-8mgp-746c-j5xp)."""

import subprocess
import sys

# Setting sys.modules["nltk"] = None makes every `import nltk` raise ImportError,
# so this holds even where nltk is installed (pip installs pull it in via crawl4ai).
SCRIPT = """
import sys
sys.modules["nltk"] = None
import crawler
from crawler import build_markdown_run_config
from crawler.mcp_server import mcp
build_markdown_run_config()
print("ok")
"""


def test_crawler_imports_and_builds_config_without_nltk():
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("ok")
