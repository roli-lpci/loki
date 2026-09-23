from loki_cli.config_defaults import DEFAULT_CONFIG
from loki_cli.go_workflows import resolve_workflow


def test_guardian_search_mcp_is_first_party_default():
    server = DEFAULT_CONFIG["mcp_servers"]["guardian_search"]
    assert server["enabled"] is True
    assert server["url"] == "https://mcp.guardianbrowser.sh/v1"
    assert set(server["tools"]["include"]) >= {"search_web", "search_shopping", "discover_sites"}


def test_shopping_workflow_prefers_guardian_search_and_blocks_browser_search_engines():
    workflow = resolve_workflow("shopping")
    assert workflow is not None
    assert "guardian_search" in workflow.toolsets
    assert "web" in workflow.toolsets
    assert "mcp__guardian_search__search_shopping" not in workflow.required_runtime_tools
    prompt = workflow.ephemeral_prompt
    assert "Guardian Search MCP is the primary discovery layer" in prompt
    assert "Do not use browser_exec to browse Google, Bing, DuckDuckGo" in prompt
    assert "webmcp_search_sites searches the WebMCP capability directory" in prompt


def test_guardian_toolset_exists_before_remote_discovery():
    from toolsets import get_toolset
    from loki_cli.tools_config import CONFIGURABLE_TOOLSETS

    toolset = get_toolset("guardian_search", include_registry=False)
    assert toolset is not None
    assert toolset["tools"] == []
    assert "guardian_search" in [item[0] for item in CONFIGURABLE_TOOLSETS]


def test_shopping_keeps_web_fallback_when_guardian_is_unavailable():
    workflow = resolve_workflow("shopping")
    assert "web" in workflow.toolsets
    assert "webmcp" in workflow.toolsets
    assert "web_search" not in workflow.required_runtime_tools
    assert not any(name.startswith("mcp__guardian_search__") for name in workflow.required_runtime_tools)
    assert "If Guardian Search MCP is unavailable" in workflow.ephemeral_prompt
