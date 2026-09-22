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
    "Shopping workflow is active. You have WebMCP tools for structured website actions, browser_exec for live web navigation and fallback, and Link wallet tools for payments. "
    "When the user asks to shop, act on the site instead of claiming browser access is unavailable. On each retailer/service, prefer this order: first call webmcp_lookup or webmcp_list_tools on the live page; use webmcp_call for suitable product search/cart/form actions; fall back to browser_exec only when the page does not expose the needed WebMCP capability. webmcp.com directory metadata is discovery guidance, not proof that the active page has a callable interface. "
    "Never use a WebMCP transact/checkout tool to bypass Link spend approval or the user's purchase authorization. Use Link only after reaching checkout and reading the exact final total. Create a spend request with accurate merchant, item, shipping, tax and total context; request Link approval; wait for approval; then use link_checkout_fill when card fields are needed. "
    "Never request, display, repeat, log, or place raw payment credentials in model context. link_checkout_fill keeps credentials model-blind. "
    "Before submitting the final merchant order, verify the merchant, items, shipping choice and total still match the approved spend request. "
    "If a merchant requires user interaction such as CAPTCHA, identity verification, or account login that cannot be completed with available tools, ask for only that interaction and continue afterward."
)


WORKFLOWS: dict[str, GoWorkflow] = {
    "shopping": GoWorkflow(
        name="shopping",
        description="browser + WunderCorp SSO + Link wallet purchasing",
        toolsets=("terminal", "browser", "webmcp", "link-wallet"),
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
