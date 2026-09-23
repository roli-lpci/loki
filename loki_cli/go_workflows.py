from __future__ import annotations

from dataclasses import dataclass

from loki_cli.ops_mode import OPS_TOOLSETS, build_ops_prompt


@dataclass(frozen=True)
class GoWorkflow:
    name: str
    description: str
    toolsets: tuple[str, ...]
    ephemeral_prompt: str
    browser_backend: str | None = None
    requires_link: bool = False
    aliases: tuple[str, ...] = ()
    required_runtime_tools: tuple[str, ...] = ()


SHOPPING_PROMPT = (
    "[LOKI_GO_SHOPPING]\n"
    "Shopping workflow is active. Guardian Search MCP is the primary discovery layer, WebMCP is the primary structured merchant interaction layer, browser_exec is an interaction fallback, and Link wallet tools handle approved payment. "
    "DISCOVERY ORDER: If the user names a merchant, do not search the web for alternatives; probe that merchant with webmcp_lookup(url=...) first. If the merchant is not named, call mcp__guardian_search__search_shopping first. Use mcp__guardian_search__discover_sites only when you need destination websites rather than products. Make at most two Guardian discovery calls before choosing a viable merchant or asking one concise question. "
    "webmcp_search_sites searches the WebMCP capability directory; it is NOT a product search engine. Never call it repeatedly with product keywords such as 'paper towels'. Once a candidate merchant is known, use webmcp_lookup(url=...) to inspect directory metadata without opening a browser, then open only the selected merchant when live page tools are needed. "
    "If Guardian Search MCP is unavailable or returns no useful result, use the normal web_search tool (DuckDuckGo/keyless search when configured) as the next discovery fallback. Do not use browser_exec to browse Google, Bing, DuckDuckGo, Yahoo, or other search-result pages. Browser automation is reserved for a known destination merchant or service. "
    "INTERACTION ORDER: On a selected site, prefer live WebMCP tools via webmcp_list_tools/webmcp_call. Use browser_exec only for capabilities the page does not expose through WebMCP. If a CAPTCHA, login, identity check, or other human gate appears, preserve the current browser session, report the exact URL, and ask for only the required human interaction before resuming. "
    "Never use a WebMCP transact/checkout tool to bypass Link spend approval or the user's purchase authorization. Use Link only after reaching checkout and reading the exact final total. Create a spend request with accurate merchant, item, shipping, tax and total context; request Link approval; wait for approval; then use link_checkout_fill when card fields are needed. "
    "Never request, display, repeat, log, or place raw payment credentials in model context. link_checkout_fill keeps credentials model-blind. Before submitting the final merchant order, verify merchant, items, shipping choice and total still match the approved spend request."
)


WORKFLOWS: dict[str, GoWorkflow] = {
    "shopping": GoWorkflow(
        name="shopping",
        description="Guardian Search MCP + WebMCP + browser fallback + Link wallet purchasing",
        toolsets=("terminal", "web", "browser", "webmcp", "guardian_search", "link-wallet"),
        browser_backend="browser-use",
        requires_link=True,
        required_runtime_tools=(
            "browser_exec",
            "webmcp_lookup",
            "webmcp_list_tools",
            "webmcp_call",
            "link_wallet_status",
            "link_spend_create",
            "link_spend_request_approval",
            "link_spend_wait",
            "link_checkout_fill",
        ),
        ephemeral_prompt=SHOPPING_PROMPT,
        aliases=("shop",),
    ),
    "ops": GoWorkflow(
        name="ops",
        description="business operations, metrics, systems, and execution",
        toolsets=OPS_TOOLSETS,
        browser_backend="browser-use",
        requires_link=False,
        ephemeral_prompt=build_ops_prompt(),
        aliases=("business",),
    ),
}


_WORKFLOW_MARKERS = ("[LOKI_GO_", "[LOKI_OPS]")


def strip_workflow_prompt(value: str | None) -> str:
    text = str(value or "").rstrip()
    indexes = [index for marker in _WORKFLOW_MARKERS if (index := text.find(marker)) >= 0]
    if indexes:
        text = text[:min(indexes)].rstrip()
    return text


def apply_workflow_prompt(agent, prompt: str) -> None:
    base = strip_workflow_prompt(getattr(agent, "ephemeral_system_prompt", None))
    agent.ephemeral_system_prompt = (base + "\n\n" + prompt).strip() if base else prompt.strip()
    if hasattr(agent, "_invalidate_system_prompt"):
        agent._invalidate_system_prompt()


def resolve_workflow(name: str) -> GoWorkflow | None:
    normalized = str(name or "").strip().lower()
    if normalized in WORKFLOWS:
        return WORKFLOWS[normalized]
    for workflow in WORKFLOWS.values():
        if normalized in workflow.aliases:
            return workflow
    return None


def workflow_lines() -> list[str]:
    return [f"  {workflow.name:<10} — {workflow.description}" for workflow in WORKFLOWS.values()]
