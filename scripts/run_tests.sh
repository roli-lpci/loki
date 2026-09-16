#!/usr/bin/env bash
# Canonical test runner for loki-agent. Run this instead of calling
# `pytest` directly to guarantee your local run matches CI behavior.
#
# What this script enforces:
#   * Per-file isolation via scripts/run_tests_parallel.py — each test
#     file runs in its own freshly-spawned `python -m pytest <file>`
#     subprocess. No xdist, no shared workers, no module-level leakage
#     between files.
#   * TZ=UTC, LANG=C.UTF-8, PYTHONHASHSEED=0 (deterministic)
#   * Env vars blanked (conftest.py also does this, but this
#     is belt-and-suspenders for anyone running pytest outside our
#     conftest path — e.g. on a single file)
#   * Proper venv activation (probes .venv, venv, then ~/.loki/...)
#
# Usage:
#   scripts/run_tests.sh                            # full suite
#   scripts/run_tests.sh -j 4                       # cap parallelism
#   scripts/run_tests.sh tests/agent/               # discover only here
#   scripts/run_tests.sh tests/agent/ tests/acp/    # multiple roots
#   scripts/run_tests.sh tests/foo.py               # single file
#   scripts/run_tests.sh tests/foo.py -q            # path + bare pytest flag
#   scripts/run_tests.sh tests/foo.py -v --tb=long  # bare flags "just work"
#   scripts/run_tests.sh -k 'pattern'               # value flags pass through too
#   scripts/run_tests.sh tests/foo.py -- --tb=long  # explicit '--' still works
#
# Bare pytest flags (anything starting with '-' that isn't one of this
# runner's own options: -j/--jobs, --paths, --slice, --file-timeout, etc.)
# are forwarded to each per-file pytest invocation automatically — no '--'
# separator required. The explicit '--' form still works and stacks with
# bare flags. Positional path arguments override the default discovery
# root (tests/).

set -euo pipefail

# ── Locate repo root ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Locate python ───────────────────────────────────────────────────────────
_python_has_pytest() {
  local candidate="$1"
  [ -x "$candidate" ] || return 1
  env -i \
    PATH="$PATH" \
    HOME="$HOME" \
    TZ=UTC \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONHASHSEED=0 \
    PYTHONUTF8=1 \
    "$candidate" -c 'import pytest' >/dev/null 2>&1
}

PYTHON=""
SKIPPED_PYTHONS=""

if [ -n "${LOKI_TEST_PYTHON:-}" ]; then
  if _python_has_pytest "$LOKI_TEST_PYTHON"; then
    PYTHON="$LOKI_TEST_PYTHON"
    echo "▶ using explicitly selected test interpreter: $PYTHON"
  else
    echo "error: LOKI_TEST_PYTHON does not provide pytest in the hermetic test environment: $LOKI_TEST_PYTHON" >&2
    exit 1
  fi
fi

if [ -z "$PYTHON" ]; then
  for candidate in \
    "$REPO_ROOT/.venv/bin/python" \
    "$REPO_ROOT/venv/bin/python" \
    "$HOME/.loki/loki-agent/venv/bin/python" \
    "$REPO_ROOT/.venv/Scripts/python.exe" \
    "$REPO_ROOT/venv/Scripts/python.exe" \
    "$HOME/.loki/loki-agent/venv/Scripts/python.exe"; do
    if [ -e "$candidate" ]; then
      if _python_has_pytest "$candidate"; then
        PYTHON="$candidate"
        break
      fi
      SKIPPED_PYTHONS="$SKIPPED_PYTHONS $candidate"
    fi
  done
fi

if [ -z "$PYTHON" ] && [ -n "${LOKI_PYTHON:-}" ] && _python_has_pytest "$LOKI_PYTHON"; then
  PYTHON="$LOKI_PYTHON"
  echo "▶ using Nix/dev interpreter via LOKI_PYTHON: $PYTHON"
fi

if [ -z "$PYTHON" ]; then
  for command_name in python3 python; do
    candidate="$(command -v "$command_name" 2>/dev/null || true)"
    if [ -n "$candidate" ] && _python_has_pytest "$candidate"; then
      PYTHON="$candidate"
      echo "▶ using pytest-capable PATH interpreter: $PYTHON"
      break
    fi
  done
fi

if [ -n "$SKIPPED_PYTHONS" ]; then
  for skipped in $SKIPPED_PYTHONS; do
    echo "▶ skipping interpreter without hermetic pytest: $skipped" >&2
  done
fi

if [ -z "$PYTHON" ]; then
  echo "error: no Python interpreter with pytest is available in the hermetic test environment." >&2
  echo "       Run 'uv sync --extra dev --extra acp --frozen' (dev includes gateway test transports such as aiohttp) or set LOKI_TEST_PYTHON to a fully provisioned test interpreter." >&2
  exit 1
fi

