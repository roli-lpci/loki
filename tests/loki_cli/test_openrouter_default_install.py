from loki_cli.models_catalog_static import CANONICAL_PROVIDERS
from loki_cli.setup import _FIRST_TIME_MODES


def test_fresh_install_defaults_to_openrouter() -> None:
    assert "OpenRouter" in _FIRST_TIME_MODES[0][0]
    assert "WunderCorp" not in _FIRST_TIME_MODES[0][0]
    assert CANONICAL_PROVIDERS[0].slug == "openrouter"


def test_first_time_quick_setup_uses_openrouter(monkeypatch, tmp_path) -> None:
    from loki_cli import model_setup_flows, setup, setup_quick

    calls = []
    monkeypatch.setattr(model_setup_flows, "_model_flow_openrouter", lambda config: calls.append("openrouter"))
    monkeypatch.setattr(setup_quick, "_reload_config_into", lambda config: None)
    monkeypatch.setattr(setup_quick, "_print_macos_fda_tip", lambda: None)
    monkeypatch.setattr(setup, "setup_terminal_backend", lambda config: calls.append("terminal"))
    monkeypatch.setattr(setup, "_apply_default_agent_settings", lambda config: calls.append("defaults"))
    monkeypatch.setattr(setup, "save_config", lambda config: None)
    monkeypatch.setattr(setup, "prompt_choice", lambda *args, **kwargs: 0)
    monkeypatch.setattr(setup, "setup_gateway", lambda config: calls.append("gateway"))
    monkeypatch.setattr(setup, "_print_setup_summary", lambda config, loki_home: None)
    monkeypatch.setattr(setup, "print_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_success", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "print_warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "_info", lambda *args, **kwargs: None)

    setup_quick._run_first_time_quick_setup({}, tmp_path, False)

    assert calls == ["openrouter", "terminal", "defaults", "gateway"]
