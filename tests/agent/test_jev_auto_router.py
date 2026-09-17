from types import SimpleNamespace

import pytest

import agent.jev_auto_router as router


class _DB:
    def __init__(self, *, message_count=0, route=None):
        self.message_count = message_count
        self.route = route
        self.updated = []
        self.patches = []

    def get_session(self, session_id):
        return {"id": session_id, "message_count": self.message_count, "model_config": None}

    def get_session_model_config_value(self, session_id, key, default=None):
        return self.route if key == "jev_auto_route" else default

    def update_session_model(self, session_id, model, provider=None):
        self.updated.append((session_id, model, provider))

    def patch_session_model_config(self, session_id, patch):
        self.patches.append((session_id, patch))


def _agent(db=None):
    return SimpleNamespace(
        provider="openrouter",
        model="vendor/expensive",
        api_key="or-key",
        base_url="https://openrouter.ai/api/v1",
        api_mode="chat_completions",
        session_id="s1",
        _session_db=db,
        _parent_session_id=None,
    )


def _candidate(model, cost, *, reasoning=False, vision=False):
    return router.JevAutoCandidate(
        model=model,
        tools=True,
        reasoning=reasoning,
        vision=vision,
        context_window=128000,
        input_cost_per_million=cost,
        output_cost_per_million=cost,
    )


def test_router_off_never_calls_typesafe(monkeypatch):
    monkeypatch.setattr(router, "_routing_config", lambda: {"enabled": False, "mode": "jev_auto"})
    monkeypatch.setattr(router, "configured_typesafe_key", lambda: "ts-key")
    monkeypatch.setattr(router, "choose_model", lambda **kwargs: pytest.fail("Jev should not be called"))
    assert router.maybe_route_first_session_task(_agent(_DB()), "hello", []) is False


def test_existing_session_never_reroutes(monkeypatch):
    monkeypatch.setattr(router, "_routing_config", lambda: {"enabled": True, "mode": "jev_auto"})
    monkeypatch.setattr(router, "configured_typesafe_key", lambda: "ts-key")
    monkeypatch.setattr(router, "choose_model", lambda **kwargs: pytest.fail("Jev should not be called"))
    assert router.maybe_route_first_session_task(_agent(_DB(message_count=2)), "hello", []) is False


def test_route_is_same_gateway_sticky_and_persisted(monkeypatch):
    db = _DB()
    agent = _agent(db)
    monkeypatch.setattr(
        router,
        "_routing_config",
        lambda: {
            "enabled": True,
            "mode": "jev_auto",
            "confidence_threshold": 0.55,
            "max_candidates": 12,
            "cost_bias": "economy",
        },
    )
    monkeypatch.setattr(router, "configured_typesafe_key", lambda: "ts-key")
    monkeypatch.setattr(
        router,
        "discover_candidates",
        lambda *args, **kwargs: [
            _candidate("vendor/expensive", 10, reasoning=True),
            _candidate("vendor/cheap", 0.2),
        ],
    )
    monkeypatch.setattr(router, "choose_model", lambda **kwargs: ("vendor/cheap", 0.91))

    switches = []

    def fake_switch(agent_obj, model, provider, **kwargs):
        switches.append((model, provider, kwargs))
        agent_obj.model = model

    monkeypatch.setattr("agent.agent_runtime_helpers.switch_model", fake_switch)

    assert router.maybe_route_first_session_task(agent, "summarize this", []) is True
    assert switches[0][0:2] == ("vendor/cheap", "openrouter")
    assert switches[0][2]["api_key"] == "or-key"
    assert db.updated == [("s1", "vendor/cheap", "openrouter")]
    route = db.patches[-1][1]["jev_auto_route"]
    assert route["chosen_model"] == "vendor/cheap"
    assert route["provider"] == "openrouter"
    assert "summarize this" not in str(route)
    # In-memory latch prevents another decision even before the DB message count changes.
    assert router.maybe_route_first_session_task(agent, "second", []) is False


