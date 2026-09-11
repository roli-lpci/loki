"""Resolve LOKI_HOME for standalone skill scripts.

Skill scripts may run outside the Loki process (e.g. system Python,
nix env, CI) where ``loki_constants`` is not importable.  This module
provides the same ``get_loki_home()`` and ``display_loki_home()``
contracts as ``loki_constants`` without requiring it on ``sys.path``.

When ``loki_constants`` IS available it is used directly so that any
future enhancements (profile resolution, Docker detection, etc.) are
picked up automatically.  The fallback path replicates the core logic
from ``loki_constants.py`` using only the stdlib.

All scripts under ``google-workspace/scripts/`` should import from here
instead of duplicating the ``LOKI_HOME = Path(os.getenv(...))`` pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from loki_constants import display_loki_home as display_loki_home
    from loki_constants import get_loki_home as get_loki_home
except (ModuleNotFoundError, ImportError):

    def get_loki_home() -> Path:
        """Return the Loki home directory (default: ~/.loki).

        Mirrors ``loki_constants.get_loki_home()``."""
        val = os.environ.get("LOKI_HOME", "").strip()
        return Path(val) if val else Path.home() / ".loki"

    def display_loki_home() -> str:
        """Return a user-friendly ``~/``-shortened display string.

        Mirrors ``loki_constants.display_loki_home()``."""
        home = get_loki_home()
        try:
            return "~/" + home.relative_to(Path.home()).as_posix()
        except ValueError:
            return str(home)
