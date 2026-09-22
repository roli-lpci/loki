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



def test_registry_exposes_go_shopping_command():
    go = resolve_command("go")
    assert go is not None
    assert go.cli_only is True
    assert go.subcommands == ("shopping", "status", "off")


def test_link_connection_spend_helpers_forward_json(monkeypatch):
    calls = []

    def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return {"id": "spend_123", "status": "pending"}

    monkeypatch.setattr(link_connection, "_request", fake_request)
    result = link_connection.create_spend_request({"amount": 999, "currency": "usd", "context": "x" * 100})
    assert result["id"] == "spend_123"
    assert calls == [(
        "POST",
        "/api/link/spend-requests",
        {"interactive_sso": False, "json_body": {"amount": 999, "currency": "usd", "context": "x" * 100}},
    )]


def test_go_shopping_enables_required_toolsets_and_prompt(monkeypatch):
    import loki_cli.config as config_module
    import loki_cli.tools_config as tools_config
    import loki_cli.cli_commands_mixin as commands_mixin
    from loki_cli.cli_commands_mixin import CLICommandsMixin

    config = {"platform_toolsets": {"cli": []}, "agent": {}, "browser": {}}
    saved = {}

    class Agent:
        ephemeral_system_prompt = None

        def _invalidate_system_prompt(self):
            return None

    class Worker:
        def __init__(self):
            self.started = False

        def start(self):
            self.started = True

    class Stub:
        def __init__(self):
            self.agent = Agent()
            self.enabled_toolsets = []
            self.disabled_toolsets = []
            self._app = True
            self.mutations = []
            self.reset_count = 0
            self.worker = Worker()

        def _run_tools_config(self, **kwargs):
            self.mutations.append(kwargs)
            for name in kwargs["names"]:
                if name not in config["platform_toolsets"]["cli"]:
                    config["platform_toolsets"]["cli"].append(name)

        def new_session(self):
            self.reset_count += 1

        def _side_worker(self, *args, **kwargs):
            return self.worker

    monkeypatch.setattr(config_module, "load_config", lambda: config)
    monkeypatch.setattr(config_module, "save_config", lambda value: saved.update(value))
    monkeypatch.setattr(
        tools_config,
        "_get_platform_tools",
        lambda cfg, platform, **kwargs: set(cfg.get("platform_toolsets", {}).get(platform, [])),
    )
    monkeypatch.setattr(commands_mixin, "_refresh_cli_toolsets", lambda cli: None)
    monkeypatch.setattr("tools.registry.invalidate_check_fn_cache", lambda: None)

    stub = Stub()
    CLICommandsMixin._handle_go_command(stub, "/go shopping")

    assert stub.mutations == [{
        "tools_action": "enable",
        "names": ["terminal", "browser", "link-wallet"],
        "platform": "cli",
    }]
    assert saved["browser"]["backend"] == "browser-use"
    assert stub.reset_count == 1
    assert stub._go_mode == "shopping"
    assert "[LOKI_GO_SHOPPING]" in stub.agent.ephemeral_system_prompt
    assert stub.worker.started is True
