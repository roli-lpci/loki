from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "sync_version.py"
    spec = importlib.util.spec_from_file_location("sync_version", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_choose_next_version_bumps_when_registry_matches_local():
    module = load_module()
    assert module.choose_next_version("0.21.4", "0.21.4", "patch") == "0.21.5"


def test_choose_next_version_keeps_unpublished_local_version():
    module = load_module()
    assert module.choose_next_version("0.21.5", "0.21.4", "patch") == "0.21.5"


def test_choose_next_version_uses_registry_as_baseline():
    module = load_module()
    assert module.choose_next_version("0.21.4", "0.21.6", "minor") == "0.22.0"


def test_sync_version_updates_all_release_metadata(tmp_path, monkeypatch):
    module = load_module()

    package_json = tmp_path / "package.json"
    package_json.write_text('{"name":"@wundercorp/loki","version":"0.21.4"}\n', encoding="utf-8")

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "loki-agent"\nversion = "0.21.4"\n', encoding="utf-8")

    cli_dir = tmp_path / "loki_cli"
    cli_dir.mkdir()
    cli_init = cli_dir / "__init__.py"
    cli_init.write_text('__version__ = "0.21.4"\n__release_date__ = "2026.9.11"\n', encoding="utf-8")

    desktop_dir = tmp_path / "apps" / "desktop"
    desktop_dir.mkdir(parents=True)
    desktop_package = desktop_dir / "package.json"
    desktop_package.write_text('{"name":"loki","version":"0.17.2"}\n', encoding="utf-8")

    uv_lock = tmp_path / "uv.lock"
    uv_lock.write_text('[[package]]\nname = "loki-agent"\nversion = "0.21.4"\nsource = { editable = "." }\n', encoding="utf-8")

    package_lock = tmp_path / "package-lock.json"
    package_lock.write_text(json.dumps({
        "name": "@wundercorp/loki",
        "version": "0.21.4",
        "packages": {"": {"name": "@wundercorp/loki", "version": "0.21.4"}},
    }), encoding="utf-8")

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "ROOT_PACKAGE", package_json)
    monkeypatch.setattr(module, "PYPROJECT", pyproject)
    monkeypatch.setattr(module, "CLI_INIT", cli_init)
    monkeypatch.setattr(module, "DESKTOP_PACKAGE", desktop_package)
    monkeypatch.setattr(module, "UV_LOCK", uv_lock)
    monkeypatch.setattr(module, "PACKAGE_LOCK", package_lock)

    module.sync_version("0.21.5", "2026.9.11")

    assert json.loads(package_json.read_text())["version"] == "0.21.5"
    assert 'version = "0.21.5"' in pyproject.read_text()
    assert '__version__ = "0.21.5"' in cli_init.read_text()
    assert json.loads(desktop_package.read_text())["version"] == "0.21.5"
    assert 'version = "0.21.5"' in uv_lock.read_text()
    lock = json.loads(package_lock.read_text())
    assert lock["version"] == "0.21.5"
    assert lock["packages"][""]["version"] == "0.21.5"
