import json

import tools.typesafe_tool as typesafe
import agent.typesafe_client as typesafe_client


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


class _FakeClient:
    response = _FakeResponse(
        200,
        {
            "answers": {
                "route": {
                    "choice": "billing",
                    "probabilities": {"billing": 0.91, "technical": 0.09},
                    "confidence": 0.82,
                }
            }
        },
    )
    calls = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, **kwargs):
        type(self).calls.append((url, kwargs))
        return type(self).response


def test_typesafe_key_check_uses_loki_config(monkeypatch):
    monkeypatch.setattr(typesafe, "get_env_value", lambda name: "ts-key" if name == "TYPESAFE_API_KEY" else None)
    assert typesafe.check_typesafe_api_key() is True

    monkeypatch.setattr(typesafe, "get_env_value", lambda name: None)
    assert typesafe.check_typesafe_api_key() is False


def test_typesafe_ask_posts_system_one_payload_and_preserves_probabilities(monkeypatch):
    _FakeClient.calls.clear()
    monkeypatch.setattr(typesafe, "get_env_value", lambda name: "ts-secret")
    monkeypatch.setattr(typesafe_client.httpx, "Client", _FakeClient)

    result = json.loads(
        typesafe.typesafe_ask_tool(
            {"ticket": {"text": "I was charged twice."}},
            [
                {
                    "id": "route",
                    "type": "choice",
                    "instructions": "Which team should own this ticket?",
                    "criteria": {"billing": None, "technical": None},
                },
                {
                    "id": "urgent",
                    "type": "noul",
                    "instructions": "Does this ticket require urgent handling?",
                },
                {
                    "id": "severity",
                    "type": "score",
                    "instructions": "How severe is the customer impact?",
                    "criteria": ["minor inconvenience", "material impact", "service blocked"],
                },
            ],
        )
    )

    assert result["answers"]["route"]["probabilities"]["billing"] == 0.91
    assert len(_FakeClient.calls) == 1
    url, request = _FakeClient.calls[0]
    assert url == "https://api.typesafe.ai/v1/systemone"
    assert request["headers"]["Authorization"] == "Bearer ts-secret"
    assert request["json"]["model"] == "jev-latest"
    assert request["json"]["state"]["ticket"]["text"] == "I was charged twice."
    assert request["json"]["questions"]["route"]["type"] == "choice"
    assert request["json"]["questions"]["severity"]["criteria"][2] == "service blocked"
    assert "criteria" not in request["json"]["questions"]["urgent"]



def test_typesafe_ask_accepts_string_state_structured_instructions_and_noul_criteria(monkeypatch):
    _FakeClient.calls.clear()
    monkeypatch.setattr(typesafe, "get_env_value", lambda name: "ts-secret")
    monkeypatch.setattr(typesafe_client.httpx, "Client", _FakeClient)

    typesafe.typesafe_ask_tool(
        "Help! My payouts have been failing for 3 days.",
        [
            {
                "id": "urgent",
                "type": "noul",
                "instructions": {"question": "Does this convey urgency?", "exclude": "routine status"},
                "criteria": {
                    "true": "Explicitly time-sensitive",
                    "false": "No urgency expressed",
                },
            }
        ],
    )

    _, request = _FakeClient.calls[-1]
    assert request["json"]["state"] == "Help! My payouts have been failing for 3 days."
    assert request["json"]["questions"]["urgent"]["instructions"]["question"] == "Does this convey urgency?"
    assert request["json"]["questions"]["urgent"]["criteria"]["true"] == "Explicitly time-sensitive"


def test_typesafe_tool_schema_allows_all_documented_state_shapes():
    state_shapes = typesafe.TYPESAFE_ASK_SCHEMA["parameters"]["properties"]["state"]["anyOf"]
    assert [shape["type"] for shape in state_shapes] == ["string", "object", "array"]

def test_typesafe_ask_rejects_bad_question_before_network(monkeypatch):
    _FakeClient.calls.clear()
    monkeypatch.setattr(typesafe, "get_env_value", lambda name: "ts-secret")
    monkeypatch.setattr(typesafe_client.httpx, "Client", _FakeClient)

    result = json.loads(
        typesafe.typesafe_ask_tool(
            {"text": "hello"},
            [{"id": "route", "type": "choice", "instructions": "Pick one", "criteria": {"only": None}}],
        )
    )

    assert "at least two" in result["error"]
    assert _FakeClient.calls == []


def test_typesafe_api_error_never_echoes_key(monkeypatch):
    monkeypatch.setattr(typesafe, "get_env_value", lambda name: "ts-super-secret")
    monkeypatch.setattr(typesafe_client.httpx, "Client", _FakeClient)
    _FakeClient.response = _FakeResponse(401, payload={}, text="bad key ts-super-secret")
    try:
        result = json.loads(
            typesafe.typesafe_ask_tool(
                {"text": "hello"},
                [{"id": "ok", "type": "noul", "instructions": "Is this a greeting?"}],
            )
        )
    finally:
        _FakeClient.response = _FakeResponse(
            200,
            {"answers": {"ok": {"probability": 0.9}}},
        )

    assert result["status"] == 401
    assert "ts-super-secret" not in json.dumps(result)
    assert "[redacted]" in result["details"]
