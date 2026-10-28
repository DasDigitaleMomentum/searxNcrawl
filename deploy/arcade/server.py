"""Arcade worker for the published searxncrawl package."""

import json
import inspect
import os
import sys
from pathlib import Path
from typing import Annotated, get_type_hints

from arcade_mcp_server import MCPApp
from arcade_tdk import ToolContext
from docstring_parser import parse
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from crawler.mcp_server import crawl, crawl_site, search as native_search

PROVIDER_KEYS = {
    "SEARXNG_URL",
    "SEARXNG_USERNAME",
    "SEARXNG_PASSWORD",
    "SEARXNG_EXTRA_HEADERS",
    "YDC_API_KEY",
    "SEARCH_RESULT_FIELDS",
}


def provider_env(raw: str) -> dict[str, str]:
    """Validate configuration without exposing secret values in errors."""
    try:
        values = json.loads(raw)
    except (TypeError, ValueError):
        raise ValueError("Invalid Arcade search configuration") from None
    if not isinstance(values, dict) or any(
        key not in PROVIDER_KEYS or not isinstance(value, str)
        for key, value in values.items()
    ):
        raise ValueError("Invalid Arcade search configuration")
    return {key: values.get(key, "") for key in PROVIDER_KEYS}


app = MCPApp(name="Searxncrawl", version="0.33.0")


async def search(
    context: ToolContext,
    query: str,
    language: str = "en",
    time_range: str | None = None,
    categories: list[str] | None = None,
    engines: list[str] | None = None,
    safesearch: int = 1,
    pageno: int = 1,
    max_results: int = 10,
    max_retries: int = 3,
    providers: list[str] | None = None,
    include_content: bool = False,
) -> str:
    """Search SearXNG and/or You.com, optionally crawling each result page."""
    env = provider_env(context.get_secret("SEARXNCRAWL_SEARCH_CONFIG"))
    # MCP's default subprocess environment omits browser runtime settings.
    env.update({
        key: os.environ[key]
        for key in ("PLAYWRIGHT_BROWSERS_PATH", "PLAYWRIGHT_AUTO_INSTALL")
        if key in os.environ
    })
    # Each process receives only this call's provider credentials.
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "crawler.mcp_server"],
        env=env,
        keep_alive=False,
        log_file=Path(os.devnull),
    )
    async with Client(transport) as client:
        result = await client.call_tool(
            "search",
            {
                "query": query,
                "language": language,
                "time_range": time_range,
                "categories": categories,
                "engines": engines,
                "safesearch": safesearch,
                "pageno": pageno,
                "max_results": max_results,
                "max_retries": max_retries,
                "providers": providers,
                "include_content": include_content,
            },
        )
    return "\n".join(block.text for block in result.content if block.type == "text")


for function, reference in ((crawl, crawl), (crawl_site, crawl_site), (search, native_search)):
    descriptions = {
        parameter.arg_name: parameter.description
        for parameter in parse(inspect.getdoc(reference)).params
    }
    # Arcade requires evaluated Annotated types instead of postponed annotations.
    function.__annotations__ = {
        name: kind if name == "context" else Annotated[kind, descriptions[name]]
        for name, kind in get_type_hints(function).items()
        if name != "return"
    } | {"return": str}
    app.add_tool(
        function,
        name=function.__name__,
        desc=inspect.getdoc(reference),
        requires_secrets=["SEARXNCRAWL_SEARCH_CONFIG"] if function is search else None,
    )


if __name__ == "__main__":
    app.run()
