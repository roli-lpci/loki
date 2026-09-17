"""Small shared TypeSafe System One client used by tools and Jev Auto routing.

The client intentionally owns no routing policy.  Callers supply state/questions and
receive TypeSafe's JSON response.  Secrets are resolved from Loki's active profile and
are never included in raised error messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import httpx

from loki_cli.config import get_env_value

TYPESAFE_SYSTEM_ONE_URL = "https://api.typesafe.ai/v1/systemone"
TYPESAFE_DEFAULT_MODEL = "jev-latest"
DEFAULT_TIMEOUT_SECONDS = 60.0
_MAX_ERROR_BODY_CHARS = 1200


@dataclass
class TypeSafeRequestError(RuntimeError):
    """Sanitized TypeSafe transport/API failure."""

    message: str
    status_code: int | None = None
    details: str = ""

    def __str__(self) -> str:
        return self.message


def configured_typesafe_key() -> str:
    """Return the active profile's TypeSafe API key, stripped."""
    return str(get_env_value("TYPESAFE_API_KEY") or "").strip()


def _safe_error_body(response: httpx.Response, api_key: str) -> str:
    body = str(getattr(response, "text", "") or "").strip()
    if api_key:
        body = body.replace(api_key, "[redacted]")
    return body[:_MAX_ERROR_BODY_CHARS]


def request_system_one(
    *,
    state: Any,
    questions: Mapping[str, Mapping[str, Any]],
    model: str = TYPESAFE_DEFAULT_MODEL,
    api_key: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Call TypeSafe System One and return its decoded JSON object.

    ``api_key`` is injectable for tests/tool callers.  When omitted, the active Loki
    profile is consulted.  Any exception raised by this function is sanitized so the
    credential cannot leak into logs or tool output.
    """
    key = str(api_key if api_key is not None else configured_typesafe_key()).strip()
    if not key:
        raise TypeSafeRequestError("TypeSafe Jev is not configured.")

    payload = {
        "state": state,
        "model": str(model or TYPESAFE_DEFAULT_MODEL).strip() or TYPESAFE_DEFAULT_MODEL,
        "questions": dict(questions),
    }
    try:
        with httpx.Client(timeout=float(timeout_seconds)) as client:
            response = client.post(
                TYPESAFE_SYSTEM_ONE_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise TypeSafeRequestError("TypeSafe Jev request timed out.") from exc
    except httpx.RequestError as exc:
        raise TypeSafeRequestError(f"TypeSafe Jev request failed ({type(exc).__name__}).") from exc

    if not 200 <= response.status_code < 300:
        raise TypeSafeRequestError(
            "TypeSafe API rejected the Jev request.",
            status_code=response.status_code,
            details=_safe_error_body(response, key),
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise TypeSafeRequestError(
            "TypeSafe API returned a non-JSON response.", status_code=response.status_code
        ) from exc
    if not isinstance(data, dict):
        raise TypeSafeRequestError("TypeSafe API returned an unexpected response shape.")
    return data
