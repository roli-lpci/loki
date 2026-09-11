from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def prepare_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "loki_cli").mkdir()
    (repo / "apps" / "desktop").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "deploy.sh", repo / "scripts" / "deploy.sh")
    shutil.copy(ROOT / "scripts" / "sync_version.py", repo / "scripts" / "sync_version.py")
    (repo / "package.json").write_text(json.dumps({"name": "@wundercorp/loki", "version": "0.21.4"}), encoding="utf-8")
    (repo / "pyproject.toml").write_text('[project]\nname = "loki-agent"\nversion = "0.21.4"\n', encoding="utf-8")
    (repo / "loki_cli" / "__init__.py").write_text('__version__ = "0.21.4"\n__release_date__ = "2026.9.11"\n', encoding="utf-8")
    (repo / "apps" / "desktop" / "package.json").write_text(json.dumps({"name": "loki", "version": "0.21.4"}), encoding="utf-8")
    (repo / "uv.lock").write_text('[[package]]\nname = "loki-agent"\nversion = "0.21.4"\nsource = { editable = "." }\n', encoding="utf-8")
    return repo


def make_fake_npm(tmp_path: Path, registry_version: str = "0.21.4") -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "npm"
    script.write_text(
        f'''#!/usr/bin/env bash
set -e
marker="{tmp_path / 'published'}"
if [ "$1" = "view" ]; then
  target="$2"
  if [ "$target" = "@wundercorp/loki" ]; then
    printf '%s\\n' "{registry_version}"
    exit 0
  fi
  if [ "$target" = "@wundercorp/loki@0.21.5" ]; then
    if [ -f "$marker" ]; then
      printf '%s\\n' '0.21.5'
      exit 0
    fi
    exit 1
  fi
  exit 1
fi
if [ "$1" = "ping" ]; then exit 0; fi
if [ "$1" = "whoami" ]; then printf '%s\\n' test-user; exit 0; fi
if [ "$1" = "run" ] && [ "$2" = "release:check" ]; then exit 0; fi
if [ "$1" = "publish" ]; then touch "$marker"; exit 0; fi
printf 'unexpected npm command: %s\\n' "$*" >&2
exit 1
''',
        encoding="utf-8",
    )
    script.chmod(0o755)
    return bin_dir


def test_deploy_auto_bumps_published_version_and_publishes(tmp_path):
    repo = prepare_repo(tmp_path)
    fake_bin = make_fake_npm(tmp_path)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", "scripts/deploy.sh", "--npm-only", "--yes", "--no-version-git"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Version plan: @wundercorp/loki@0.21.4 -> 0.21.5" in result.stdout
    assert "npm registry confirmed @wundercorp/loki@0.21.5." in result.stdout
    assert json.loads((repo / "package.json").read_text())["version"] == "0.21.5"
    assert 'version = "0.21.5"' in (repo / "pyproject.toml").read_text()
    assert '__version__ = "0.21.5"' in (repo / "loki_cli" / "__init__.py").read_text()
    assert json.loads((repo / "apps" / "desktop" / "package.json").read_text())["version"] == "0.21.5"
    assert 'version = "0.21.5"' in (repo / "uv.lock").read_text()


def test_deploy_dry_run_plans_bump_without_mutating_files(tmp_path):
    repo = prepare_repo(tmp_path)
    fake_bin = make_fake_npm(tmp_path)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", "scripts/deploy.sh", "--npm-only", "--dry-run", "--yes"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "would synchronize release metadata to 0.21.5" in result.stdout
    assert "would publish @wundercorp/loki@0.21.5" in result.stdout
    assert json.loads((repo / "package.json").read_text())["version"] == "0.21.4"


def test_no_auto_version_refuses_to_skip_existing_release(tmp_path):
    repo = prepare_repo(tmp_path)
    fake_bin = make_fake_npm(tmp_path)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", "scripts/deploy.sh", "--npm-only", "--yes", "--no-auto-version", "--no-version-git"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "already published and auto-versioning is disabled" in result.stderr


def test_deploy_commits_and_pushes_version_before_publish(tmp_path):
    repo = prepare_repo(tmp_path)
    fake_bin = make_fake_npm(tmp_path)
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Release Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "release@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repo, check=True, capture_output=True)

    result = subprocess.run(
        ["bash", "scripts/deploy.sh", "--npm-only", "--yes"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "chore: bump version to v0.21.5" in result.stdout
    assert "Pushing release source on main before npm publish" in result.stdout
    remote_package = subprocess.run(
        ["git", f"--git-dir={remote}", "show", "main:package.json"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(remote_package.stdout)["version"] == "0.21.5"
