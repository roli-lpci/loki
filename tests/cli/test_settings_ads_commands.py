"""Regression coverage for the in-session /settings hub and /ads consent command."""

from queue import Queue
from types import SimpleNamespace
from unittest.mock import patch

from cli import LokiCLI
from loki_cli.commands import resolve_command


def _bare_cli():
    cli = LokiCLI.__new__(LokiCLI)
    cli._app = None
    return cli


def test_settings_and_ads_are_cli_only_registry_commands():
    settings = resolve_command("settings")
    jev = resolve_command("jev")
    ads = resolve_command("ads")
    assert settings is not None and settings.cli_only is True
    assert jev is not None and jev.cli_only is True
    assert tuple(jev.subcommands) == ("status", "enable", "disable", "setup", "on", "off")
    assert ads is not None and ads.cli_only is True
    assert tuple(ads.subcommands) == ("on", "off", "status")
    assert LokiCLI._slash_handler("settings")[0] == "_handle_settings_command"
    assert LokiCLI._slash_handler("jev")[0] == "_handle_jev_command"
    assert LokiCLI._slash_handler("ads")[0] == "_handle_ads_command"


def test_settings_opens_native_palette_with_optional_filter():
    cli = _bare_cli()
    cli._app = SimpleNamespace()
    cli._open_settings_palette = lambda initial_filter="": setattr(cli, "opened_filter", initial_filter)

    cli._handle_settings_command("/settings tools")

    assert cli.opened_filter == "tools"


def test_settings_palette_contains_tools_and_ads():
    cli = _bare_cli()
    commands = [row[0] for row in cli._build_settings_palette_entries()]
    assert "/model" in commands
    assert "/tools list" in commands
    assert "/skills" in commands
    assert "/jev status" in commands
    assert "/ads status" in commands


def test_settings_palette_selection_queues_command_instead_of_nested_prompt():
    cli = _bare_cli()
    cli._pending_input = Queue()
    cli._command_palette_state = {
        "entries": [("/tools list", "Settings", "Tools")],
        "filter": "",
        "selected": 0,
        "_scroll_offset": 0,
        "execute_selection": True,
    }
    buffer = SimpleNamespace(text="something", cursor_position=9, reset=lambda: setattr(buffer, "text", ""))
    cli._app = SimpleNamespace(current_buffer=buffer)
    cli._restore_modal_input_snapshot = lambda: None
    cli._invalidate = lambda **kwargs: None

    cli._handle_command_palette_selection()

    assert cli._pending_input.get_nowait() == "/tools list"
    assert cli._command_palette_state is None


def test_ads_on_records_consent_without_enabling_rollout():
    cli = _bare_cli()
    config = {
        "ads": {
            "user_opt_in": False,
            "enabled": False,
            "text": {"enabled": False, "messages": []},
        }
    }
    output = []
    with patch("loki_cli.config.load_config", return_value=config), \
            patch("loki_cli.config.save_config") as save, \
            patch("loki_cli.cli_commands_mixin._cp", side_effect=lambda *lines: output.extend(lines)):
        cli._handle_ads_command("/ads on")

    assert config["ads"]["user_opt_in"] is True
    assert config["ads"]["enabled"] is False
    assert config["ads"]["text"]["enabled"] is False
    save.assert_called_once_with(config)
    assert any("OPTED IN" in line for line in output)


def test_ads_off_revokes_consent():
    cli = _bare_cli()
    config = {"ads": {"user_opt_in": True, "enabled": True, "text": {"enabled": True}}}
    with patch("loki_cli.config.load_config", return_value=config), \
            patch("loki_cli.config.save_config") as save, \
            patch("loki_cli.cli_commands_mixin._cp"):
        cli._handle_ads_command("/ads off")

    assert config["ads"]["user_opt_in"] is False
    # Rollout switches are independent of consent and remain untouched.
    assert config["ads"]["enabled"] is True
    assert config["ads"]["text"]["enabled"] is True
    save.assert_called_once_with(config)


