from wcwidth import wcswidth


def test_setup_banner_uses_terminal_cell_width(monkeypatch, capsys):
    import loki_cli.setup as setup

    monkeypatch.setattr(setup, "color", lambda text, *codes: text)
    setup._print_banner(
        "𖤍 Loki Agent Setup Wizard",
        "Let's configure your Loki Agent installation.",
        "Press Ctrl+C at any time to exit.",
    )

    lines = [line for line in capsys.readouterr().out.splitlines() if line]
    assert len(lines) == 6
    widths = [wcswidth(line) for line in lines]
    assert len(set(widths)) == 1
    assert widths[0] == 59
    assert all(line.endswith(("┐", "│", "┤", "┘")) for line in lines)


def test_setup_banner_uses_loki_truecolor_blue(monkeypatch, capsys):
    import loki_cli.setup as setup

    monkeypatch.setattr(setup, "color", lambda text, *codes: "|".join(codes) + ":" + text)
    setup._print_banner("𖤍 Loki Agent Setup Wizard")
    rendered = capsys.readouterr().out

    assert "38;2;37;99;235m" in rendered
    assert "38;2;147;197;253m" in rendered
    assert setup.Colors.MAGENTA not in rendered
