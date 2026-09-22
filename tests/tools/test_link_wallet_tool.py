from __future__ import annotations

import json


def test_link_wallet_toolset_is_registered():
    import model_tools

    tools = model_tools.get_tool_definitions(
        enabled_toolsets=["link-wallet"],
        disabled_toolsets=[],
        quiet_mode=True,
        skip_tool_search_assembly=True,
    )
    names = {tool["function"]["name"] for tool in tools}
    assert {
        "link_wallet_status",
        "link_wallet_user_info",
        "link_wallet_payment_methods",
        "link_wallet_shipping_addresses",
        "link_spend_create",
        "link_spend_request_approval",
        "link_spend_get",
        "link_spend_wait",
        "link_spend_cancel",
        "link_checkout_fill",
    } <= names


def test_normalize_card_accepts_link_style_fields():
    from tools.link_wallet_tool import _normalize_card

    card = _normalize_card({
        "number": "4242424242424242",
        "exp_month": 12,
        "exp_year": 2030,
        "cvc": "123",
        "name": "Test User",
    })
    assert card == {
        "card_number": "4242424242424242",
        "cardholder_name": "Test User",
        "exp_month": "12",
        "exp_year": "2030",
        "cvc": "123",
    }


def test_checkout_fill_never_returns_card_values(monkeypatch):
    from loki_cli import link_connection
    from tools import browser_vault_tool
    from tools import link_wallet_tool

    card_number = "4242424242424242"
    cvc = "987"
    monkeypatch.setattr(
        link_connection,
        "get_spend_credential",
        lambda spend_request_id, credential_type="card": {
            "spend_request_id": spend_request_id,
            "credential_type": "card",
            "credential": {
                "number": card_number,
                "exp_month": "12",
                "exp_year": "2030",
                "cvc": cvc,
            },
        },
    )
    monkeypatch.setattr(browser_vault_tool, "_focus_bound_origin", lambda *args, **kwargs: "https://merchant.example")
    monkeypatch.setattr(browser_vault_tool, "_current_page_origin", lambda *args, **kwargs: "https://merchant.example")
    monkeypatch.setattr(
        browser_vault_tool,
        "_eval_js",
        lambda *args, **kwargs: {
            "success": True,
            "result": json.dumps([
                {"autocomplete": "cc-number", "formIndex": 0, "index": 0, "maxLength": 19, "label": "Card number", "name": "card", "type": "text"},
                {"autocomplete": "cc-exp-month", "formIndex": 0, "index": 1, "maxLength": 2, "label": "Month", "name": "month", "type": "text"},
                {"autocomplete": "cc-exp-year", "formIndex": 0, "index": 2, "maxLength": 4, "label": "Year", "name": "year", "type": "text"},
                {"autocomplete": "cc-csc", "formIndex": 0, "index": 3, "maxLength": 4, "label": "CVC", "name": "cvc", "type": "text"},
            ]),
        },
    )
    monkeypatch.setattr(browser_vault_tool, "_eval_js_secret", lambda *args, **kwargs: {"success": True, "result": {"filled": 4}})

    result = link_wallet_tool.link_checkout_fill("spend_123", task_id="task")
    assert card_number not in result
    assert cvc not in result
    payload = json.loads(result)
    assert payload["success"] is True
    assert payload["filled_fields"] == 4
