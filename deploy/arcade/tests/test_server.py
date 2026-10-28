import importlib.util
from functools import cache
import json
import os
import sys
from pathlib import Path

import pytest


@cache
def load_adapter():
    path = Path(__file__).parents[1] / "server.py"
    assert path.exists(), "Arcade deployment entrypoint is missing"
    spec = importlib.util.spec_from_file_location("arcade_adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_provider_config_is_request_local(monkeypatch):
    adapter = load_adapter()
    monkeypatch.setenv("YDC_API_KEY", "parent-secret")
    env = adapter.provider_env('{"YDC_API_KEY":"request-secret"}')
    assert env["YDC_API_KEY"] == "request-secret"
    assert env["SEARXNG_URL"] == ""
    assert os.environ["YDC_API_KEY"] == "parent-secret"
    assert "PATH" not in env
    assert adapter.provider_env("{}")["YDC_API_KEY"] == ""


@pytest.mark.parametrize(
    "config",
    [
        "secret-invalid-json",
        "null",
        "[]",
        '{"YDC_API_KEY":42}',
        '{"PATH":"secret-path"}',
        '{"SEARXNG_URL":{"secret":"value"}}',
    ],
)
def test_rejects_invalid_secret_config_without_echoing_values(config):
    adapter = load_adapter()
    with pytest.raises(ValueError) as error:
        adapter.provider_env(config)
    assert "secret" not in str(error.value)
    assert config not in str(error.value)


async def test_search_does_not_inherit_parent_credentials(monkeypatch):
    adapter = load_adapter()
    from arcade_tdk import ToolContext
    import psutil

    monkeypatch.setenv("SEARXNG_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("YDC_API_KEY", "parent-secret")
    context = ToolContext(
        secrets=[{"key": "SEARXNCRAWL_SEARCH_CONFIG", "value": "{}"}]
    )
    process = psutil.Process()
    previous_children = {child.pid for child in process.children(recursive=True)}
    result = await adapter.search(context=context, query="offline isolation check")
    payload = json.loads(result)
    assert "configured" in payload["error"].lower()
    assert "parent-secret" not in result
    assert os.environ["YDC_API_KEY"] == "parent-secret"
    assert {child.pid for child in process.children(recursive=True)} <= previous_children


async def test_mcp_exposes_native_tools_and_include_content_without_secret_inputs():
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    path = Path(__file__).parents[1] / "server.py"
    transport = StdioTransport(
        command=sys.executable,
        args=[str(path)],
        env={"SEARXNCRAWL_SEARCH_CONFIG": "{}"},
        log_file=Path(os.devnull),
    )
    async with Client(transport) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        result = await client.call_tool("Searxncrawl_Search", {"query": "offline check"})
    assert set(tools) == {
        "Searxncrawl_Crawl",
        "Searxncrawl_CrawlSite",
        "Searxncrawl_Search",
    }
    schema = tools["Searxncrawl_Search"].input_schema
    assert schema["required"] == ["query"]
    assert schema["properties"]["include_content"]["type"] == "boolean"
    assert "include_content" not in schema["required"]
    assert "providers" in schema["properties"]
    assert "context" not in schema["properties"]
    assert "SEARXNCRAWL_SEARCH_CONFIG" not in json.dumps(schema)
    text = "\n".join(block.text for block in result.content if block.type == "text")
    assert "configured" in json.loads(text)["error"].lower()
