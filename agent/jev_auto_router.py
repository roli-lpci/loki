"""Jev Auto: one-shot, same-gateway model routing for new Loki sessions.

The router is intentionally *session sticky*.  It runs before the first system prompt
is assembled, asks TypeSafe Jev to choose from a bounded catalog exposed by the
already-selected provider, then leaves that route alone for the rest of the session.
That preserves Loki's provider prompt-cache prefix and ensures Jev can never move a
user to a different gateway or credential boundary.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Iterable

from agent.typesafe_client import TypeSafeRequestError, configured_typesafe_key, request_system_one

logger = logging.getLogger(__name__)

_ROUTE_KEY = "jev_auto_route"
_DEFAULT_MAX_CANDIDATES = 12
_MAX_TASK_CHARS = 6000
_VALID_COST_BIASES = {"economy", "balanced", "quality"}


@dataclass(frozen=True)
class JevAutoCandidate:
    model: str
    name: str = ""
    family: str = ""
    reasoning: bool | None = None
    tools: bool | None = None
    vision: bool | None = None
    context_window: int = 0
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None

    @property
    def blended_cost(self) -> float | None:
        inp, out = self.input_cost_per_million, self.output_cost_per_million
        if inp is None and out is None:
            return None
        # Agent traffic is input-heavy; use a stable heuristic only for shortlist construction.
        return 0.7 * float(inp or 0.0) + 0.3 * float(out or 0.0)

    def description(self) -> str:
        capabilities: list[str] = []
        if self.tools is True:
            capabilities.append("tools")
        elif self.tools is False:
            capabilities.append("no-tools")
        if self.reasoning is True:
            capabilities.append("reasoning")
        if self.vision is True:
            capabilities.append("vision")
        elif self.vision is False:
            capabilities.append("no-vision")
        if not capabilities:
            capabilities.append("capabilities-unknown")

        identity = self.name.strip() if self.name.strip() and self.name.strip() != self.model else ""
        if self.family.strip():
            identity = f"{identity}; family={self.family.strip()}" if identity else f"family={self.family.strip()}"
        pieces = ([identity] if identity else []) + [", ".join(capabilities)]
        if self.context_window > 0:
            pieces.append(f"context={self.context_window:,} tokens")
        if self.input_cost_per_million is not None or self.output_cost_per_million is not None:
            inp = "?" if self.input_cost_per_million is None else f"${self.input_cost_per_million:.4g}/M input"
            out = "?" if self.output_cost_per_million is None else f"${self.output_cost_per_million:.4g}/M output"
            pieces.append(f"cost={inp}, {out}")
        else:
            pieces.append("cost=unknown")
        return "; ".join(pieces)


def _routing_config() -> dict[str, Any]:
    try:
        from loki_cli.config import load_config
        raw = (load_config() or {}).get("smart_model_routing") or {}
        return raw if isinstance(raw, dict) else {}
    except Exception:
        logger.debug("Jev Auto could not load routing config", exc_info=True)
        return {}


def _task_text_and_vision(user_message: Any) -> tuple[str, bool]:
    """Return a bounded first-task representation and whether it visibly carries image input."""
    vision = False
    text_parts: list[str] = []

    def visit(value: Any) -> None:
        nonlocal vision
        if isinstance(value, str):
            if value.strip():
                text_parts.append(value.strip())
            return
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        kind = str(value.get("type") or "").lower()
        if kind in {"image", "image_url", "input_image", "image_file"} or any(
            key in value for key in ("image_url", "image_data")
        ):
            vision = True
        for key in ("text", "content", "prompt", "message"):
            if key in value:
                visit(value[key])

    visit(user_message)
    text = "\n".join(text_parts).strip()
    if not text:
        try:
            text = json.dumps(user_message, ensure_ascii=False, default=str)
        except Exception:
            text = str(user_message)
    return text[:_MAX_TASK_CHARS], vision


def _float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _live_price_per_million(row: dict[str, Any] | None, key: str) -> float | None:
    if not isinstance(row, dict):
        return None
    value = _float_or_none(row.get(key))
    return None if value is None else value * 1_000_000.0


def _candidate(model: str, provider: str, pricing: dict[str, dict[str, Any]]) -> JevAutoCandidate | None:
    try:
        from agent.models_dev import get_model_info
        info = get_model_info(provider, model, allow_network=False)
    except Exception:
        info = None

    # Known non-tool models are unsafe for the main agent loop. Unknown models remain eligible
    # because custom/OpenAI-compatible gateways often have no models.dev metadata at all.
    if info is not None and info.tool_call is False:
        return None

    price_row = pricing.get(model) if isinstance(pricing, dict) else None
    live_in = _live_price_per_million(price_row, "prompt")
    live_out = _live_price_per_million(price_row, "completion")
    mdev_in = float(info.cost_input) if info is not None and info.cost_input > 0 else None
    mdev_out = float(info.cost_output) if info is not None and info.cost_output > 0 else None
    return JevAutoCandidate(
        model=model,
        name=(str(info.name) if info is not None else ""),
        family=(str(info.family) if info is not None else ""),
        reasoning=(bool(info.reasoning) if info is not None else None),
        tools=(bool(info.tool_call) if info is not None else None),
        vision=(bool(info.supports_vision()) if info is not None else None),
        context_window=(int(info.context_window) if info is not None else 0),
        input_cost_per_million=live_in if live_in is not None else mdev_in,
        output_cost_per_million=live_out if live_out is not None else mdev_out,
    )


def _append_unique(target: list[JevAutoCandidate], items: Iterable[JevAutoCandidate], limit: int) -> None:
    seen = {item.model for item in target}
    for item in items:
        if len(target) >= limit:
            return
        if item.model not in seen:
            target.append(item)
            seen.add(item.model)


def discover_candidates(
    provider: str,
    current_model: str,
    *,
    max_candidates: int = _DEFAULT_MAX_CANDIDATES,
    requires_vision: bool = False,
) -> list[JevAutoCandidate]:
    """Build a bounded, capability-aware shortlist from the active gateway's own catalog."""
    max_candidates = max(2, min(24, int(max_candidates or _DEFAULT_MAX_CANDIDATES)))
    try:
        from loki_cli.models import cached_provider_model_ids
        model_ids = cached_provider_model_ids(provider)
    except Exception:
        logger.debug("Jev Auto provider model discovery failed", exc_info=True)
        model_ids = []

    ordered_ids: list[str] = []
    for model_id in [current_model, *model_ids]:
        mid = str(model_id or "").strip()
        if mid and mid not in ordered_ids:
            ordered_ids.append(mid)

    try:
        from loki_cli.models_pricing import get_pricing_for_provider
        pricing = get_pricing_for_provider(provider, cached_only=True) or {}
    except Exception:
        pricing = {}

    candidates = [item for mid in ordered_ids if (item := _candidate(mid, provider, pricing)) is not None]
    if requires_vision:
        known_vision = [item for item in candidates if item.vision is True]
        if known_vision:
            # Preserve current as a deterministic fallback, but don't let Jev select a model known
            # to reject the attachment merely because it is cheaper.
            candidates = [
                item for item in candidates
                if item.vision is True or item.model == current_model and item.vision is not False
            ]
            if not any(item.model == current_model for item in candidates):
                current = _candidate(current_model, provider, pricing)
                if current is not None and current.vision is not False:
                    candidates.insert(0, current)

    if len(candidates) <= max_candidates:
        return candidates

    by_cost = sorted(
        (item for item in candidates if item.blended_cost is not None),
        key=lambda item: (item.blended_cost, item.model),
    )
    by_context = sorted(candidates, key=lambda item: (item.context_window, item.model), reverse=True)
    reasoning = sorted(
        (item for item in candidates if item.reasoning is True),
        key=lambda item: (item.blended_cost is None, item.blended_cost or float("inf"), item.model),
    )
    vision = sorted(
        (item for item in candidates if item.vision is True),
        key=lambda item: (item.blended_cost is None, item.blended_cost or float("inf"), item.model),
    )
    current = [item for item in candidates if item.model == current_model]

    shortlist: list[JevAutoCandidate] = []
    _append_unique(shortlist, current, max_candidates)
    _append_unique(shortlist, by_cost[:5], max_candidates)
    _append_unique(shortlist, reasoning[:3], max_candidates)
    if requires_vision:
        _append_unique(shortlist, vision[:3], max_candidates)
    _append_unique(shortlist, by_context[:3], max_candidates)
    # Fill remaining slots in gateway catalog order, which keeps this useful for gateways with no
    # external metadata/pricing rather than silently collapsing to the current model only.
    _append_unique(shortlist, candidates, max_candidates)
    return shortlist


