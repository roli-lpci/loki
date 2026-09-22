from __future__ import annotations

import json
import time
from urllib.parse import parse_qs, urlparse

from loki_cli.commands import resolve_command
from loki_cli import link_connection, wundercorp_sso


def _jwt(payload: dict) -> str:
    import base64

    def enc(value: dict) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{enc({'alg': 'none'})}.{enc(payload)}.sig"


def test_registry_exposes_sso_and_link_commands():
    sso = resolve_command("sso")
    link = resolve_command("link")
    wallet = resolve_command("wallet")
    assert sso is not None
    assert sso.cli_only is True
    assert sso.subcommands == ("status", "login", "logout")
    assert link is not None
    assert link.cli_only is True
    assert wallet is link
    assert "connect" in link.subcommands


def test_sso_authorization_url_uses_registered_loopback_and_pkce(monkeypatch):
    monkeypatch.delenv("LOKI_WUNDERCORP_SSO_DOMAIN", raising=False)
    monkeypatch.delenv("LOKI_WUNDERCORP_SSO_CLIENT_ID", raising=False)
    monkeypatch.delenv("LOKI_WUNDERCORP_SSO_REDIRECT_URI", raising=False)
    url = wundercorp_sso._authorization_url("state-value", "challenge-value")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == "https://auth.wundercorp.co/oauth2/authorize"
    assert query["client_id"] == ["42s62lgsghpne2r3gf8ret6ojf"]
    assert query["redirect_uri"] == ["http://127.0.0.1:48741/auth/callback"]
    assert query["scope"] == ["openid email profile"]
    assert query["state"] == ["state-value"]
    assert query["code_challenge"] == ["challenge-value"]
    assert query["code_challenge_method"] == ["S256"]


def test_sso_refresh_preserves_refresh_token(tmp_path, monkeypatch):
    monkeypatch.setattr(wundercorp_sso, "get_loki_home", lambda: tmp_path)
    old_refresh = "refresh-original"
    wundercorp_sso._save_state({
        "access_token": _jwt({"token_use": "access", "exp": int(time.time()) - 60}),
        "refresh_token": old_refresh,
    })
    new_access = _jwt({"token_use": "access", "exp": int(time.time()) + 3600})
    monkeypatch.setattr(wundercorp_sso, "_token_request", lambda data, timeout_seconds=20.0: {"access_token": new_access})
    assert wundercorp_sso.refresh_sso_session() == new_access
    stored = json.loads((tmp_path / "wundercorp-sso.json").read_text())
    assert stored["refresh_token"] == old_refresh
    assert stored["access_token"] == new_access


def test_link_connect_reuses_sso_and_polls(monkeypatch):
    statuses = iter([{"connected": False}, {"connected": False}, {"connected": True, "scope": "payment_methods.agentic userinfo:read"}])
    monkeypatch.setattr(link_connection, "link_status", lambda interactive_sso=False: next(statuses))
    monkeypatch.setattr(link_connection, "_request", lambda method, path, interactive_sso=False, retry_auth=True: {"authorization_url": "https://login.link.com/auth?x=1"})
    opened = []
    monkeypatch.setattr(link_connection.webbrowser, "open", opened.append)
    monkeypatch.setattr(link_connection.time, "sleep", lambda seconds: None)
    result = link_connection.connect_link(timeout_seconds=5)
    assert result["connected"] is True
    assert opened == ["https://login.link.com/auth?x=1"]


def test_link_status_copy_for_disconnected():
    assert link_connection.format_link_status({"connected": False}) == (
        "Link: not connected\nRun /link connect to connect your Link wallet."
    )
