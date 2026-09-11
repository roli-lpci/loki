#!/usr/bin/env python3
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOT_PACKAGE = REPO_ROOT / "package.json"
PYPROJECT = REPO_ROOT / "pyproject.toml"
CLI_INIT = REPO_ROOT / "loki_cli" / "__init__.py"
DESKTOP_PACKAGE = REPO_ROOT / "apps" / "desktop" / "package.json"
UV_LOCK = REPO_ROOT / "uv.lock"
PACKAGE_LOCK = REPO_ROOT / "package-lock.json"
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def parse_semver(value: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"expected a stable semantic version like 0.21.5, got {value!r}")
    return tuple(int(group) for group in match.groups())


def bump_semver(value: str, part: str) -> str:
    major, minor, patch = parse_semver(value)
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"unknown bump part: {part}")
    return f"{major}.{minor}.{patch}"


def choose_next_version(local: str, registry: str | None, part: str) -> str:
    local_tuple = parse_semver(local)
    if not registry:
        return local
    registry_tuple = parse_semver(registry)
    if local_tuple > registry_tuple:
        return local
    baseline = registry if registry_tuple >= local_tuple else local
    return bump_semver(baseline, part)


def replace_once(path: Path, pattern: str, replacement: str, *, flags: int = 0) -> None:
    content = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, content, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"could not update version in {path.relative_to(REPO_ROOT)}")
    path.write_text(updated, encoding="utf-8")


def sync_version(version: str, release_date: str) -> list[Path]:
    parse_semver(version)
    changed: list[Path] = []

    package = json.loads(ROOT_PACKAGE.read_text(encoding="utf-8"))
    if package.get("version") != version:
        package["version"] = version
        ROOT_PACKAGE.write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed.append(ROOT_PACKAGE)

    pyproject_before = PYPROJECT.read_text(encoding="utf-8")
    pyproject_after, count = re.subn(
        r'(?ms)(^\[project\]\s*.*?^version\s*=\s*)"[^"]+"',
        rf'\g<1>"{version}"',
        pyproject_before,
        count=1,
    )
    if count != 1:
        raise RuntimeError("could not locate [project] version in pyproject.toml")
    if pyproject_after != pyproject_before:
        PYPROJECT.write_text(pyproject_after, encoding="utf-8")
        changed.append(PYPROJECT)

    cli_before = CLI_INIT.read_text(encoding="utf-8")
    cli_after, version_count = re.subn(
        r'^__version__\s*=\s*"[^"]+"',
        f'__version__ = "{version}"',
        cli_before,
        count=1,
        flags=re.MULTILINE,
    )
    cli_after, date_count = re.subn(
        r'^__release_date__\s*=\s*"[^"]+"',
        f'__release_date__ = "{release_date}"',
        cli_after,
        count=1,
        flags=re.MULTILINE,
    )
    if version_count != 1 or date_count != 1:
        raise RuntimeError("could not update loki_cli version metadata")
    if cli_after != cli_before:
        CLI_INIT.write_text(cli_after, encoding="utf-8")
        changed.append(CLI_INIT)

    if DESKTOP_PACKAGE.exists():
        desktop = json.loads(DESKTOP_PACKAGE.read_text(encoding="utf-8"))
        if desktop.get("version") != version:
            desktop["version"] = version
            DESKTOP_PACKAGE.write_text(json.dumps(desktop, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            changed.append(DESKTOP_PACKAGE)

    if UV_LOCK.exists():
        lock_before = UV_LOCK.read_text(encoding="utf-8")
        lock_after, count = re.subn(
            r'(\[\[package\]\]\s*\nname = "loki-agent"\s*\nversion = ")([^"]+)(")',
            rf'\g<1>{version}\g<3>',
            lock_before,
            count=1,
        )
        if count != 1:
            raise RuntimeError("could not locate loki-agent package entry in uv.lock")
        if lock_after != lock_before:
            UV_LOCK.write_text(lock_after, encoding="utf-8")
            changed.append(UV_LOCK)

    if PACKAGE_LOCK.exists():
        lock = json.loads(PACKAGE_LOCK.read_text(encoding="utf-8"))
        lock_changed = False
        if lock.get("version") != version:
            lock["version"] = version
            lock_changed = True
        root_package = lock.get("packages", {}).get("")
        if isinstance(root_package, dict) and root_package.get("version") != version:
            root_package["version"] = version
            lock_changed = True
        if lock_changed:
            PACKAGE_LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            changed.append(PACKAGE_LOCK)

    return changed


def read_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    package = json.loads(ROOT_PACKAGE.read_text(encoding="utf-8"))
    versions["package.json"] = str(package.get("version", ""))

    pyproject = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'(?ms)^\[project\]\s*.*?^version\s*=\s*"([^"]+)"', pyproject)
    versions["pyproject.toml"] = match.group(1) if match else ""

    cli = CLI_INIT.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', cli, flags=re.MULTILINE)
    versions["loki_cli/__init__.py"] = match.group(1) if match else ""

    if DESKTOP_PACKAGE.exists():
        desktop = json.loads(DESKTOP_PACKAGE.read_text(encoding="utf-8"))
        versions["apps/desktop/package.json"] = str(desktop.get("version", ""))

    if UV_LOCK.exists():
        uv_lock = UV_LOCK.read_text(encoding="utf-8")
        match = re.search(r'\[\[package\]\]\s*\nname = "loki-agent"\s*\nversion = "([^"]+)"', uv_lock)
        versions["uv.lock"] = match.group(1) if match else ""

    if PACKAGE_LOCK.exists():
        package_lock = json.loads(PACKAGE_LOCK.read_text(encoding="utf-8"))
        versions["package-lock.json"] = str(package_lock.get("packages", {}).get("", {}).get("version", ""))

    return versions


def verify_versions() -> int:
    versions = read_versions()
    expected = versions["package.json"]
    failures = [f"{path}: {version or '<missing>'} != {expected}" for path, version in versions.items() if version != expected]
    if failures:
        print("version synchronization failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"version synchronization passed for {expected} across {len(versions)} metadata files.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize Loki release versions")
    subparsers = parser.add_subparsers(dest="command", required=True)

    next_parser = subparsers.add_parser("next", help="choose a publishable next version")
    next_parser.add_argument("--local", required=True)
    next_parser.add_argument("--registry", default="")
    next_parser.add_argument("--bump", choices=["patch", "minor", "major"], default="patch")

    set_parser = subparsers.add_parser("set", help="write a version to all release metadata")
    set_parser.add_argument("version")
    set_parser.add_argument("--date", default=f"{date.today().year}.{date.today().month}.{date.today().day}")

    subparsers.add_parser("verify", help="verify all release metadata has the same version")

    args = parser.parse_args()
    try:
        if args.command == "next":
            print(choose_next_version(args.local, args.registry or None, args.bump))
            return 0
        if args.command == "set":
            changed = sync_version(args.version, args.date)
            for path in changed:
                print(path.relative_to(REPO_ROOT))
            return 0
        if args.command == "verify":
            return verify_versions()
    except (ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"version error: {error}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
