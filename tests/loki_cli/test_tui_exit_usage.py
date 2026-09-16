from loki_cli import main_tui_launch


def test_tui_exit_summary_uses_canonical_token_math_and_farewell(monkeypatch, capsys):
    class FakeDB:
        def get_session(self, session_id):
            assert session_id == "tui-session"
            return {
                "message_count": 3,
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read_tokens": 200,
                "cache_write_tokens": 10,
                "reasoning_tokens": 25,
            }

        def get_session_title(self, session_id):
            return "TUI session"

        def close(self):
            pass

    monkeypatch.setattr("loki_state.SessionDB", FakeDB)
    monkeypatch.setattr("loki_cli.main._resolve_last_session", lambda source: None)

    main_tui_launch._print_tui_exit_summary("tui-session")

    output = capsys.readouterr().out
    assert "Tokens:         360 total (in 100, out 50, cache 210; reasoning 25 of out)" in output
    assert "385" not in output
    assert "Farewell!" in output