def _extract_route_answer(payload: dict[str, Any]) -> tuple[str, float]:
    answer = ((payload.get("answers") or {}).get("route_model") or {}) if isinstance(payload, dict) else {}
    if not isinstance(answer, dict):
        return "", 0.0
    choice = str(answer.get("choice") or "").strip()
    confidence = _float_or_none(answer.get("confidence"))
    probabilities = answer.get("probabilities") or {}
    probability = _float_or_none(probabilities.get(choice)) if isinstance(probabilities, dict) and choice else None
    return choice, float(confidence if confidence is not None else probability or 0.0)


def choose_model(
    *,
    task: str,
    provider: str,
    current_model: str,
    candidates: list[JevAutoCandidate],
    cost_bias: str = "balanced",
) -> tuple[str, float]:
    """Ask Jev to select the least-cost sufficiently capable model from *candidates*."""
    if len(candidates) < 2:
        return current_model, 0.0
    bias = str(cost_bias or "balanced").lower()
    if bias not in _VALID_COST_BIASES:
        bias = "balanced"
    criteria = {candidate.model: candidate.description() for candidate in candidates}
    policy = {
        "economy": "Aggressively prefer the cheapest model that is still sufficiently capable.",
        "balanced": "Prefer lower cost when capability is sufficient; pay more only for material task needs.",
        "quality": "Prefer capability and reliability, using cost as the tie-breaker among sufficient models.",
    }[bias]
    response = request_system_one(
        state={
            "task": task,
            "gateway": provider,
            "current_model": current_model,
            "routing_goal": "Minimize inference cost without selecting a model too weak for the task.",
        },
        questions={
            "route_model": {
                "type": "choice",
                "instructions": (
                    "Choose exactly one model from the provided criteria for this agent task. "
                    "The model must be sufficiently capable for the task, including tools, reasoning, "
                    "context, or vision when those are relevant. " + policy
                ),
                "criteria": criteria,
            }
        },
    )
    choice, confidence = _extract_route_answer(response)
    allowed = {candidate.model for candidate in candidates}
    return (choice if choice in allowed else current_model), confidence


