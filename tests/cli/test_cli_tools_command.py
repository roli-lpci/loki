"""Tests for /tools slash command handler in the interactive CLI."""

from unittest.mock import MagicMock, patch

from cli import LokiCLI


def _make_cli(enabled_toolsets=None):
    """Build a minimal LokiCLI stub without running __init__."""
    cli_obj = LokiCLI.__new__(LokiCLI)
    cli_obj.enabled_toolsets = set(enabled_toolsets or ["web", "memory"])
    cli_obj._command_running = False
    cli_obj.console = MagicMock()
    return cli_obj


# ── /tools (no subcommand) ──────────────────────────────────────────────────


class TestToolsSlashNoSubcommand:

    def test_bare_tools_shows_tool_list(self):
        cli_obj = _make_cli()
        with patch.object(cli_obj, "show_tools") as mock_show:
            cli_obj._handle_tools_command("/tools")
        mock_show.assert_called_once()



# ── /tools list ─────────────────────────────────────────────────────────────


class TestToolsSlashList:

    def test_list_calls_backend(self, capsys):
        cli_obj = _make_cli()
        with patch("loki_cli.tools_config.load_config",
                   return_value={"platform_toolsets": {"cli": ["web"]}}), \
             patch("loki_cli.tools_config.save_config"):
            cli_obj._handle_tools_command("/tools list")
        out = capsys.readouterr().out
        assert "web" in out



# ── /tools disable (session reset) ──────────────────────────────────────────


class TestToolsSlashDisableWithReset:

    def test_disable_applies_directly_and_resets_session(self):
        """Disable applies immediately (no confirmation prompt) and resets session."""
        cli_obj = _make_cli(["web", "memory"])
        with patch("loki_cli.tools_config.load_config",
                   return_value={"platform_toolsets": {"cli": ["web", "memory"]}}), \
             patch("loki_cli.tools_config.save_config"), \
             patch("loki_cli.tools_config._get_platform_tools", return_value={"memory"}), \
             patch("loki_cli.config.load_config", return_value={}), \
             patch.object(cli_obj, "new_session") as mock_reset:
            cli_obj._handle_tools_command("/tools disable web")
        mock_reset.assert_called_once()
        assert "web" not in cli_obj.enabled_toolsets


    def test_disable_always_resets_session(self):
        """Even without a confirmation prompt, disable always resets the session."""
        cli_obj = _make_cli(["web", "memory"])
        with patch("loki_cli.tools_config.load_config",
                   return_value={"platform_toolsets": {"cli": ["web", "memory"]}}), \
             patch("loki_cli.tools_config.save_config"), \
             patch("loki_cli.tools_config._get_platform_tools", return_value={"memory"}), \
             patch("loki_cli.config.load_config", return_value={}), \
             patch.object(cli_obj, "new_session") as mock_reset:
            cli_obj._handle_tools_command("/tools disable web")
        mock_reset.assert_called_once()



# ── /tools enable (session reset) ───────────────────────────────────────────


class TestToolsSlashEnableWithReset:

    def test_enable_applies_directly_and_resets_session(self):
        """Enable applies immediately (no confirmation prompt) and resets session."""
        cli_obj = _make_cli(["memory"])
        with patch("loki_cli.tools_config.load_config",
                   return_value={"platform_toolsets": {"cli": ["memory"]}}), \
             patch("loki_cli.tools_config.save_config"), \
             patch("loki_cli.tools_config._get_platform_tools", return_value={"memory", "web"}), \
             patch("loki_cli.config.load_config", return_value={}), \
             patch.object(cli_obj, "new_session") as mock_reset:
            cli_obj._handle_tools_command("/tools enable web")
        mock_reset.assert_called_once()
        assert "web" in cli_obj.enabled_toolsets

    def test_enable_missing_name_prints_usage(self, capsys):
        cli_obj = _make_cli()
        cli_obj._handle_tools_command("/tools enable")
        out = capsys.readouterr().out
        assert "Usage" in out


def test_typesafe_toolset_list_marks_missing_key_as_not_ready(capsys):
    from loki_cli.tools_config_mcp import _print_tools_list

    with patch("loki_cli.config.get_env_value", return_value=None):
        _print_tools_list({"typesafe"}, {}, platform="cli")

    out = capsys.readouterr().out
    assert "typesafe" in out
    assert "not ready" in out
    assert "/jev setup" in out


def test_typesafe_toolset_list_points_to_router_status_when_key_exists(capsys):
    from loki_cli.tools_config_mcp import _print_tools_list

    with patch("loki_cli.config.get_env_value", return_value="ts-key"):
        _print_tools_list({"typesafe"}, {}, platform="cli")

    out = capsys.readouterr().out
    assert "key configured" in out
    assert "/jev status" in out


def test_tools_enable_reloads_existing_agent_tool_snapshot():
    """In-session tool changes must update AIAgent.tools, not only LokiCLI.enabled_toolsets."""
    cli_obj = _make_cli(["memory"])
    cli_obj.disabled_toolsets = []
    cli_obj.agent = MagicMock()
    cli_obj.agent._tool_search_scope_cache = ("stale", {"old_tool"})

    with patch("loki_cli.tools_config.load_config",
               return_value={"platform_toolsets": {"cli": ["memory", "web"]}}), \
         patch("loki_cli.tools_config.save_config"), \
         patch("loki_cli.tools_config._get_platform_tools", return_value={"memory", "web"}), \
         patch("loki_cli.config.load_config",
               return_value={"platform_toolsets": {"cli": ["memory", "web"]}, "agent": {}}), \
         patch("agent.agent_init._load_tools") as reload_tools, \
         patch.object(cli_obj, "new_session") as mock_reset:
        cli_obj._handle_tools_command("/tools enable web")

    mock_reset.assert_called_once()
    reload_tools.assert_called_once_with(cli_obj.agent, {"memory", "web"}, [])
    assert cli_obj.agent.enabled_toolsets == {"memory", "web"}
    assert cli_obj.agent.disabled_toolsets == []
    assert cli_obj.agent._tool_search_scope_cache is None
