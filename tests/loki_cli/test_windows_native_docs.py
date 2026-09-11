from pathlib import Path


def test_windows_native_install_path_docs_match_installer() -> None:
    doc = Path("website/docs/user-guide/windows-native.md").read_text()
    install = Path("scripts/install.ps1").read_text()

    # The launchers live in the managed binary dir OUTSIDE the git checkout
    # (LOKI_HOME\bin, next to the managed uv) — NOT the whole venv\Scripts
    # (which would shadow the user's python, #83797) and NOT a dir inside
    # the checkout (which `loki update`'s autostash swept off disk).
    assert "%LOCALAPPDATA%\\loki\\bin" in doc
    assert (
        "Get-Command loki        # should print "
        "C:\\Users\\<you>\\AppData\\Local\\loki\\bin\\loki.exe"
    ) in doc
    # Installer exposes $LokiHome\bin, and must copy the launchers into it.
    assert '$lokiBin = "$LokiHome\\bin"' in install
    assert "loki.exe" in install and "loki-acp.exe" in install
    # Guard against regressions to either legacy layout.
    assert '$lokiBin = "$InstallDir\\venv\\Scripts"' not in install
    assert '$lokiBin = "$InstallDir\\bin"' not in install