def _is_new_root_session(agent: Any, conversation_history: Any) -> bool:
    if getattr(agent, "_parent_session_id", None):
        return False
    if conversation_history:
        return False
    if getattr(agent, "_jev_auto_route_attempted", False):
        return False

    session_db = getattr(agent, "_session_db", None)
    session_id = str(getattr(agent, "session_id", "") or "")
    if session_db is None or not session_id:
        return True
    try:
        row = session_db.get_session(session_id)
    except Exception:
        logger.debug("Jev Auto could not inspect session row", exc_info=True)
        return True
    if not row:
        return True
    try:
        if int(row.get("message_count") or 0) > 0:
            return False
    except (TypeError, ValueError):
        return False
    try:
        if session_db.get_session_model_config_value(session_id, _ROUTE_KEY, None):
            return False
    except Exception:
        pass
    return True


def _persist_route(agent: Any, metadata: dict[str, Any], chosen_model: str) -> None:
    session_db = getattr(agent, "_session_db", None)
    session_id = str(getattr(agent, "session_id", "") or "")
    if session_db is None or not session_id:
        return
    try:
        # Persist the actual route so resume reconstructs the same provider/model pair.
        if chosen_model and chosen_model != metadata.get("original_model"):
            session_db.update_session_model(session_id, chosen_model, provider=metadata.get("provider") or None)
        session_db.patch_session_model_config(session_id, {_ROUTE_KEY: metadata})
    except Exception:
        logger.warning("Jev Auto could not persist session route", exc_info=True)


