"""Tests for TUI gateway slash_worker profile_home propagation (#40677)."""

from pathlib import Path
from unittest.mock import MagicMock, patch


def test_slash_worker_accepts_profile_home():
    """_SlashWorker.__init__ accepts profile_home parameter."""
    # loki_state evaluates get_loki_home() / "state.db" at import time, so
    # the mock must return a Path (a bare str raises TypeError under per-file
    # subprocess isolation).
    with patch.dict("sys.modules", {
        "loki_constants": MagicMock(
            get_loki_home=MagicMock(return_value=Path("/tmp/loki_test")),
        ),
    }):
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value.stdout = MagicMock()
            mock_popen.return_value.stderr = MagicMock()

            from tui_gateway.server import _SlashWorker

            # Test initialization with profile_home
            worker = _SlashWorker(
                session_key="test_key",
                model="test-model",
                profile_home="/home/luke/.loki/profiles/work"
            )

            # Verify Popen was called
            assert mock_popen.called

            # Check that LOKI_HOME was set in the environment
            call_kwargs = mock_popen.call_args[1]
            assert "env" in call_kwargs
            assert call_kwargs["env"]["LOKI_HOME"] == "/home/luke/.loki/profiles/work"


