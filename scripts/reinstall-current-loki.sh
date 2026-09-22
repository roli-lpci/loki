#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOKI_BIN="$(command -v loki || true)"
if [[ -z "$LOKI_BIN" ]]; then
  echo "ERROR: loki is not currently on PATH."
  echo "Activate the environment you normally use for Loki, then rerun this script."
  exit 1
fi

FIRST_LINE="$(head -n 1 "$LOKI_BIN" 2>/dev/null || true)"
PYTHON_BIN=""
if [[ "$FIRST_LINE" == '#!'* ]]; then
  CANDIDATE="${FIRST_LINE#\#!}"
  if [[ -x "$CANDIDATE" ]] && "$CANDIDATE" -c 'import sys' >/dev/null 2>&1; then
    PYTHON_BIN="$CANDIDATE"
  fi
fi

if [[ -z "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [[ -z "$PYTHON_BIN" ]]; then
  echo "ERROR: Could not determine the Python interpreter used by Loki."
  exit 1
fi

echo "Loki executable: $LOKI_BIN"
echo "Python:          $PYTHON_BIN"
echo "Source tree:     $ROOT"

if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$PYTHON_BIN" --no-deps -e "$ROOT"
else
  "$PYTHON_BIN" -m pip install --no-deps -e "$ROOT"
fi

"$PYTHON_BIN" - "$ROOT" <<'PY'
from pathlib import Path
import inspect
import sys

expected_root = Path(sys.argv[1]).resolve()

import loki_cli.tools_config as tools_config
import loki_cli.go_workflows as go_workflows
import loki_cli.cli_commands_mixin as cli_commands_mixin
import model_tools

loaded = Path(tools_config.__file__).resolve()
print(f"Loaded loki_cli from: {loaded}")

if expected_root not in loaded.parents:
    raise SystemExit(
        "ERROR: Loki is still importing a different source tree. "
        f"Expected under {expected_root}, got {loaded}"
    )

keys = {row[0] for row in tools_config.CONFIGURABLE_TOOLSETS}
if "link-wallet" not in keys:
    raise SystemExit("ERROR: link-wallet is missing from CONFIGURABLE_TOOLSETS")

shopping = go_workflows.resolve_workflow("shopping")
if shopping is None:
    raise SystemExit("ERROR: shopping workflow is missing")

required_toolsets = set(shopping.toolsets)
if not {"terminal", "browser", "link-wallet"}.issubset(required_toolsets):
    raise SystemExit(
        "ERROR: /go shopping does not require terminal + browser + link-wallet: "
        f"{shopping.toolsets}"
    )

required_runtime = set(shopping.required_runtime_tools)
expected_runtime = {
    "browser_exec",
    "link_wallet_status",
    "link_spend_create",
    "link_spend_request_approval",
    "link_spend_wait",
    "link_checkout_fill",
}
if not expected_runtime.issubset(required_runtime):
    raise SystemExit(
        "ERROR: shopping runtime verification is incomplete: "
        f"{shopping.required_runtime_tools}"
    )

source = inspect.getsource(cli_commands_mixin.CLICommandsMixin._activate_go_workflow)
if "did not produce the required runtime tools" not in source:
    raise SystemExit("ERROR: /go runtime fail-closed check is missing")

browser_rewriter_source = inspect.getsource(model_tools._rewrite_browser_exec)
if "process_manage" not in browser_rewriter_source:
    raise SystemExit("ERROR: Browser Use terminal-toolset authority fix is missing")

print("OK: link-wallet is configurable")
print("OK: /go shopping requires terminal, browser, and link-wallet")
print("OK: /go shopping verifies model-visible browser + Link tools")
print("OK: Browser Use recognizes terminal-toolset authority")
print("Reinstall/self-check complete. Restart Loki before testing /go shopping.")
PY
