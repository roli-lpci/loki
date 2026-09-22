from __future__ import annotations

import json
import secrets
import time
from typing import Any

from tools.registry import registry


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _safe_call(fn, *args, **kwargs) -> str:
    try:
        return _json(fn(*args, **kwargs))
    except Exception as exc:
        return _json({"success": False, "error": str(exc)[:300]})


def _link_available() -> bool:
    return True


def link_wallet_status() -> str:
    from loki_cli.link_connection import link_status
    return _safe_call(link_status, interactive_sso=False)


def link_wallet_user_info() -> str:
    from loki_cli.link_connection import link_user_info
    return _safe_call(link_user_info)


def link_wallet_payment_methods() -> str:
    from loki_cli.link_connection import link_payment_methods
    return _safe_call(link_payment_methods)


def link_wallet_shipping_addresses() -> str:
    from loki_cli.link_connection import link_shipping_addresses
    return _safe_call(link_shipping_addresses)


def link_spend_create(amount: int, currency: str, context: str, test: bool = False) -> str:
    from loki_cli.link_connection import create_spend_request

    context = str(context or "").strip()
    if len(context) < 100:
        return _json({
            "success": False,
            "error": "context must be at least 100 characters and describe the merchant, items, final total, shipping, and purchase purpose",
        })
    payload: dict[str, Any] = {
        "amount": int(amount),
        "currency": str(currency or "usd").lower(),
        "context": context,
    }
    if test:
        payload["test"] = True
    return _safe_call(create_spend_request, payload)


def link_spend_request_approval(spend_request_id: str) -> str:
    from loki_cli.link_connection import request_spend_approval
    return _safe_call(request_spend_approval, str(spend_request_id))


def link_spend_get(spend_request_id: str) -> str:
    from loki_cli.link_connection import get_spend_request
    return _safe_call(get_spend_request, str(spend_request_id))


def link_spend_wait(spend_request_id: str, timeout_seconds: int = 180) -> str:
    from loki_cli.link_connection import get_spend_request

    timeout_seconds = max(1, min(int(timeout_seconds), 300))
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            last = get_spend_request(str(spend_request_id))
        except Exception as exc:
            return _json({"success": False, "error": str(exc)[:300]})
        status = str(last.get("status") or "").lower()
        if status in {"approved", "declined", "canceled", "cancelled", "expired", "failed"}:
            return _json(last)
        time.sleep(2)
    return _json({
        "success": False,
        "error": "Timed out waiting for Link approval",
        "spend_request_id": str(spend_request_id),
        "last_status": last.get("status"),
    })


def link_spend_cancel(spend_request_id: str) -> str:
    from loki_cli.link_connection import cancel_spend_request
    return _safe_call(cancel_spend_request, str(spend_request_id))


