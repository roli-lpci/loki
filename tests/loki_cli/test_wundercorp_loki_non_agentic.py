"""Tests for the WunderCorp-Loki-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"loki"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``loki-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "loki" tag namespace.

``is_wundercorp_loki_non_agentic`` should only match the actual WunderCorp, Inc.
Loki-3 / Loki-4 chat family.
"""

from __future__ import annotations

import pytest

from loki_cli.model_switch import (
    _LOKI_MODEL_WARNING,
    _check_loki_model_warning,
    is_wundercorp_loki_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "WunderCorp/Loki-3-Llama-3.1-70B",
        "WunderCorp/Loki-3-Llama-3.1-405B",
        "loki-3",
        "Loki-3",
        "loki-4",
        "loki-4-405b",
        "loki_4_70b",
        "openrouter/loki3:70b",
        "openrouter/wundercorp/loki-4-405b",
        "WunderCorp/Loki3",
        "loki-3.1",
    ],
)
def test_matches_real_wundercorp_loki_chat_models(model_name: str) -> None:
    assert is_wundercorp_loki_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as WunderCorp Loki 3/4"
    )
    assert _check_loki_model_warning(model_name) == _LOKI_MODEL_WARNING


