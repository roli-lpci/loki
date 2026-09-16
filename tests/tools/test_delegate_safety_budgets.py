from types import SimpleNamespace
from unittest.mock import patch

from tools import delegate_tool
from tools.delegate_tool_child_run import _SchemaOutcome, _build_result_entry


def test_delegation_safety_defaults_are_bounded(monkeypatch):
    monkeypatch.delenv("DELEGATION_MAX_CONCURRENT_CHILDREN", raising=False)
    monkeypatch.delenv("DELEGATION_MAX_INPUT_TOKENS", raising=False)
    with patch("tools.delegate_tool._load_config", return_value={}):
        assert delegate_tool._get_max_concurrent_children() == 4
        assert delegate_tool._get_max_input_tokens() == 300_000
    assert delegate_tool.DEFAULT_MAX_ITERATIONS == 80


def test_max_input_tokens_can_be_overridden_or_disabled(monkeypatch):
    monkeypatch.delenv("DELEGATION_MAX_INPUT_TOKENS", raising=False)
    with patch("tools.delegate_tool._load_config", return_value={"max_input_tokens": 125_000}):
        assert delegate_tool._get_max_input_tokens() == 125_000
    with patch("tools.delegate_tool._load_config", return_value={"max_input_tokens": 0}):
        assert delegate_tool._get_max_input_tokens() is None


def test_delegation_budget_exit_is_a_parent_visible_failure():
    child = SimpleNamespace(
        model="test-model",
        session_estimated_cost_usd=1.25,
        session_cost_status="estimated",
        session_prompt_tokens=300_000,
        session_completion_tokens=2_000,
        _delegate_role="leaf",
    )
    entry = _build_result_entry(
        child,
        {
            "final_response": "partial findings",
            "completed": False,
            "api_calls": 7,
            "messages": [],
            "turn_exit_reason": "delegation_input_budget_exhausted",
        },
        0,
        1.0,
        _SchemaOutcome(None, None, [], 0),
    )
    assert entry["status"] == "failed"
    assert entry["exit_reason"] == "input_token_budget"
    assert entry["truncated"] is False
    assert "max_input_tokens" in entry["error"]