def _first_string(mapping: dict[str, Any], names: tuple[str, ...]) -> str:
    for name in names:
        value = mapping.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_card(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    nested = raw.get("card")
    if isinstance(nested, dict):
        raw = {**raw, **nested}
    card = {
        "card_number": _first_string(raw, ("card_number", "number", "pan")),
        "cardholder_name": _first_string(raw, ("cardholder_name", "name", "cardholder")),
        "exp_month": _first_string(raw, ("exp_month", "expiry_month", "expiration_month")),
        "exp_year": _first_string(raw, ("exp_year", "expiry_year", "expiration_year")),
        "cvc": _first_string(raw, ("cvc", "cvv", "security_code", "csc")),
        "billing_postal_code": _first_string(raw, ("billing_postal_code", "postal_code", "zip", "zip_code")),
    }
    return {key: value for key, value in card.items() if value}


def link_checkout_fill(spend_request_id: str, task_id: str | None = None) -> str:
    from agent.redact import register_vault_redaction_value
    from agent.vault_login_classifier import (
        ClassifiedLoginControl,
        LoginControl,
        build_fill_js,
        build_inspection_js,
        classify_checkout_control,
        select_checkout_fills,
    )
    from agent.vault_store import PAYMENT_FIELDS
    from loki_cli.link_connection import get_spend_credential
    from tools.browser_vault_tool import (
        _current_page_origin,
        _eval_js,
        _eval_js_secret,
        _focus_bound_origin,
        _parse_json_result,
    )

    effective_task_id = task_id or "default"
    try:
        response = get_spend_credential(str(spend_request_id), "card")
    except Exception as exc:
        return _json({"success": False, "error": str(exc)[:300]})

    card = _normalize_card(response.get("credential"))
    required = ("card_number", "exp_month", "exp_year", "cvc")
    if any(not card.get(field) for field in required):
        return _json({
            "success": False,
            "error": "Link returned an approved credential, but it did not contain the card fields required for browser checkout",
        })

    page_origin = _focus_bound_origin(effective_task_id, "", "payment") or _current_page_origin(effective_task_id)
    if not page_origin:
        return _json({"success": False, "error": "No checkout payment page is open in the active browser session"})

    nonce = secrets.token_hex(8)
    inspected = _eval_js(effective_task_id, build_inspection_js(nonce))
    if not inspected.get("success"):
        return _json({"success": False, "error": "Could not inspect checkout payment fields"})
    raw_controls = _parse_json_result(inspected.get("result"))
    if isinstance(raw_controls, str):
        raw_controls = _parse_json_result(raw_controls)
    if not isinstance(raw_controls, list):
        return _json({"success": False, "error": "Checkout input inspection returned no usable controls"})

    classified: list[ClassifiedLoginControl] = []
    for raw_control in raw_controls:
        if not isinstance(raw_control, dict):
            continue
        result = classify_checkout_control(LoginControl.from_dict(raw_control))
        if result is not None:
            classified.append(result)
    fills = select_checkout_fills(classified, card, PAYMENT_FIELDS)
    if not fills:
        return _json({"success": False, "error": "No supported card fields were found on the checkout page"})

    for value in card.values():
        if value:
            register_vault_redaction_value(value)

    result = _eval_js_secret(
        effective_task_id,
        build_fill_js(fills, expected_origin=page_origin, nonce=nonce),
    )
    card.clear()
    if not result.get("success"):
        return _json({
            "success": False,
            "error_type": result.get("error_type"),
            "error": "Secure Link card injection failed before checkout submission",
        })

    parsed = _parse_json_result(result.get("result"))
    if isinstance(parsed, str):
        parsed = _parse_json_result(parsed)
    if isinstance(parsed, dict) and parsed.get("refused") == "origin_changed":
        return _json({
            "success": False,
            "error_type": "origin_changed",
            "error": "The checkout page navigated before the approved Link credential could be filled; nothing was written",
        })
    filled = int(parsed.get("filled", 0)) if isinstance(parsed, dict) else 0
    return _json({
        "success": filled > 0,
        "spend_request_id": str(spend_request_id),
        "origin": page_origin,
        "filled_fields": filled,
        "fields": sorted(fill["token"] for fill in fills),
        "next": "Review the checkout page state and submit the order only if the merchant, items, shipping, and final total still match the approved spend request.",
    })


_STATUS = {
    "name": "link_wallet_status",
    "description": "Check whether the current WunderCorp user has a connected Link wallet. Use before payment actions.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}
_USER = {
    "name": "link_wallet_user_info",
    "description": "Read basic Link customer information for checkout prefilling. Never use this as payment authorization.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}
_METHODS = {
    "name": "link_wallet_payment_methods",
    "description": "List Link payment-method metadata available to the connected user. This never returns raw card credentials.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}
_ADDRESSES = {
    "name": "link_wallet_shipping_addresses",
    "description": "List Link shipping-address metadata available to the connected user for checkout.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}
_CREATE = {
    "name": "link_spend_create",
    "description": "Create a Link spend request after the browser has reached checkout and the exact final total is known. amount is in the currency minor unit (for USD, cents). context must accurately describe merchant, item(s), shipping, taxes, final total, and purpose. Never invent the amount.",
    "parameters": {
        "type": "object",
        "properties": {
            "amount": {"type": "integer", "minimum": 1, "description": "Exact final amount in minor units, e.g. 999 for $9.99."},
            "currency": {"type": "string", "description": "Three-letter currency code, normally usd."},
            "context": {"type": "string", "minLength": 100, "description": "Detailed human-readable purchase context shown/used for approval."},
            "test": {"type": "boolean", "default": False, "description": "Use Link test-mode spend behavior when supported."},
        },
        "required": ["amount", "currency", "context"],
    },
}
_APPROVE = {
    "name": "link_spend_request_approval",
    "description": "Request explicit Link user approval for a spend request. Present any approval URL/instructions returned to the user and do not retrieve payment credentials until approved.",
    "parameters": {"type": "object", "properties": {"spend_request_id": {"type": "string"}}, "required": ["spend_request_id"]},
}
_GET = {
    "name": "link_spend_get",
    "description": "Retrieve the current redacted status of a Link spend request. Raw payment credentials are never returned.",
    "parameters": {"type": "object", "properties": {"spend_request_id": {"type": "string"}}, "required": ["spend_request_id"]},
}
_WAIT = {
    "name": "link_spend_wait",
    "description": "Wait for a Link spend request to reach a terminal status such as approved or declined. Use after requesting approval instead of repeatedly polling yourself.",
    "parameters": {"type": "object", "properties": {"spend_request_id": {"type": "string"}, "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 300, "default": 180}}, "required": ["spend_request_id"]},
}
_CANCEL = {
    "name": "link_spend_cancel",
    "description": "Cancel a Link spend request that should no longer be used.",
    "parameters": {"type": "object", "properties": {"spend_request_id": {"type": "string"}}, "required": ["spend_request_id"]},
}
_FILL = {
    "name": "link_checkout_fill",
    "description": "Securely fill the active browser checkout with the one-time card credential from an APPROVED Link spend request. Card number/CVC are fetched server-side and injected through the supervised CDP connection; they are never returned to you or written to conversation history. After filling, re-check merchant, items, shipping and final total before submitting the order.",
    "parameters": {"type": "object", "properties": {"spend_request_id": {"type": "string"}}, "required": ["spend_request_id"]},
}

registry.register(name="link_wallet_status", toolset="link-wallet", schema=_STATUS, handler=lambda args, **kw: link_wallet_status(), check_fn=_link_available, emoji="💳")
registry.register(name="link_wallet_user_info", toolset="link-wallet", schema=_USER, handler=lambda args, **kw: link_wallet_user_info(), check_fn=_link_available, emoji="💳")
registry.register(name="link_wallet_payment_methods", toolset="link-wallet", schema=_METHODS, handler=lambda args, **kw: link_wallet_payment_methods(), check_fn=_link_available, emoji="💳")
registry.register(name="link_wallet_shipping_addresses", toolset="link-wallet", schema=_ADDRESSES, handler=lambda args, **kw: link_wallet_shipping_addresses(), check_fn=_link_available, emoji="💳")
registry.register(name="link_spend_create", toolset="link-wallet", schema=_CREATE, handler=lambda args, **kw: link_spend_create(args.get("amount", 0), args.get("currency", "usd"), args.get("context", ""), bool(args.get("test", False))), check_fn=_link_available, emoji="💳")
registry.register(name="link_spend_request_approval", toolset="link-wallet", schema=_APPROVE, handler=lambda args, **kw: link_spend_request_approval(args.get("spend_request_id", "")), check_fn=_link_available, emoji="💳")
registry.register(name="link_spend_get", toolset="link-wallet", schema=_GET, handler=lambda args, **kw: link_spend_get(args.get("spend_request_id", "")), check_fn=_link_available, emoji="💳")
registry.register(name="link_spend_wait", toolset="link-wallet", schema=_WAIT, handler=lambda args, **kw: link_spend_wait(args.get("spend_request_id", ""), args.get("timeout_seconds", 180)), check_fn=_link_available, emoji="💳")
registry.register(name="link_spend_cancel", toolset="link-wallet", schema=_CANCEL, handler=lambda args, **kw: link_spend_cancel(args.get("spend_request_id", "")), check_fn=_link_available, emoji="💳")
registry.register(name="link_checkout_fill", toolset="link-wallet", schema=_FILL, handler=lambda args, **kw: link_checkout_fill(args.get("spend_request_id", ""), task_id=kw.get("task_id")), check_fn=_link_available, emoji="💳")
