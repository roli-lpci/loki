"""TypeSafe System One / Jev decision tool.

Jev is a structured decision model rather than a chat/text-generation model.  This
module deliberately exposes it as an agent tool instead of an inference provider:
the caller supplies application state plus bounded Choice / Score / Noul questions
and receives TypeSafe's typed answers and probabilities unchanged.
"""

from __future__ import annotations

from typing import Any

from loki_cli.config import get_env_value
from agent.typesafe_client import (
    TYPESAFE_DEFAULT_MODEL, TypeSafeRequestError, request_system_one,
)
from tools.registry import no_cache_check_fn, registry, tool_error, tool_result

_DEFAULT_MODEL = TYPESAFE_DEFAULT_MODEL
_ALLOWED_QUESTION_TYPES = {"choice", "score", "noul"}


@no_cache_check_fn
def check_typesafe_api_key() -> bool:
    """Return whether the active Loki profile has a TypeSafe API key."""
    return bool(str(get_env_value("TYPESAFE_API_KEY") or "").strip())


def _build_questions(questions: Any) -> tuple[dict[str, dict[str, Any]] | None, str | None]:
    """Validate the agent-friendly question list and convert it to TypeSafe's ID map."""
    if not isinstance(questions, list) or not questions:
        return None, "questions must be a non-empty list"

    converted: dict[str, dict[str, Any]] = {}
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            return None, f"questions[{index}] must be an object"

        question_id = str(question.get("id") or "").strip()
        if not question_id:
            return None, f"questions[{index}].id is required"
        if question_id in converted:
            return None, f"duplicate question id: {question_id}"

        question_type = str(question.get("type") or "").strip().lower()
        if question_type not in _ALLOWED_QUESTION_TYPES:
            return None, (
                f"questions[{index}].type must be one of: "
                f"{', '.join(sorted(_ALLOWED_QUESTION_TYPES))}"
            )

        instructions = question.get("instructions")
        if isinstance(instructions, str):
            instructions = instructions.strip()
            if not instructions:
                return None, f"questions[{index}].instructions must not be empty"
        elif isinstance(instructions, (dict, list)):
            if not instructions:
                return None, f"questions[{index}].instructions must not be empty"
        else:
            return None, (
                f"questions[{index}].instructions must be a string, object, or array"
            )

        payload: dict[str, Any] = {
            "type": question_type,
            "instructions": instructions,
        }
        criteria = question.get("criteria")

        if question_type == "choice":
            if not isinstance(criteria, dict) or len(criteria) < 2:
                return None, (
                    f"questions[{index}].criteria must be an object with at least two "
                    "named options for a choice question"
                )
            payload["criteria"] = criteria
        elif question_type == "score":
            if not isinstance(criteria, list) or len(criteria) < 2:
                return None, (
                    f"questions[{index}].criteria must be an ordered list with at least two "
                    "described levels for a score question"
                )
            payload["criteria"] = criteria
        elif criteria is not None:
            if not isinstance(criteria, dict):
                return None, f"questions[{index}].criteria must be an object for a noul question"
            unknown_keys = set(criteria) - {"true", "false"}
            if unknown_keys:
                return None, (
                    f"questions[{index}].criteria for noul may only define true/false descriptions"
                )
            payload["criteria"] = criteria

        converted[question_id] = payload

    return converted, None



def typesafe_ask_tool(
    state: Any,
    questions: Any,
    *,
    model: str = _DEFAULT_MODEL,
) -> str:
    """Evaluate typed questions over *state* with TypeSafe Jev/System One."""
    api_key = str(get_env_value("TYPESAFE_API_KEY") or "").strip()
    if not api_key:
        return tool_error(
            "TypeSafe Jev is not configured. Add TYPESAFE_API_KEY with `loki setup jev` "
            "or in Settings → Keys → Tools."
        )

    converted_questions, validation_error = _build_questions(questions)
    if validation_error:
        return tool_error(validation_error)

    model_name = str(model or _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
    try:
        data = request_system_one(
            state=state, questions=converted_questions, model=model_name, api_key=api_key
        )
    except TypeSafeRequestError as exc:
        extra = {}
        if exc.status_code is not None:
            extra["status"] = exc.status_code
        if exc.details:
            extra["details"] = exc.details
        message = str(exc)
        if "timed out" in message.lower():
            message += " Try again with less state or fewer questions."
        return tool_error(message, **extra)

    return tool_result(data)


_TYPESAFE_QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "description": "Caller-chosen stable ID used to identify this answer in the response.",
        },
        "type": {
            "type": "string",
            "enum": ["choice", "score", "noul"],
            "description": (
                "choice = select one defined option; score = place state on ordered described "
                "levels; noul = probability that a condition holds."
            ),
        },
        "instructions": {
            "description": "One narrow, self-contained judgment to make from the supplied state.",
            "anyOf": [
                {"type": "string"},
                {"type": "object", "additionalProperties": True},
                {"type": "array"},
            ],
        },
        "criteria": {
            "description": (
                "For choice: object mapping option names to optional descriptions. For score: "
                "ordered array of level descriptions. Omit for noul."
            ),
            "anyOf": [
                {
                    "type": "object",
                    "additionalProperties": True,
                },
                {"type": "array", "items": {"anyOf": [{"type": "string"}, {"type": "object"}]}},
            ],
        },
    },
    "required": ["id", "type", "instructions"],
}

TYPESAFE_ASK_SCHEMA = {
    "name": "typesafe_ask",
    "description": (
        "Use TypeSafe Jev/System One for fast typed judgments over application state. Ask Choice, "
        "Score, or Noul questions and receive structured decisions/probabilities. Jev does NOT "
        "generate prose; use the normal chat model for writing/reasoning and this tool for bounded "
        "semantic decisions. Independent questions over the same state should be batched together."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "state": {
                "description": (
                    "State Jev should judge. TypeSafe accepts a plain string or structured JSON "
                    "object/array; use named fields when several facts or relationships matter."
                ),
                "anyOf": [
                    {"type": "string"},
                    {"type": "object", "additionalProperties": True},
                    {"type": "array"},
                ],
            },
            "questions": {
                "type": "array",
                "description": "Independent typed questions evaluated against the same state.",
                "items": _TYPESAFE_QUESTION_SCHEMA,
                "minItems": 1,
            },
            "model": {
                "type": "string",
                "description": "TypeSafe System One model alias; defaults to jev-latest.",
                "default": _DEFAULT_MODEL,
            },
        },
        "required": ["state", "questions"],
    },
}


registry.register(
    name="typesafe_ask",
    toolset="typesafe",
    schema=TYPESAFE_ASK_SCHEMA,
    handler=lambda args, **kw: typesafe_ask_tool(
        args.get("state", {}),
        args.get("questions", []),
        model=args.get("model", _DEFAULT_MODEL),
    ),
    check_fn=check_typesafe_api_key,
    requires_env=["TYPESAFE_API_KEY"],
    description="TypeSafe Jev structured decisions (Choice, Score, Noul)",
    emoji="⚡",
    max_result_size_chars=100_000,
)
