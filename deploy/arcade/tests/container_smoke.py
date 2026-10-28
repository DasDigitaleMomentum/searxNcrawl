"""Run inside the built image; use real MCP processes and Chromium offline."""

import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import threading

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


class Page(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.send_response(200)
        if self.path.startswith("/search?"):
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"results": [{
                "title": "Local browser fixture",
                "url": f"http://127.0.0.1:{self.server.server_port}/",
                "content": "A local page with content rendered by Chromium.",
            }]}).encode())
            return
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Container browser check</h1><main id='content'></main>"
            b"<script>document.getElementById('content').textContent="
            b"'Rendered by Chromium';</script><p>"
            b"This local documentation page verifies the packaged crawler in its real runtime. "
            b"The browser must render JavaScript before the MCP tool returns Markdown. "
            b"Both single-page and site crawling read the same deterministic document. "
            b"The fixture contains enough visible text to represent an ordinary content page "
            b"and pass the crawler's protection against empty or blocked responses. "
            b"No external website, search provider, credential or cloud connection is needed."
            b"</p></body></html>"
        )


async def check(url):
    transport = StdioTransport(
        command=sys.executable,
        args=["server.py"],
        env={
            "SEARXNCRAWL_SEARCH_CONFIG": json.dumps({"SEARXNG_URL": url}),
            "PLAYWRIGHT_BROWSERS_PATH": os.environ["PLAYWRIGHT_BROWSERS_PATH"],
            "PLAYWRIGHT_AUTO_INSTALL": "false",
        },
        keep_alive=False,
        log_file=Path(os.devnull),
    )
    async with Client(transport, timeout=90) as client:
        assert {tool.name for tool in await client.list_tools()} == {
            "Searxncrawl_Crawl", "Searxncrawl_CrawlSite", "Searxncrawl_Search"
        }
        for tool, arguments in (
            ("Searxncrawl_Crawl", {"urls": [url]}),
            ("Searxncrawl_CrawlSite", {"url": url, "max_depth": 0, "max_pages": 1}),
        ):
            result = await client.call_tool(tool, arguments)
            assert not result.is_error
            text = "\n".join(block.text for block in result.content if block.type == "text")
            assert "Rendered by Chromium" in text, text
            print(f"PASS {tool}: real Chromium rendered JavaScript", flush=True)
        result = await client.call_tool("Searxncrawl_Search", {
            "query": "browser fixture", "providers": ["searxng"],
            "max_results": 1, "include_content": True,
        })
        assert not result.is_error
        text = "\n".join(block.text for block in result.content if block.type == "text")
        payload = json.loads(text)
        assert "Rendered by Chromium" in payload["results"][0].get("markdown", ""), text
        print("PASS Searxncrawl_Search: include_content used bundled Chromium", flush=True)


if __name__ == "__main__":
    assert os.getuid() != 0, "Container must run as a non-root user"
    assert version("searxncrawl") == "0.33.0"
    assert not Path(".env").exists(), "Credentials must not be copied into the image"
    with ThreadingHTTPServer(("127.0.0.1", 0), Page) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            asyncio.run(check(f"http://127.0.0.1:{server.server_port}/"))
        finally:
            server.shutdown()
            thread.join()
