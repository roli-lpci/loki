#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def python_test_environment() -> dict[str, str]:
    keys = (
        "PATH",
        "HOME",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "APPDATA",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
    )
    env = {key: os.environ[key] for key in keys if os.environ.get(key)}
    env.update(
        {
            "TZ": "UTC",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONHASHSEED": "0",
            "PYTHONUTF8": "1",
        }
    )
    return env


def interpreter_can_import(interpreter: str, modules: tuple[str, ...]) -> bool:
    imports = "; ".join(f"import {module}" for module in modules)
    result = subprocess.run(
        [interpreter, "-c", imports],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=python_test_environment(),
    )
    return result.returncode == 0


def quick_pytest_command(test_args: list[str]) -> list[str]:
    if interpreter_can_import(sys.executable, ("pytest",)):
        return [sys.executable, "-m", "pytest", *test_args]

    uv = shutil.which("uv")
    if uv:
        return [uv, "run", "--with", "pytest", "python", "-m", "pytest", *test_args]

    raise SystemExit(
        f"Quick validation needs pytest, but {sys.executable} cannot import it. "
        "Run `uv sync --extra dev --extra acp --frozen` or install pytest in the active environment."
    )


def python_dependency_preflight() -> None:
    required = ("pytest", "openai", "acp", "aiohttp")
    missing = [module for module in required if not interpreter_can_import(sys.executable, (module,))]
    if missing:
        names = ", ".join(missing)
        raise SystemExit(
            f"Full validation requires the declared dev/runtime dependencies; missing: {names}. "
            "Run `uv sync --extra dev --extra acp --frozen` first. The dev extra includes gateway test transports such as aiohttp."
        )


def node_dependency_preflight() -> None:
    required = [ROOT / "node_modules" / ".bin" / "eslint", ROOT / "node_modules" / ".bin" / "tsc"]
    if not all(path.exists() for path in required):
        raise SystemExit(
            "Node workspace validation requires root workspace dependencies. "
            "Run `npm install` first."
        )

    result = subprocess.run(
        ["node", "-e", "require.resolve('hermes-parser')"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise SystemExit(
            "Node dependencies are incomplete: hermes-parser is missing. "
            "Run `npm install` from the repository root before validating."
        )


def run(label: str, command: list[str], *, extra_env: dict[str, str] | None = None) -> None:
    print(f"\n=== {label} ===", flush=True)
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    subprocess.run(command, cwd=ROOT, check=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--skip-node", action="store_true")
    args = parser.parse_args()

    run("repository health", [sys.executable, "scripts/repo_health.py", "--check", "--top", "15"])
    if args.quick:
        test_args = [
            "-q",
            "tests/tools/test_file_state_registry.py",
            "tests/tools/test_file_staleness.py",
            "tests/tools/test_delegate_child_compression_cap.py",
            "tests/tools/test_delegate_safety_budgets.py",
            "tests/tools/test_subagent_worktree.py",
            "tests/agent/test_micro_compaction.py",
            "tests/agent/test_prompt_caching.py",
            "tests/agent/test_prompt_cache_boundary.py",
            "tests/agent/test_prompt_cache_scope.py",
            "tests/gateway/test_agent_cache.py::TestExtractCacheBustingConfig",
            "tests/cli/test_session_exit_usage.py",
            "tests/loki_cli/test_tui_exit_usage.py",
            "tests/loki_cli/test_api_versioning.py",
            "tests/loki_cli/test_api_contract_surface.py",
        ]
        run("critical Python regression suite", quick_pytest_command(test_args))
    else:
        python_dependency_preflight()
        run(
            "Python suite",
            ["bash", "scripts/run_tests.sh"],
            extra_env={"LOKI_TEST_PYTHON": sys.executable},
        )

    if not args.skip_node:
        node_dependency_preflight()
        if args.quick:
            run("quick Node regression suite", ["npm", "run", "check:quick"])
        else:
            run("Node workspace suite", ["npm", "run", "check"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
