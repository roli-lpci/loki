"""Resolve LOKI_HOME for standalone skill scripts.

Skill scripts may run outside the Loki process (system Python, nix env,
CI) where ``loki_constants`` is not importable.  This module provides the
same ``get_loki_home()`` contract without requiring it on ``sys.path``.

When ``loki_constants`` IS available it is used directly so profile
resolution and any future enhancements are picked up automatically.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from loki_constants import get_loki_home as get_loki_home
except (ModuleNotFoundError, ImportError):

    def get_loki_home() -> Path:
        """Return the Loki home directory (default: ``~/.loki``)."""
        val = os.environ.get("LOKI_HOME", "").strip()
        return Path(val) if val else Path.home() / ".loki"
