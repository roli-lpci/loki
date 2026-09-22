from __future__ import annotations

from loki_cli.commands import resolve_command
from loki_cli.go_workflows import resolve_workflow
from loki_cli.ops_mode import OPS_TOOLSETS, build_ops_prompt, resolve_lens


def test_registry_exposes_ops_command_and_go_ops():
    ops = resolve_command("ops")
    go = resolve_command("go")
    assert ops is not None
    assert ops.cli_only is True
    assert "finance" in ops.subcommands
    assert "operations" in ops.subcommands
    assert "hiring" in ops.subcommands
    assert go is not None
    assert "ops" in go.subcommands


def test_go_shopping_requires_link_wallet_and_ops_does_not():
    shopping = resolve_workflow("shopping")
    ops = resolve_workflow("ops")
    assert shopping is not None
    assert "link-wallet" in shopping.toolsets
    assert shopping.requires_link is True
    assert ops is not None
    assert ops.toolsets == OPS_TOOLSETS
    assert "connections" in ops.toolsets
    assert "cronjob" in ops.toolsets
    assert "link-wallet" not in ops.toolsets
    assert ops.requires_link is False


def test_ops_lenses_are_industry_agnostic_but_include_vertical_adaptation():
    assert resolve_lens("accounting").name == "finance"
    assert resolve_lens("efficiency").name == "operations"
    assert resolve_lens("hr").name == "people"
    assert resolve_lens("recruiting").name == "hiring"
    prompt = build_ops_prompt(
        lens="operations",
        business_context="Single-site gas station and convenience store in Virginia.",
    )
    assert "[LOKI_OPS]" in prompt
    assert "[LOKI_OPS_LENS:operations]" in prompt
    assert "gas station and convenience store" in prompt
    assert "fuel margin per gallon" in prompt
    assert "Never invent business data" in prompt


def test_ops_setup_persists_business_context(monkeypatch):
    import loki_cli.config as config_module
    import loki_cli.cli_commands_mixin as commands_mixin
    from loki_cli.cli_commands_mixin import CLICommandsMixin

    config = {"ops": {"business_context": "", "default_lens": "overview"}}
    saved = {}
    outputs = []

    monkeypatch.setattr(config_module, "load_config", lambda: config)
    monkeypatch.setattr(config_module, "save_config", lambda value: saved.update(value))
    monkeypatch.setattr(commands_mixin, "_cp", lambda *lines: outputs.append(lines))

    stub = object.__new__(CLICommandsMixin)
    CLICommandsMixin._handle_ops_command(
        stub,
        "/ops setup Single-site gas station; 8 employees; fuel and c-store revenue",
    )

    assert saved["ops"]["business_context"].startswith("Single-site gas station")
    assert any("profile saved" in line for call in outputs for line in call)


def test_ops_finance_activates_existing_toolsets_and_fresh_prompt(monkeypatch):
    import loki_cli.config as config_module
    import loki_cli.tools_config as tools_config
    import loki_cli.cli_commands_mixin as commands_mixin
    from loki_cli.cli_commands_mixin import CLICommandsMixin

    config = {
        "platform_toolsets": {"cli": []},
        "agent": {},
        "browser": {},
        "ops": {
            "business_context": "Neighborhood service business with 12 employees.",
            "default_lens": "overview",
        },
    }
    saved = {}
    outputs = []

    class Agent:
        ephemeral_system_prompt = "existing transient context"

        def _invalidate_system_prompt(self):
            return None

    class Stub:
        def __init__(self):
            self.agent = Agent()
            self.enabled_toolsets = []
            self.disabled_toolsets = []
            self._app = True
            self.mutations = []
            self.reset_count = 0

        def _run_tools_config(self, **kwargs):
            self.mutations.append(kwargs)
            for name in kwargs["names"]:
                if name not in config["platform_toolsets"]["cli"]:
                    config["platform_toolsets"]["cli"].append(name)

        def new_session(self):
            self.reset_count += 1

    monkeypatch.setattr(config_module, "load_config", lambda: config)
    monkeypatch.setattr(config_module, "save_config", lambda value: saved.update(value))
    monkeypatch.setattr(
        tools_config,
        "_get_platform_tools",
        lambda cfg, platform, **kwargs: set(cfg.get("platform_toolsets", {}).get(platform, [])),
    )
    monkeypatch.setattr(commands_mixin, "_refresh_cli_toolsets", lambda cli: None)
    monkeypatch.setattr(commands_mixin, "_cp", lambda *lines: outputs.append(lines))
    monkeypatch.setattr("tools.registry.invalidate_check_fn_cache", lambda: None)

    stub = Stub()
    CLICommandsMixin._handle_ops_command(stub, "/ops finance")

    assert stub.mutations == [{
        "tools_action": "enable",
        "names": list(OPS_TOOLSETS),
        "platform": "cli",
    }]
    assert stub.reset_count == 1
    assert stub._go_mode == "ops"
    assert stub._ops_lens == "finance"
    assert saved["browser"]["backend"] == "browser-use"
    assert "[LOKI_OPS]" in stub.agent.ephemeral_system_prompt
    assert "[LOKI_OPS_LENS:finance]" in stub.agent.ephemeral_system_prompt
    assert "Neighborhood service business" in stub.agent.ephemeral_system_prompt
    assert any("Ops lens: finance" in line for call in outputs for line in call)