# ── Live-gateway plugin (computed before we drop env) ───────────────────────
EXTRA_PYTHONPATH=""
EXTRA_PYTEST_PLUGINS=""
if [ -f "$HOME/.loki/pytest_live_guard.py" ]; then
  EXTRA_PYTHONPATH="$HOME/.loki"
  EXTRA_PYTEST_PLUGINS="pytest_live_guard"
fi


# ── Windows location variables (computed before we drop env) ───────────────
# `env -i` forwards HOME, which is enough on POSIX. Native Windows CPython
# resolves Path.home() from USERPROFILE (or HOMEDRIVE+HOMEPATH), stdlib
# platform paths come from LOCALAPPDATA/APPDATA, ssl/sockets need SYSTEMROOT,
# and tempfile needs TEMP/TMP. Dropping them breaks collection on native
# Windows (issues #67385, #70813). These are location variables, not
# credentials, so forwarding them keeps the isolation intent intact. Each is
# only forwarded when actually set, so POSIX runs are byte-for-byte unchanged.
WIN_ENV=()
for _win_var in USERPROFILE HOMEDRIVE HOMEPATH LOCALAPPDATA APPDATA SYSTEMROOT TEMP TMP; do
  if [ -n "${!_win_var:-}" ]; then
    WIN_ENV+=("$_win_var=${!_win_var}")
  fi
done

# ── Test-runner knobs (computed before we drop env) ────────────────────────
# The runner's own documented environment knobs must survive the hermetic
# `env -i` below, or they are silent no-ops for anyone invoking this script:
#
#   * LOKI_TEST_WORKERS / PATHS / FILE_TIMEOUT / FILE_RETRIES / SLICE are
#     read by run_tests_parallel.py at argparse-default time — inside the
#     stripped environment.
#   * LOKI_TEST_IMAGE is read by tests/docker/conftest.py to skip its
#     session-scoped `docker build`. CI's docker.yml sets it to the image
#     the build step just loaded; stripping it made every per-file pytest
#     subprocess rebuild the 5GB image from a cold builder cache instead
#     (~4 min per worker per run, and the rebuilt image lacked the
#     LOKI_GIT_SHA build-arg the workflow bakes in).
#
# These are test-infrastructure knobs, not credentials — same class as the
# LOKI_RUN_SLOW_PET_TESTS / LOKI_E2E_BROWSER opt-ins already forwarded.
# Keep this an explicit allowlist (no LOKI_TEST_* glob) so the "no
# credential can leak" property stays auditable at a glance.
TEST_ENV=()
for _test_var in LOKI_TEST_IMAGE LOKI_TEST_WORKERS LOKI_TEST_PATHS \
  LOKI_TEST_FILE_TIMEOUT LOKI_TEST_FILE_RETRIES LOKI_TEST_SLICE; do
  if [ -n "${!_test_var:-}" ]; then
    TEST_ENV+=("$_test_var=${!_test_var}")
  fi
done

# ── Run in hermetic env ──────────────────────────────────────────────────────
# env -i: start with empty environment, opt-in only what we need.
# No credential var can leak — you'd have to explicitly add it here.
echo "▶ running per-file parallel test suite via run_tests_parallel.py"
echo "  (TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0; clean env)"

cd "$REPO_ROOT"

# ── Pre-compile .pyc bytecode cache ─────────────────────────────────────────
# Each test file runs in its own subprocess via run_tests_parallel.py.
# Pre-building the bytecode cache once here (instead of each subprocess
# compiling on first import) avoids redundant work across ~2000 processes.
# Uses git to list tracked .py files (skips venv, node_modules, etc).
echo "▶ pre-compiling bytecode cache"
if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$REPO_ROOT" ls-files -z -- '*.py' | xargs -0 "$PYTHON" -m compileall -q -j 0 -- >/dev/null 2>&1 || true
else
  echo "  (git index unavailable; skipping bytecode precompile)"
fi

echo "▶ launching test runner"
exec env -i \
  PATH="$PATH" \
  HOME="$HOME" \
  ${WIN_ENV[@]+"${WIN_ENV[@]}"} \
  ${TEST_ENV[@]+"${TEST_ENV[@]}"} \
  TZ=UTC \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  PYTHONHASHSEED=0 \
  PYTHONUTF8=1 \
  ${LOKI_RUN_SLOW_PET_TESTS:+LOKI_RUN_SLOW_PET_TESTS="$LOKI_RUN_SLOW_PET_TESTS"} \
  ${LOKI_E2E_BROWSER:+LOKI_E2E_BROWSER="$LOKI_E2E_BROWSER"} \
  ${EXTRA_PYTHONPATH:+PYTHONPATH="$EXTRA_PYTHONPATH"} \
  ${EXTRA_PYTEST_PLUGINS:+PYTEST_PLUGINS="$EXTRA_PYTEST_PLUGINS"} \
  "$PYTHON" "$SCRIPT_DIR/run_tests_parallel.py" "$@"
