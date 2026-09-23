from __future__ import annotations

import json
import os
import time
import webbrowser
from typing import Any

import httpx

from loki_cli.wundercorp_sso import get_sso_access_token

DEFAULT_LINK_API_URL = "https://link-auth.wundercorp.co"


class LinkConnectionError(RuntimeError):
    pass


def link_api_url() -> str:
    return os.getenv("LOKI_LINK_API_URL", DEFAULT_LINK_API_URL).rstrip("/")


def _request(method: str, path: str, *, interactive_sso: bool = False, retry_auth: bool = True,
             json_body: dict[str, Any] | None = None) -> dict[str, Any]:
    access_token = get_sso_access_token(interactive=interactive_sso)
    if not access_token:
        raise LinkConnectionError("WunderCorp SSO is required. Run /sso login or /link connect.")
    try:
        response = httpx.request(
            method,
            f"{link_api_url()}{path}",
            headers={"authorization": f"Bearer {access_token}", "accept": "application/json"},
            json=json_body,
            timeout=20.0,
        )
    except httpx.HTTPError as exc:
        raise LinkConnectionError(f"Link service request failed: {exc}") from exc
    if response.status_code == 401 and retry_auth:
        access_token = get_sso_access_token(interactive=interactive_sso, force_refresh=True)
        if access_token:
            return _request(method, path, interactive_sso=interactive_sso, retry_auth=False, json_body=json_body)
    if response.status_code >= 400:
        message = ""
        try:
            payload = response.json()
            if isinstance(payload, dict):
                message = str(payload.get("message") or payload.get("error") or "")
        except ValueError:
            pass
        suffix = f": {message}" if message else ""
        raise LinkConnectionError(f"Link service returned HTTP {response.status_code}{suffix}")
    if not response.content:
        return {}
    try:
        payload = response.json()
    except ValueError as exc:
        raise LinkConnectionError("Link service returned an invalid response") from exc
    return payload if isinstance(payload, dict) else {"data": payload}


def link_status(*, interactive_sso: bool = False) -> dict[str, Any]:
    return _request("GET", "/api/link/status", interactive_sso=interactive_sso)


def connect_link(*, timeout_seconds: int = 240, open_browser: bool = True) -> dict[str, Any]:
    status = link_status(interactive_sso=True)
    if status.get("connected"):
        return status
    response = _request("POST", "/api/link/connect", interactive_sso=True)
    authorization_url = response.get("authorization_url")
    if not isinstance(authorization_url, str) or not authorization_url:
        raise LinkConnectionError("Link service did not return an authorization URL")
    if open_browser:
        webbrowser.open(authorization_url)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        time.sleep(2)
        try:
            status = link_status(interactive_sso=False)
        except LinkConnectionError:
            continue
        if status.get("connected"):
            return status
    raise LinkConnectionError("Link authorization timed out")


def disconnect_link() -> dict[str, Any]:
    return _request("POST", "/api/link/disconnect", interactive_sso=False)


def link_user_info() -> dict[str, Any]:
    return _request("GET", "/api/link/user-info", interactive_sso=False)


def link_payment_methods() -> dict[str, Any]:
    return _request("GET", "/api/link/payment-methods", interactive_sso=False)


def link_shipping_addresses() -> dict[str, Any]:
    return _request("GET", "/api/link/shipping-addresses", interactive_sso=False)


def link_spend_requests() -> dict[str, Any]:
    return _request("GET", "/api/link/spend-requests", interactive_sso=False)


def create_spend_request(payload: dict[str, Any]) -> dict[str, Any]:
    return _request("POST", "/api/link/spend-requests", interactive_sso=False, json_body=payload)


def get_spend_request(spend_request_id: str) -> dict[str, Any]:
    return _request("GET", f"/api/link/spend-requests/{spend_request_id}", interactive_sso=False)


def request_spend_approval(spend_request_id: str) -> dict[str, Any]:
    return _request("POST", f"/api/link/spend-requests/{spend_request_id}/request-approval", interactive_sso=False)


def cancel_spend_request(spend_request_id: str) -> dict[str, Any]:
    return _request("POST", f"/api/link/spend-requests/{spend_request_id}/cancel", interactive_sso=False)


def get_spend_credential(spend_request_id: str, credential_type: str = "card") -> dict[str, Any]:
    if credential_type not in {"card", "shared_payment_token", "link_pay_token"}:
        raise LinkConnectionError("Unsupported Link credential type")
    return _request(
        "GET",
        f"/api/link/spend-requests/{spend_request_id}/credential?type={credential_type}",
        interactive_sso=False,
    )


def format_link_status(status: dict[str, Any]) -> str:
    if not status.get("connected"):
        return "Link: not connected\nRun /link connect to connect your Link wallet."
    lines = ["Link: connected"]
    scope = status.get("scope")
    if isinstance(scope, str) and scope:
        lines.append(f"Scopes: {scope}")
    connected_at = status.get("connectedAt") or status.get("connected_at")
    if isinstance(connected_at, str) and connected_at:
        lines.append(f"Connected: {connected_at}")
    return "\n".join(lines)


def format_link_user_info(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def format_link_payment_methods(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def format_link_shipping_addresses(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)
