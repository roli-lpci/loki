import argparse

from loki_cli.config_defaults import OPTIONAL_ENV_VARS


def test_typesafe_key_is_a_first_class_tool_credential():
    info = OPTIONAL_ENV_VARS["TYPESAFE_API_KEY"]
    assert info["category"] == "tool"
    assert info["password"] is True
    assert info["url"] == "https://console.typesafe.ai"
    assert info["tools"] == ["typesafe_ask"]


def test_setup_typesafe_prompts_and_saves_new_key(monkeypatch):
    from loki_cli import setup
    from loki_cli.setup_typesafe import setup_typesafe_jev

    saved = []
    monkeypatch.setattr(setup, "get_env_value", lambda name: None)
    monkeypatch.setattr(setup, "prompt", lambda *args, **kwargs: "ts-new-key")
    monkeypatch.setattr(setup, "save_env_value", lambda name, value: saved.append((name, value)))
    monkeypatch.setattr(setup, "print_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "_section_rule", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_success", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_warning", lambda *args, **kwargs: None)

    setup_typesafe_jev({})

    assert saved == [("TYPESAFE_API_KEY", "ts-new-key")]


def test_setup_typesafe_can_remove_existing_key(monkeypatch):
    from loki_cli import setup
    from loki_cli.setup_typesafe import setup_typesafe_jev

    removed = []
    monkeypatch.setattr(setup, "get_env_value", lambda name: "ts-existing")
    monkeypatch.setattr(setup, "prompt_choice", lambda *args, **kwargs: 2)
    monkeypatch.setattr(setup, "remove_env_value", lambda name: removed.append(name))
    monkeypatch.setattr(setup, "print_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_success", lambda *args, **kwargs: None)

    setup_typesafe_jev({})

    assert removed == ["TYPESAFE_API_KEY"]


def test_setup_parser_accepts_jev_section():
    from loki_cli.subcommands.setup import build_setup_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    build_setup_parser(subparsers, cmd_setup=lambda args: None)

    args = parser.parse_args(["setup", "jev"])
    assert args.section == "jev"


def test_first_time_mode_offers_typesafe_jev():
    from loki_cli.setup import _FIRST_TIME_MODES

    matching = [(label, runner) for label, runner in _FIRST_TIME_MODES if "TypeSafe Jev" in label]
    assert matching == [
        (
            "Quick Setup + TypeSafe Jev — OpenRouter chat plus Jev typed decisions",
            "_run_first_time_typesafe_setup",
        )
    ]


def test_typesafe_first_time_wrapper_includes_jev_step(monkeypatch, tmp_path):
    from loki_cli import model_setup_flows, setup, setup_quick, setup_typesafe

    calls = []
    monkeypatch.setattr(model_setup_flows, "_model_flow_openrouter", lambda config: calls.append("openrouter"))
    monkeypatch.setattr(setup_quick, "_reload_config_into", lambda config: None)
    monkeypatch.setattr(setup_quick, "_print_macos_fda_tip", lambda: None)
    monkeypatch.setattr(setup_typesafe, "setup_typesafe_jev", lambda config: calls.append("typesafe"))
    monkeypatch.setattr(setup, "setup_terminal_backend", lambda config: calls.append("terminal"))
    monkeypatch.setattr(setup, "_apply_default_agent_settings", lambda config: calls.append("defaults"))
    monkeypatch.setattr(setup, "save_config", lambda config: None)
    monkeypatch.setattr(setup, "prompt_choice", lambda *args, **kwargs: 1)
    monkeypatch.setattr(setup, "_print_setup_summary", lambda config, loki_home: None)
    monkeypatch.setattr(setup, "print_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_success", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "_info", lambda *args, **kwargs: None)
    monkeypatch.setattr("loki_cli.gateway.ensure_gateway_service", lambda **kwargs: calls.append("gateway-service"))

    setup_quick._run_first_time_typesafe_setup({}, tmp_path, False)

    assert calls == ["openrouter", "typesafe", "terminal", "defaults", "gateway-service"]


def test_setup_typesafe_can_enable_jev_auto_with_existing_key(monkeypatch):
    from loki_cli import setup
    from loki_cli.setup_typesafe import setup_typesafe_jev

    choices = iter([0, 1])  # keep key, then enable Jev Auto
    monkeypatch.setattr(setup, "get_env_value", lambda name: "ts-existing")
    monkeypatch.setattr(setup, "prompt_choice", lambda *args, **kwargs: next(choices))
    monkeypatch.setattr(setup, "print_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_success", lambda *args, **kwargs: None)

    config = {}
    setup_typesafe_jev(config)

    assert config["smart_model_routing"]["enabled"] is True
    assert config["smart_model_routing"]["mode"] == "jev_auto"


def test_removing_typesafe_key_disables_jev_auto(monkeypatch):
    from loki_cli import setup
    from loki_cli.setup_typesafe import setup_typesafe_jev

    monkeypatch.setattr(setup, "get_env_value", lambda name: "ts-existing")
    monkeypatch.setattr(setup, "prompt_choice", lambda *args, **kwargs: 2)
    monkeypatch.setattr(setup, "remove_env_value", lambda name: None)
    monkeypatch.setattr(setup, "print_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_success", lambda *args, **kwargs: None)

    config = {"smart_model_routing": {"enabled": True, "mode": "jev_auto"}}
    setup_typesafe_jev(config)

    assert config["smart_model_routing"]["enabled"] is False
