from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from loki_cli.api import API_PREFIX, api_domain_tag, canonical_api_path, install_api_versioning, legacy_api_path


def _app() -> FastAPI:
    app = FastAPI(title="test")

    @app.get("/api/health")
    async def health():
        return {"ok": True}

    @app.get("/api/sessions/{session_id}")
    async def session(session_id: str):
        return {"session_id": session_id}

    @app.websocket("/api/events")
    async def events(socket: WebSocket):
        await socket.accept()
        await socket.send_text("ready")
        await socket.close()

    @app.get("/login")
    async def login():
        return {"login": True}

    install_api_versioning(app)
    return app


def test_api_path_helpers_are_idempotent():
    assert API_PREFIX == "/api/v1"
    assert canonical_api_path("/api/health") == "/api/v1/health"
    assert canonical_api_path("/api/v1/health") == "/api/v1/health"
    assert canonical_api_path("/login") == "/login"
    assert legacy_api_path("/api/v1/health") == "/api/health"
    assert legacy_api_path("/api/health") is None
    assert api_domain_tag("/api/health") == "System"
    assert api_domain_tag("/api/v1/sessions/abc") == "Sessions"
    assert api_domain_tag("/login") is None


def test_versioned_http_path_routes_to_existing_handler():
    app = _app()
    client = TestClient(app)

    response = client.get("/api/v1/sessions/abc")

    assert response.status_code == 200
    assert response.json() == {"session_id": "abc"}
    assert "x-loki-api-deprecated" not in response.headers


def test_legacy_http_path_remains_compatible_and_advertises_successor():
    app = _app()
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert response.headers["x-loki-api-deprecated"] == "true"
    assert '</api/v1/health>; rel="successor-version"' in response.headers["link"]


def test_versioned_websocket_path_routes_to_existing_handler():
    app = _app()
    client = TestClient(app)

    with client.websocket_connect("/api/v1/events") as socket:
        assert socket.receive_text() == "ready"


def test_openapi_exposes_canonical_versioned_paths_only():
    app = _app()
    schema = app.openapi()

    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/sessions/{session_id}" in schema["paths"]
    assert "/api/health" not in schema["paths"]
    assert schema["paths"]["/api/v1/health"]["get"]["x-loki-legacy-path"] == "/api/health"
    assert schema["paths"]["/api/v1/health"]["get"]["tags"] == ["System"]
    assert schema["paths"]["/api/v1/sessions/{session_id}"]["get"]["tags"] == ["Sessions"]
    assert any(tag["name"] == "System" for tag in schema["tags"])
    assert schema["paths"]["/login"]
    assert schema["x-loki-api-version"] == "v1"
    assert schema["info"]["x-loki-api-prefix"] == "/api/v1"
