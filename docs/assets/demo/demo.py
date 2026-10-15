# /// script
# requires-python = ">=3.10"
# dependencies = ["fastmcp>=3.4.3"]
# ///
"""Record-ready MCP client session: search, then crawl the top hit.

Starts `uvx searxncrawl` over STDIO, as an MCP client in an agent does, and prints the
real tool results. Long Markdown is cut for display; the cut is labelled.
Server logs go to searxncrawl-demo.log in the temp directory.

    SEARXNG_URL=http://localhost:8888 uv run docs/assets/demo/demo.py "crawl4ai quick start"
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

DIM, BOLD, CYAN, GREEN, RESET = "\033[2m", "\033[1m", "\033[36m", "\033[32m", "\033[0m"
SHOW_LINES = 16


def step(text: str) -> None:
    print(f"\n{CYAN}●{RESET} {BOLD}{text}{RESET}", flush=True)


async def main(query: str) -> None:
    env = {"SEARXNG_URL": os.environ.get("SEARXNG_URL", "http://localhost:8888")}
    # Server logs go to a file so the terminal shows only the MCP exchange.
    log = Path(tempfile.gettempdir()) / "searxncrawl-demo.log"
    transport = StdioTransport(command="uvx", args=["searxncrawl"], env=env, log_file=log)
    async with Client(transport) as client:
        tools = sorted(t.name for t in await client.list_tools())
        step("connected to uvx searxncrawl over MCP (STDIO)")
        print(f"  {DIM}tools: {', '.join(tools)}{RESET}")

        step(f'search(query="{query}", max_results=3)')
        result = await client.call_tool("search", {"query": query, "max_results": 3})
        hits = json.loads(result.content[0].text)["results"]
        for i, hit in enumerate(hits, 1):
            print(f"  {i}. {hit['title']}\n     {DIM}{hit['url']}{RESET}")

        url = hits[0]["url"]
        step(f'crawl(urls=["{url}"])')
        result = await client.call_tool("crawl", {"urls": [url]})
        lines = result.content[0].text.splitlines()
        for line in lines[:SHOW_LINES]:
            print(f"  {GREEN}{line}{RESET}")
        rest = len(lines) - SHOW_LINES
        if rest > 0:
            size = len(result.content[0].text.encode()) / 1000
            print(f"  {DIM}… {rest} more lines, {size:.1f} kB of Markdown in total{RESET}")


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "crawl4ai quick start"))
