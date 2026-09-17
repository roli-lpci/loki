"""Interactive TypeSafe Jev setup.

Jev is a structured decision companion.  It also powers Loki Autorouter, Loki's
session-sticky model router, but routing is always an explicit opt-in because the first
user task is sent to TypeSafe for classification.
"""

from __future__ import annotations


def _configure_jev_auto(config: dict) -> None:
    from loki_cli import setup as _setup

    current = config.get("smart_model_routing")
    routing = dict(current) if isinstance(current, dict) else {}
    enabled = bool(routing.get("enabled", False)) and str(routing.get("mode") or "jev_auto") == "jev_auto"
    _setup._info(
        None,
        "Loki Autorouter, powered by Jev, can route the first task of each new session to a lower-cost capable model",
        "from your CURRENT gateway's model catalog. It never switches gateways and keeps the",
        "selected model sticky for the session to preserve prompt caching.",
        "Enabling it sends only that first task plus bounded model metadata to TypeSafe;",
        "conversation history and provider credentials are not sent.",
        None,
    )
    choice = _setup.prompt_choice(
        "Loki Autorouter (powered by Jev)",
        [
            "Keep manual model selection (recommended until you opt in)",
            "Enable Loki Autorouter for new sessions",
        ],
        1 if enabled else 0,
    )
    routing.update({"mode": "jev_auto", "enabled": choice == 1})
    config["smart_model_routing"] = routing
    if choice == 1:
        _setup.print_success("Loki Autorouter enabled — routing stays within your selected gateway.")
    else:
        _setup.print_success("Loki Autorouter disabled — Loki will keep your selected model.")


def setup_typesafe_jev(config: dict) -> None:
    """Configure ``TYPESAFE_API_KEY`` and optional Loki Autorouter model routing."""
    from loki_cli import setup as _setup
    from loki_cli.config import OPTIONAL_ENV_VARS, redact_key

    meta = dict(OPTIONAL_ENV_VARS["TYPESAFE_API_KEY"])
    meta["name"] = "TYPESAFE_API_KEY"

    _setup.print_header("TypeSafe Jev")
    _setup._info(
        "Jev is TypeSafe's System One decision model: it returns typed judgments and",
        "probabilities (Choice, Score, Noul) instead of generating chat text.",
        "Loki keeps your normal chat model and exposes Jev as the `typesafe_ask` tool.",
        "Loki Autorouter can optionally use the same Jev key to route new sessions within your current gateway.",
        "Docs: https://docs.typesafe.ai/introduction",
        "Get/manage your key: https://console.typesafe.ai",
        None,
    )

    current = str(_setup.get_env_value("TYPESAFE_API_KEY") or "").strip()
    if current:
        _setup.print_success(f"TypeSafe key configured: {redact_key(current)}")
        action = _setup.prompt_choice(
            "TypeSafe Jev key",
            ["Keep current key", "Replace key", "Remove key"],
            0,
        )
        if action == 2:
            _setup.remove_env_value("TYPESAFE_API_KEY")
            routing = config.setdefault("smart_model_routing", {})
            if isinstance(routing, dict):
                routing["enabled"] = False
                routing.setdefault("mode", "jev_auto")
            _setup.print_success("Removed TYPESAFE_API_KEY and disabled Loki Autorouter.")
            return
        if action == 1:
            _setup._prompt_api_key(meta)
    else:
        _setup._prompt_api_key(meta)

    # Re-read after save so a skipped/blank prompt does not offer a router that cannot run.
    if str(_setup.get_env_value("TYPESAFE_API_KEY") or "").strip():
        _configure_jev_auto(config)
