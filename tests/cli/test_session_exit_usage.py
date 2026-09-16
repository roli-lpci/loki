from datetime import datetime
from types import SimpleNamespace

from cli import LokiCLI
from loki_cli.session_epilogue import SessionTokenUsage


def test_session_token_usage_total_does_not_double_count_reasoning():
    usage = SessionTokenUsage(
        input_tokens=1_000,
        output_tokens=300,
        cache_read_tokens=2_000,
        cache_write_tokens=100,
        reasoning_tokens=125,
    )

    assert usage.total_tokens == 3_400
    assert usage.render() == (
        "Tokens:         3,400 total (in 1,000, out 300, cache 2,100; reasoning 125 of out)"
    )


def test_exit_summary_prints_persisted_session_token_usage(capsys, monkeypatch):
    class FakeDB:
        def get_session(self, session_id):
            assert session_id == "session-usage"
            return {
                "input_tokens": 1_250,
                "output_tokens": 400,
                "cache_read_tokens": 3_000,
                "cache_write_tokens": 50,
                "reasoning_tokens": 175,
            }

        def get_session_title(self, session_id):
            assert session_id == "session-usage"
            return None

    cli = LokiCLI.__new__(LokiCLI)
    cli.session_id = "session-usage"
    cli.conversation_history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    cli.session_start = datetime.now()
    cli._session_db = FakeDB()
    cli.agent = SimpleNamespace(session_total_tokens=999_999)
    cli._clear_terminal_on_exit = lambda: None

    monkeypatch.setattr("loki_cli.profiles.get_active_profile_name", lambda: "default")
    cli._print_exit_summary(clear_screen=False)

    output = capsys.readouterr().out
    assert "Tokens:         4,700 total (in 1,250, out 400, cache 3,050; reasoning 175 of out)" in output
    assert "999,999" not in output
    assert "Farewell!" in output
