#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
LEGACY_PATH_PARTS = {"ui-tui"}
TRACKED_JUNK_NAMES = {".DS_Store"}
TRACKED_JUNK_PARTS = {"__MACOSX", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "node_modules"}
TRACKED_JUNK_SUFFIXES = {".pyc", ".pyo"}
GENERATED_DIRS = {"website/build", "web/dist"}


def iter_files(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        base = Path(current)
        for name in files:
            path = base / name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            yield path, size


def tracked_paths(root: Path) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True, timeout=15
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return [p.decode("utf-8", errors="replace") for p in result.stdout.split(b"\0") if p]


def is_tracked_junk(path: str) -> bool:
    p = Path(path)
    parts = set(p.parts)
    if p.name in TRACKED_JUNK_NAMES or p.suffix in TRACKED_JUNK_SUFFIXES:
        return True
    if parts & TRACKED_JUNK_PARTS:
        return True
    normalized = p.as_posix()
    return any(normalized == generated or normalized.startswith(generated + "/") for generated in GENERATED_DIRS)


def scan(root: Path, top: int = 20) -> dict:
    files = list(iter_files(root))
    largest_files = sorted(files, key=lambda item: item[1], reverse=True)[:top]
    dir_sizes = defaultdict(int)
    for path, size in files:
        rel = path.relative_to(root)
        top_dir = rel.parts[0] if len(rel.parts) > 1 else "."
        dir_sizes[top_dir] += size
    largest_dirs = sorted(dir_sizes.items(), key=lambda item: item[1], reverse=True)[:top]
    legacy = sorted(
        str(path.relative_to(root))
        for path, _ in files
        if LEGACY_PATH_PARTS.intersection(path.relative_to(root).parts)
    )
    tracked = tracked_paths(root)
    tracked_junk = sorted(path for path in (tracked or []) if is_tracked_junk(path))
    return {
        "total_bytes": sum(size for _, size in files),
        "file_count": len(files),
        "largest_files": [(str(path.relative_to(root)), size) for path, size in largest_files],
        "largest_directories": largest_dirs,
        "legacy_paths": legacy,
        "tracked_junk": tracked_junk,
        "git_index_available": tracked is not None,
    }


def format_bytes(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = scan(root, max(1, args.top))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Repository payload: {format_bytes(report['total_bytes'])} across {report['file_count']:,} files")
        print("Largest source directories:")
        for name, size in report["largest_directories"]:
            print(f"  {format_bytes(size):>10}  {name}")
        print("Largest files:")
        for name, size in report["largest_files"]:
            print(f"  {format_bytes(size):>10}  {name}")
        if report["legacy_paths"]:
            print("Legacy path names:")
            for name in report["legacy_paths"]:
                print(f"  {name}")
        if report["tracked_junk"]:
            print("Tracked generated/cache artifacts:")
            for name in report["tracked_junk"]:
                print(f"  {name}")
        if not report["git_index_available"]:
            print("Git index unavailable: generated-artifact checks are informational only.")
    if args.check and (report["legacy_paths"] or report["tracked_junk"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
