from types import SimpleNamespace

import agent.ads as ads


def _agent():
    return SimpleNamespace(_parent_session_id=None)


def _result():
    return {
        "completed": True,
        "final_response": "Normal assistant answer.",
        "messages": [{"role": "assistant", "content": "Normal assistant answer."}],
    }


def test_ads_are_off_by_default(monkeypatch):
    monkeypatch.setattr(ads, "_ads_config", lambda: {
        "enabled": False,
        "text": {"enabled": False, "every_n_turns": 1, "messages": ["Buy this"]},
    })
    result = _result()
    before_messages = list(result["messages"])
    ads.maybe_attach_text_ad(_agent(), result)
    assert result["final_response"] == "Normal assistant answer."
    assert "advertisement" not in result
    assert result["messages"] == before_messages


def test_both_opt_in_gates_are_required(monkeypatch):
    monkeypatch.setattr(ads, "_ads_config", lambda: {
        "user_opt_in": True,
        "enabled": True,
        "text": {"enabled": False, "every_n_turns": 1, "messages": ["Buy this"]},
    })
    result = _result()
    ads.maybe_attach_text_ad(_agent(), result)
    assert "advertisement" not in result


def test_opted_in_text_ad_is_labeled_and_never_enters_transcript(monkeypatch):
    monkeypatch.setattr(ads, "_ads_config", lambda: {
        "user_opt_in": True,
        "enabled": True,
        "text": {
            "enabled": True,
            "every_n_turns": 1,
            "messages": [{"sponsor": "ExampleCo", "text": "Save on compute", "url": "https://example.test"}],
        },
    })
    agent = _agent()
    result = _result()
    original_messages = [dict(row) for row in result["messages"]]
    ads.maybe_attach_text_ad(agent, result)
    assert result["final_response"] == "Normal assistant answer."
    assert result["advertisement"]["label"] == "Sponsored"
    assert result["advertisement"]["display_text"].startswith("Sponsored\nExampleCo: Save on compute")
    assert result["messages"] == original_messages


def test_user_opt_in_is_required_even_when_rollout_gates_are_on(monkeypatch):
    monkeypatch.setattr(ads, "_ads_config", lambda: {
        "user_opt_in": False,
        "enabled": True,
        "text": {"enabled": True, "every_n_turns": 1, "messages": ["Buy this"]},
    })
    result = _result()
    ads.maybe_attach_text_ad(_agent(), result)
    assert "advertisement" not in result


def test_subagents_never_receive_ads(monkeypatch):
    monkeypatch.setattr(ads, "_ads_config", lambda: {
        "user_opt_in": True,
        "enabled": True,
        "text": {"enabled": True, "every_n_turns": 1, "messages": ["Buy this"]},
    })
    agent = SimpleNamespace(_parent_session_id="parent")
    result = _result()
    ads.maybe_attach_text_ad(agent, result)
    assert "advertisement" not in result


def test_shipped_defaults_opt_every_user_out_and_hide_ads_from_desktop_schema():
    from loki_cli.config_defaults import DEFAULT_CONFIG
    from loki_cli.web_server_config import CONFIG_SCHEMA

    assert DEFAULT_CONFIG["ads"]["user_opt_in"] is False
    assert DEFAULT_CONFIG["ads"]["enabled"] is False
    assert DEFAULT_CONFIG["ads"]["text"]["enabled"] is False
    assert not any(key == "ads" or key.startswith("ads.") for key in CONFIG_SCHEMA)
