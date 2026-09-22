from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoWorkflow:
    name: str
    description: str
    toolsets: tuple[str, ...]
    ephemeral_prompt: str
    browser_backend: str | None = None
    requires_link: bool = False
    aliases: tuple[str, ...] = ()


SHOPPING_PROMPT = (
    "[LOKI_GO_SHOPPING]\n"
    "Shopping workflow is active. You have browser_exec for live web navigation and Link wallet tools for payments. "
    "When the user asks to shop, browse the site instead of claiming browser access is unavailable. "
    "Use Link only after reaching checkout and reading the exact final total. Create a spend request with accurate merchant, item, shipping, tax and total context; request Link approval; wait for approval; then use link_checkout_fill to inject the approved one-time card into the active checkout. "
    "Never request, display, repeat, log, or place raw payment credentials in model context. link_checkout_fill keeps credentials model-blind. "
    "Before submitting the final merchant order, verify the merchant, items, shipping choice and total still match the approved spend request. "
    "If a merchant requires user interaction such as CAPTCHA, identity verification, or account login that cannot be completed with available tools, ask for only that interaction and continue afterward."
)


WORKFLOWS: dict[str, GoWorkflow] = {
    "shopping": GoWorkflow(
        name="shopping",
        description="browser + WunderCorp SSO + Link wallet purchasing",
        toolsets=("terminal", "browser", "link-wallet"),
        browser_backend="browser-use",
        requires_link=True,
        ephemeral_prompt=SHOPPING_PROMPT,
        aliases=("shop",),
    ),
}


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
