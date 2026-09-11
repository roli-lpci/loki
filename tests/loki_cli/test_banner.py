"""Tests for banner toolset name normalization and skin color usage."""

from unittest.mock import patch

from rich.console import Console

import loki_cli.banner as banner
import model_tools
import tools.mcp_tool_discovery


def test_cprint_falls_back_to_plain_print_when_prompt_toolkit_has_no_console(capsys):
    with patch(
        "prompt_toolkit.print_formatted_text",
        side_effect=RuntimeError("no console screen buffer"),
    ):
        banner.cprint("fallback text")

    assert capsys.readouterr().out == "fallback text\n"








def test_build_welcome_banner_title_falls_back_when_no_tag():
    """Without a resolvable tag, the panel title renders as plain text (no hyperlink escape)."""
    import io
    from unittest.mock import patch as _patch
    import loki_cli.banner as _banner
    import model_tools as _mt
    import tools.mcp_tool as _mcp
    from tools import mcp_tool_discovery as _mcp_discovery

    _banner._latest_release_cache = None
    buf = io.StringIO()
    with (
        _patch.object(_mt, "check_tool_availability", return_value=(["web"], [])),
        _patch.object(_banner, "get_available_skills", return_value={}),
        _patch.object(_banner, "get_update_result", return_value=None),
        _patch.object(_mcp_discovery, "get_mcp_status", return_value=[]),
        _patch.object(_banner, "get_latest_release_tag", return_value=None),
    ):
        console = Console(file=buf, force_terminal=True, color_system="truecolor", width=160)
        _banner.build_welcome_banner(
            console=console, model="x", cwd="/tmp",
            session_id="abc123",
            tools=[{"function": {"name": "read_file"}}],
            get_toolset_for_tool=lambda n: "file",
        )

    raw = buf.getvalue()
    assert "Loki Agent v" in raw, "Version label missing from title"
    assert "\x1b]8;" not in raw, "OSC-8 hyperlink should not be emitted without a tag"






def test_build_welcome_banner_non_moa_unchanged(tmp_path, monkeypatch):
    """A normal provider still renders the bare model slug, no MoA prefix."""
    monkeypatch.setenv("LOKI_HOME", str(tmp_path / ".loki"))
    (tmp_path / ".loki").mkdir()

    with (
        patch.object(model_tools, "check_tool_availability", return_value=([], [])),
        patch.object(banner, "get_available_skills", return_value={}),
        patch.object(banner, "get_update_result", return_value=None),
        patch.object(tools.mcp_tool_discovery, "get_mcp_status", return_value=[]),
    ):
        console = Console(record=True, force_terminal=False, color_system=None, width=160)
        banner.build_welcome_banner(
            console=console,
            model="anthropic/claude-opus-4.8",
            cwd="/tmp/project",
            tools=[],
            enabled_toolsets=[],
            provider="openrouter",
        )

    out = console.export_text()
    assert "claude-opus-4.8" in out
    assert "MoA:" not in out


def test_empty_model_shows_the_free_tier_route_when_it_carries_inference(tmp_path, monkeypatch):
    """The banner prints before credentials resolve, so ``model`` is empty on a fresh install. On the
    free tier the route is known locally (identity on disk + tier on): the banner shows its model.
    When nothing resolves the red "no model configured" line stays."""
    monkeypatch.setenv("LOKI_HOME", str(tmp_path / ".loki"))
    (tmp_path / ".loki").mkdir()
    import loki_cli.anon_auth as anon_auth

    def render(carries: bool) -> str:
        with (
            patch.object(model_tools, "check_tool_availability", return_value=([], [])),
            patch.object(banner, "get_available_skills", return_value={}),
            patch.object(banner, "get_update_result", return_value=None),
            patch.object(tools.mcp_tool_discovery, "get_mcp_status", return_value=[]),
            patch.object(anon_auth, "guest_carries_inference", return_value=carries),
        ):
            console = Console(record=True, force_terminal=False, color_system=None, width=160)
            banner.build_welcome_banner(console=console, model="", cwd="/tmp/project", tools=[],
                                        enabled_toolsets=[], provider="auto")
        return console.export_text()

    assert "welcome" in render(True) and "no model configured" not in render(True)
    assert "no model configured" in render(False)


def _render_responsive_banner(width: int) -> str:
    import io

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, color_system=None, width=width)
    with (
        patch.object(banner, "get_available_skills", return_value={"devops": ["sdlc-review"]}),
        patch.object(banner, "get_update_result", return_value=0),
        patch.object(banner, "get_latest_release_tag", return_value=None),
        patch.object(banner, "_mcp_configured", return_value=False),
        patch.object(banner, "_active_profile_name", return_value=None),
        patch.object(banner, "_codex_runtime_active", return_value=False),
    ):
        banner.build_welcome_banner(
            console=console,
            model="us.openai.gpt-5.6-luna",
            cwd="/tmp/project",
            tools=[{"function": {"name": "read_file"}}],
            enabled_toolsets=["skills"],
            session_id="session-123",
            get_toolset_for_tool=lambda _name: "file",
            availability={"unavailable_toolsets": [], "lazy_tools": [], "disabled_tools": []},
            skills_by_category={"devops": ["sdlc-review"]},
        )
    return buf.getvalue()


def test_banner_uses_large_wordmark_only_on_wide_terminals():
    wide = _render_responsive_banner(160)
    normal = _render_responsive_banner(80)

    assert "██████╗" in wide
    assert "▄██▄" in normal
    assert "██████╗" not in normal


def test_banner_stacks_and_keeps_company_centered_on_normal_terminals():
    rendered = _render_responsive_banner(80)

    assert rendered.count("by WunderCorp, Inc.") == 1
    assert "Available Tools" in rendered
    assert max(len(line) for line in rendered.splitlines()) <= 80


def test_banner_has_minimal_fallback_for_very_narrow_terminals():
    rendered = _render_responsive_banner(48)

    assert "L O K I" in rendered
    assert "A G E N T" in rendered
    assert max(len(line) for line in rendered.splitlines()) <= 48
