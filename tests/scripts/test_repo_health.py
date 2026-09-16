from pathlib import Path

from scripts.repo_health import is_tracked_junk, scan


def test_tracked_junk_classification():
    assert is_tracked_junk("pkg/__pycache__/x.pyc")
    assert is_tracked_junk("website/build/index.html")
    assert is_tracked_junk(".DS_Store")
    assert not is_tracked_junk("tui-ui/src/index.ts")
    assert not is_tracked_junk("tui_gateway/server.py")


def test_scan_reports_legacy_workspace_name(tmp_path: Path):
    legacy = tmp_path / "ui-tui" / "src"
    legacy.mkdir(parents=True)
    (legacy / "index.ts").write_text("export {}", encoding="utf-8")
    report = scan(tmp_path, 5)
    assert report["legacy_paths"] == ["ui-tui/src/index.ts"]