def maybe_route_first_session_task(agent: Any, user_message: Any, conversation_history: Any = None) -> bool:
    """Route a new root session once, before system-prompt construction.

    Returns True only when the live model changed.  Every failure is fail-open: Loki keeps the
    user's configured model and proceeds with the turn.
    """
    cfg = _routing_config()
    if not bool(cfg.get("enabled", False)) or str(cfg.get("mode") or "jev_auto") != "jev_auto":
        return False
    if not configured_typesafe_key() or not _is_new_root_session(agent, conversation_history):
        return False

    agent._jev_auto_route_attempted = True
    provider = str(getattr(agent, "provider", "") or "").strip()
    current_model = str(getattr(agent, "model", "") or "").strip()
    if not provider or not current_model:
        return False

    task, requires_vision = _task_text_and_vision(user_message)
    if not task:
        return False
    try:
        max_candidates = int(cfg.get("max_candidates", _DEFAULT_MAX_CANDIDATES))
    except (TypeError, ValueError):
        max_candidates = _DEFAULT_MAX_CANDIDATES
    candidates = discover_candidates(
        provider, current_model, max_candidates=max_candidates, requires_vision=requires_vision
    )
    if len(candidates) < 2:
        logger.info("Jev Auto skipped: %s exposes fewer than two eligible models", provider)
        return False

    try:
        choice, confidence = choose_model(
            task=task,
            provider=provider,
            current_model=current_model,
            candidates=candidates,
            cost_bias=str(cfg.get("cost_bias") or "balanced"),
        )
    except TypeSafeRequestError as exc:
        logger.warning("Jev Auto failed open on TypeSafe request: %s", exc)
        return False
    except Exception:
        logger.warning("Jev Auto routing failed open", exc_info=True)
        return False

    try:
        threshold = float(cfg.get("confidence_threshold", 0.55))
    except (TypeError, ValueError):
        threshold = 0.55
    threshold = max(0.0, min(1.0, threshold))
    if confidence < threshold:
        choice = current_model

    metadata = {
        "mode": "jev_auto",
        "provider": provider,
        "original_model": current_model,
        "chosen_model": choice,
        "confidence": round(confidence, 6),
        "confidence_threshold": threshold,
        "cost_bias": str(cfg.get("cost_bias") or "balanced"),
        "candidate_count": len(candidates),
        "task_fingerprint": hashlib.sha256(task.encode("utf-8", errors="replace")).hexdigest()[:16],
    }
    if choice == current_model:
        _persist_route(agent, metadata, choice)
        agent._jev_auto_last_route = dict(metadata)
        logger.info("Jev Auto kept %s/%s (confidence %.3f)", provider, current_model, confidence)
        return False

    try:
        from agent.agent_runtime_helpers import switch_model
        switch_model(
            agent,
            choice,
            provider,
            api_key=str(getattr(agent, "api_key", "") or ""),
            base_url=str(getattr(agent, "base_url", "") or ""),
            api_mode=str(getattr(agent, "api_mode", "") or ""),
        )
    except Exception:
        logger.warning("Jev Auto selected %s but live switch failed; keeping %s", choice, current_model, exc_info=True)
        return False

    metadata["chosen_model"] = str(getattr(agent, "model", choice) or choice)
    _persist_route(agent, metadata, metadata["chosen_model"])
    agent._jev_auto_last_route = dict(metadata)
    try:
        emit = getattr(agent, "_emit_status", None)
        if callable(emit):
            emit(
                f"⚡ Loki Autorouter (Jev) routed {current_model} → {metadata['chosen_model']} "
                f"within {provider}"
            )
    except Exception:
        logger.debug("Jev Auto route status emission failed", exc_info=True)
    logger.info(
        "Jev Auto routed new session within %s: %s -> %s (confidence %.3f)",
        provider, current_model, metadata["chosen_model"], confidence,
    )
    return True