def test_low_confidence_keeps_current_model(monkeypatch):
    db = _DB()
    agent = _agent(db)
    monkeypatch.setattr(router, "_routing_config", lambda: {
        "enabled": True, "mode": "jev_auto", "confidence_threshold": 0.8,
    })
    monkeypatch.setattr(router, "configured_typesafe_key", lambda: "ts-key")
    monkeypatch.setattr(router, "discover_candidates", lambda *a, **k: [
        _candidate("vendor/expensive", 10), _candidate("vendor/cheap", 0.1)
    ])
    monkeypatch.setattr(router, "choose_model", lambda **kwargs: ("vendor/cheap", 0.6))
    monkeypatch.setattr(
        "agent.agent_runtime_helpers.switch_model",
        lambda *a, **k: pytest.fail("low-confidence route must not switch"),
    )

    assert router.maybe_route_first_session_task(agent, "hard task", []) is False
    assert db.updated == []
    assert db.patches[-1][1]["jev_auto_route"]["chosen_model"] == "vendor/expensive"


def test_typesafe_failure_fails_open(monkeypatch):
    monkeypatch.setattr(router, "_routing_config", lambda: {"enabled": True, "mode": "jev_auto"})
    monkeypatch.setattr(router, "configured_typesafe_key", lambda: "ts-key")
    monkeypatch.setattr(router, "discover_candidates", lambda *a, **k: [
        _candidate("vendor/expensive", 10), _candidate("vendor/cheap", 0.1)
    ])

    def fail(**kwargs):
        raise router.TypeSafeRequestError("network unavailable")

    monkeypatch.setattr(router, "choose_model", fail)
    agent = _agent(_DB())
    assert router.maybe_route_first_session_task(agent, "hello", []) is False
    assert agent.model == "vendor/expensive"


def test_choice_request_contains_task_and_same_gateway_candidates(monkeypatch):
    captured = {}

    def fake_request(**kwargs):
        captured.update(kwargs)
        return {"answers": {"route_model": {"choice": "vendor/cheap", "confidence": 0.9}}}

    monkeypatch.setattr(router, "request_system_one", fake_request)
    candidates = [_candidate("vendor/current", 4), _candidate("vendor/cheap", 0.2)]
    choice, confidence = router.choose_model(
        task="write a regex",
        provider="openrouter",
        current_model="vendor/current",
        candidates=candidates,
        cost_bias="balanced",
    )
    assert (choice, confidence) == ("vendor/cheap", 0.9)
    assert captured["state"]["gateway"] == "openrouter"
    assert captured["state"]["task"] == "write a regex"
    assert "api_key" not in captured["state"]
    assert "or-key" not in str(captured)
    assert set(captured["questions"]["route_model"]["criteria"]) == {"vendor/current", "vendor/cheap"}


def test_multimodal_task_marks_vision():
    text, vision = router._task_text_and_vision([
        {"type": "text", "text": "describe this"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
    ])
    assert text == "describe this"
    assert vision is True


def test_custom_gateway_catalog_routes_without_models_dev_metadata(monkeypatch):
    monkeypatch.setattr(
        "loki_cli.models.cached_provider_model_ids",
        lambda provider: ["private/cheap", "private/strong", "private/current"],
    )
    monkeypatch.setattr("agent.models_dev.get_model_info", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "loki_cli.models_pricing.get_pricing_for_provider",
        lambda provider, cached_only=True: {
            "private/cheap": {"prompt": "0.0000001", "completion": "0.0000002"},
            "private/strong": {"prompt": "0.000001", "completion": "0.000002"},
        },
    )

    candidates = router.discover_candidates("my-private-gateway", "private/current", max_candidates=12)
    assert {candidate.model for candidate in candidates} == {
        "private/current", "private/cheap", "private/strong"
    }
    cheap = next(candidate for candidate in candidates if candidate.model == "private/cheap")
    assert cheap.input_cost_per_million == pytest.approx(0.1)
    assert cheap.output_cost_per_million == pytest.approx(0.2)
