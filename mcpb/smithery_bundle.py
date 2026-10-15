# /// script
# requires-python = ">=3.10"
# dependencies = ["fastmcp>=4.1.0"]
# ///
"""Build the Smithery variant of the MCPB bundle.

Smithery's CLI accepts only python, node, bun or binary bundles and rejects a
release unless every tool carries its inputSchema, which the MCPB manifest
schema does not allow. This script turns mcpb/ into a "python" bundle that
runs `uvx searxncrawl==<version>` and copies the tool list, with schemas, from
the published server. `mcpb pack` would reject the extra keys, so it zips the
files directly.

    uv run mcpb/smithery_bundle.py searxncrawl-<version>-smithery.mcpb
"""

import asyncio
import json
import sys
import tempfile
import zipfile
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

MCPB_DIR = Path(__file__).resolve().parent
FILES = ["pyproject.toml", "icon.png", "src/server.py"]


async def published_tools(version: str) -> list[dict]:
    log = Path(tempfile.gettempdir()) / "searxncrawl-smithery-bundle.log"
    transport = StdioTransport(
        command="uvx", args=[f"searxncrawl=={version}"], env={}, log_file=log
    )
    async with Client(transport) as client:
        return [
            {"name": t.name, "description": t.description, "inputSchema": t.input_schema}
            for t in await client.list_tools()
        ]


def main(out: str) -> None:
    manifest = json.loads((MCPB_DIR / "manifest.json").read_text())
    version = manifest["version"]
    manifest["server"]["type"] = "python"
    manifest["server"]["mcp_config"] = {
        "command": "uvx",
        "args": [f"searxncrawl=={version}"],
        "env": manifest["server"]["mcp_config"]["env"],
    }
    manifest["tools"] = asyncio.run(published_tools(version))
    assert {t["name"] for t in manifest["tools"]} == {"crawl", "crawl_site", "search"}

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        for name in FILES:
            bundle.write(MCPB_DIR / name, name)
    print(f"wrote {out} ({version}, {len(manifest['tools'])} tools)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "searxncrawl-smithery.mcpb")
