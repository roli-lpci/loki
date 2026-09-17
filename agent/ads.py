"""Dormant, opt-in advertisement presentation layer.

Ads are disabled by default and require explicit user consent plus two independent
feature gates.  This module does not fetch ads, target users, inspect conversation
content, or write ad copy into model history.  It only knows how to attach
preconfigured text copy to the outward turn result, clearly labelled as sponsored
content.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _ads_config() -> dict[str, Any]:
    try:
        from loki_cli.config import load_config
        raw = (load_config() or {}).get("ads") or {}
        return raw if isinstance(raw, dict) else {}
    except Exception:
        logger.debug("Could not load advertisement config", exc_info=True)
        return {}


def _text_copy(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        text = str(item.get("text") or "").strip()
        url = str(item.get("url") or "").strip()
        sponsor = str(item.get("sponsor") or "").strip()
        if sponsor and text:
            text = f"{sponsor}: {text}"
        if url and text:
            text = f"{text} — {url}"
        return text
    return ""


def maybe_attach_text_ad(agent: Any, result: dict[str, Any]) -> dict[str, Any]:
    """Append a configured text ad to a successful outward response when explicitly opted in.

    ``result['messages']`` is never touched, so sponsored copy cannot become prompt/history input.
    The same result object is returned for compatibility with existing turn wrappers.
    """
    if not isinstance(result, dict) or result.get("completed") is not True:
        return result
    if getattr(agent, "_parent_session_id", None):
        return result

    cfg = _ads_config()
    text_cfg = cfg.get("text") if isinstance(cfg.get("text"), dict) else {}
    if not bool(cfg.get("user_opt_in", False)):
        return result
    if not bool(cfg.get("enabled", False)) or not bool(text_cfg.get("enabled", False)):
        return result

    raw_messages = text_cfg.get("messages")
    if not isinstance(raw_messages, list):
        return result
    messages = [copy for item in raw_messages if (copy := _text_copy(item))]
    if not messages:
        return result

    try:
        every_n_turns = max(1, int(text_cfg.get("every_n_turns", 6) or 6))
    except (TypeError, ValueError):
        every_n_turns = 6
    completed_turns = int(getattr(agent, "_ad_completed_turns", 0) or 0) + 1
    agent._ad_completed_turns = completed_turns
    if completed_turns % every_n_turns != 0:
        return result

    index = ((completed_turns // every_n_turns) - 1) % len(messages)
    copy = messages[index]
    final_response = result.get("final_response")
    if not isinstance(final_response, str) or not final_response.strip():
        return result

    # Deliberately separate from assistant prose and label it unambiguously.  Surfaces may render
    # ``display_text`` beneath the assistant response as a separate sponsored item; the assistant
    # answer itself remains byte-for-byte unchanged.
    result["advertisement"] = {
        "format": "text",
        "label": "Sponsored",
        "text": copy,
        "display_text": f"Sponsored\n{copy}",
    }
    return result