def test_ads_status_reports_saved_opt_in_when_delivery_is_still_dark():
    cli = _bare_cli()
    config = {"ads": {"user_opt_in": True, "enabled": False, "text": {"enabled": False}}}
    output = []
    with patch("loki_cli.config.load_config", return_value=config), \
            patch("loki_cli.cli_commands_mixin._cp", side_effect=lambda *lines: output.extend(lines)):
        cli._handle_ads_command("/ads status")

    rendered = "\n".join(output)
    assert "OPTED IN" in rendered
    assert "ad delivery is not enabled" in rendered


def test_jev_status_separates_key_and_router_state():
    cli = _bare_cli()
    config = {"smart_model_routing": {"enabled": False, "mode": "jev_auto"}}
    output = []
    with patch("loki_cli.config.load_config", return_value=config), \
            patch("agent.typesafe_client.configured_typesafe_key", return_value=""), \
            patch("loki_cli.cli_commands_mixin._cp", side_effect=lambda *lines: output.extend(lines)):
        cli._handle_jev_command("/jev status")

    rendered = "\n".join(output)
    assert "Loki Autorouter: OFF" in rendered
    assert "NOT CONFIGURED" in rendered
    assert "decision tool: unavailable" in rendered


def test_jev_enable_prompts_for_missing_key_then_enables_router():
    cli = _bare_cli()
    config = {"smart_model_routing": {"enabled": False, "mode": "jev_auto"}}
    key_states = iter(["", "ts-key"])
    with patch("loki_cli.config.load_config", return_value=config), \
            patch("agent.typesafe_client.configured_typesafe_key", side_effect=lambda: next(key_states)), \
            patch("loki_cli.callbacks.prompt_for_secret", return_value={"success": True, "skipped": False}) as prompt, \
            patch("loki_cli.config.save_config") as save, \
            patch("loki_cli.cli_commands_mixin._cp"):
        cli._handle_jev_command("/jev enable")

    prompt.assert_called_once()
    assert config["smart_model_routing"]["enabled"] is True
    assert config["smart_model_routing"]["mode"] == "jev_auto"
    save.assert_called_once_with(config)


def test_jev_enable_with_existing_key_does_not_prompt():
    cli = _bare_cli()
    config = {"smart_model_routing": {"enabled": False, "mode": "jev_auto"}}
    with patch("loki_cli.config.load_config", return_value=config), \
            patch("agent.typesafe_client.configured_typesafe_key", return_value="ts-key"), \
            patch("loki_cli.callbacks.prompt_for_secret") as prompt, \
            patch("loki_cli.config.save_config") as save, \
            patch("loki_cli.cli_commands_mixin._cp"):
        cli._handle_jev_command("/jev enable")

    prompt.assert_not_called()
    assert config["smart_model_routing"]["enabled"] is True
    save.assert_called_once_with(config)


def test_jev_disable_keeps_key_and_turns_router_off():
    cli = _bare_cli()
    config = {"smart_model_routing": {"enabled": True, "mode": "jev_auto"}}
    with patch("loki_cli.config.load_config", return_value=config), \
            patch("agent.typesafe_client.configured_typesafe_key", return_value="ts-key"), \
            patch("loki_cli.config.save_config") as save, \
            patch("loki_cli.cli_commands_mixin._cp"):
        cli._handle_jev_command("/jev disable")

    assert config["smart_model_routing"]["enabled"] is False
    save.assert_called_once_with(config)


def test_settings_jev_on_remains_backward_compatible():
    cli = _bare_cli()
    config = {"smart_model_routing": {"enabled": False, "mode": "jev_auto"}}
    with patch("loki_cli.config.load_config", return_value=config), \
            patch("agent.typesafe_client.configured_typesafe_key", return_value="ts-key"), \
            patch("loki_cli.config.save_config") as save, \
            patch("loki_cli.cli_commands_mixin._cp"):
        cli._handle_settings_command("/settings jev on")

    assert config["smart_model_routing"]["enabled"] is True
    save.assert_called_once_with(config)

