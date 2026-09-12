"""Tests for ``_prompt_api_key`` — the shared Keep/Replace/Clear menu used by
``loki setup`` / ``loki model`` when an API key already exists in ``.env``.

Regression coverage for #16394: the wizard used to silently skip the key prompt
when any value was present (even malformed junk), leaving users stuck.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from loki_cli import main_provider_setup


@pytest.fixture
def profile_env(tmp_path, monkeypatch):
    home = tmp_path / ".loki"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("LOKI_HOME", str(home))
    (home / ".env").write_text("")
    return home


def _pconfig(name="deepseek"):
    from loki_cli.auth import PROVIDER_REGISTRY
    return PROVIDER_REGISTRY[name]


def _run_prompt(existing_key, choice, new_key="", provider_id="", pconfig_name="deepseek"):
    """Invoke _prompt_api_key with mocked input()/getpass() responses."""
    from loki_cli import main as m

    pconfig = _pconfig(pconfig_name)
    with patch("builtins.input", return_value=choice), \
         patch("loki_cli.secret_prompt.masked_secret_prompt", return_value=new_key):
        return main_provider_setup._prompt_api_key(pconfig, existing_key, provider_id=provider_id)


def test_pool_only_key_does_not_offer_or_execute_clear(profile_env, monkeypatch, capsys):
    from loki_cli import main as m

    pconfig = _pconfig("deepseek")
    prompts = []

    def choose_clear(prompt):
        prompts.append(prompt)
        return "c"

    monkeypatch.setattr("builtins.input", choose_clear)
    with patch("loki_cli.config.save_env_value") as save_env:
        key, abort = main_provider_setup._prompt_api_key(
            pconfig,
            "pool-secret",
            provider_id="deepseek",
            existing_source="credential_pool:deepseek",
        )

    assert key == "pool-secret"
    assert abort is False
    assert prompts and "[C]lear" not in prompts[0]
    assert "[K]eep / [R]eplace" in prompts[0]
    save_env.assert_not_called()
    assert "API key cleared" not in capsys.readouterr().out


# First-time entry ────────────────────────────────────────────────────────────



# Already configured — K / R / C ───────────────────────────────────────────────







def test_clear_wipes_env_and_aborts(profile_env):
    from loki_cli.config import get_env_value, save_env_value
    save_env_value("DEEPSEEK_API_KEY", "sk-existing")
    save_env_value("OTHER_VAR", "keep-me")

    key, abort = _run_prompt(existing_key="sk-existing", choice="c")
    assert key == ""
    assert abort is True
    # Cleared, but sibling entries untouched.
    assert not get_env_value("DEEPSEEK_API_KEY")
    assert get_env_value("OTHER_VAR") == "keep-me"




# LM Studio no-auth placeholder ────────────────────────────────────────────────

def test_lmstudio_first_time_empty_uses_placeholder(profile_env):
    from loki_cli.auth import LMSTUDIO_NOAUTH_PLACEHOLDER
    from loki_cli.config import get_env_value

    key, abort = _run_prompt(
        existing_key="", choice="", new_key="",
        provider_id="lmstudio", pconfig_name="lmstudio",
    )
    assert key == LMSTUDIO_NOAUTH_PLACEHOLDER
    assert abort is False
    assert get_env_value("LM_API_KEY") == LMSTUDIO_NOAUTH_PLACEHOLDER




def test_openrouter_first_time_o_opens_key_page_then_accepts_key(profile_env, monkeypatch, capsys):
    from loki_cli.auth import ProviderConfig
    from loki_cli.config import get_env_value

    pconfig = ProviderConfig(
        id="openrouter",
        name="OpenRouter",
        auth_type="api_key",
        api_key_env_vars=("OPENROUTER_API_KEY",),
    )
    answers = iter(["o", "sk-or-v1-test"])
    monkeypatch.setattr(
        "loki_cli.secret_prompt.masked_secret_prompt",
        lambda _prompt: next(answers),
    )
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)

    key, abort = main_provider_setup._prompt_api_key(
        pconfig,
        "",
        provider_id="openrouter",
        open_url="https://openrouter.ai/keys",
    )

    assert abort is False
    assert key == "sk-or-v1-test"
    assert opened == ["https://openrouter.ai/keys"]
    assert get_env_value("OPENROUTER_API_KEY") == "sk-or-v1-test"
    assert "Opened https://openrouter.ai/keys" in capsys.readouterr().out
