from __future__ import annotations

import json
from pathlib import Path


def test_webmcp_toolset_is_registered_and_direct():
    import model_tools

    tools = model_tools.get_tool_definitions(
        enabled_toolsets=["webmcp"],
        disabled_toolsets=[],
        quiet_mode=True,
        skip_tool_search_assembly=True,
    )
    names = {tool["function"]["name"] for tool in tools}
    assert {
        "webmcp_lookup",
        "webmcp_list_tools",
        "webmcp_describe_tool",
        "webmcp_call",
        "webmcp_search_sites",
    } <= names
    source = (Path(__file__).resolve().parents[2] / "tools" / "tool_search.py").read_text()
    assert '"webmcp"' in source.split("_DIRECT_SURFACE_TOOLSETS", 1)[1].split("}", 1)[0]


def test_webmcp_is_configurable_and_default_off():
    from loki_cli.tools_config import CONFIGURABLE_TOOLSETS, _DEFAULT_OFF_TOOLSETS
    from toolsets import validate_toolset

    keys = {key for key, _label, _description in CONFIGURABLE_TOOLSETS}
    assert "webmcp" in keys
    assert "webmcp" in _DEFAULT_OFF_TOOLSETS
    assert validate_toolset("webmcp") is True


def test_live_list_parses_browser_exec_marker(monkeypatch):
    from tools import browser_use_cli, webmcp_tool

    payload = {
        "success": True,
        "supported": True,
        "url": "https://shop.example/",
        "tool_count": 1,
        "tools": [{"name": "search_products"}],
    }
    monkeypatch.setattr(
        browser_use_cli,
        "browser_exec",
        lambda **kwargs: json.dumps({
            "success": True,
            "output": "noise\n" + webmcp_tool._RESULT_MARKER + json.dumps(payload) + "\n",
        }),
    )

    result = json.loads(webmcp_tool.webmcp_list_tools())
    assert result == payload


def test_call_executes_non_sensitive_live_tool(monkeypatch):
    from tools import webmcp_tool

    monkeypatch.setattr(
        webmcp_tool,
        "webmcp_describe_tool",
        lambda *args, **kwargs: json.dumps({
            "success": True,
            "url": "https://shop.example/products",
            "tool": {
                "name": "add_to_cart",
                "annotations": {"readOnlyHint": False, "consequentialHint": False},
            },
        }),
    )
    monkeypatch.setattr(webmcp_tool, "_directory_tool_kind", lambda *args, **kwargs: "act")
    calls = []
    monkeypatch.setattr(
        webmcp_tool,
        "_run_browser_expression",
        lambda expression, **kwargs: calls.append(expression) or {
            "success": True,
            "tool": "add_to_cart",
            "result": {"cart_count": 1},
        },
    )
    monkeypatch.setattr(
        webmcp_tool,
        "_request_consequential_consent",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not ask")),
    )

    result = json.loads(webmcp_tool.webmcp_call("add_to_cart", {"product_id": "sku_1"}))
    assert result["success"] is True
    assert result["directory_kind"] == "act"
    assert "add_to_cart" in calls[0]


def test_transact_tool_fails_closed_without_user_consent(monkeypatch):
    from tools import webmcp_tool

    monkeypatch.setattr(
        webmcp_tool,
        "webmcp_describe_tool",
        lambda *args, **kwargs: json.dumps({
            "success": True,
            "url": "https://shop.example/checkout",
            "tool": {"name": "checkout", "annotations": {"readOnlyHint": False}},
        }),
    )
    monkeypatch.setattr(webmcp_tool, "_directory_tool_kind", lambda *args, **kwargs: "transact")
    monkeypatch.setattr(webmcp_tool, "_request_consequential_consent", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        webmcp_tool,
        "_run_browser_expression",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not execute")),
    )

    result = json.loads(webmcp_tool.webmcp_call("checkout", {"cart_id": "cart_1"}))
    assert result["blocked"] is True
    assert result["kind"] == "transact"
    assert "did not approve" in result["error"]


def test_directory_search_bounds_limit_and_kind(monkeypatch):
    from tools import webmcp_tool

    seen = {}

    def fake_request(path, params=None):
        seen["path"] = path
        seen["params"] = params
        return {"ok": True, "sites": []}

    monkeypatch.setattr(webmcp_tool, "_directory_request", fake_request)
    result = json.loads(webmcp_tool.webmcp_search_sites("shop", tool="cart", kind="act", limit=999))
    assert result["ok"] is True
    assert seen["path"] == "/api/v1/sites"
    assert seen["params"]["limit"] == 25
    assert seen["params"]["kind"] == "act"
