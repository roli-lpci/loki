from loki_cli.web_server import app


_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
_PHANTOM_FLAT_PATHS = {
    "/activity_count",
    "/archive_bytes",
    "/author",
    "/created_at",
    "/duration_ms",
    "/message",
    "/name",
    "/session_id",
    "/title",
    "/tokens_delta",
    "/user_id",
}


def test_dashboard_openapi_is_versioned_and_domain_grouped():
    schema = app.openapi()
    api_paths = {path: definition for path, definition in schema["paths"].items() if path.startswith("/api")}

    assert len(api_paths) >= 200
    assert all(path == "/api/v1" or path.startswith("/api/v1/") for path in api_paths)
    assert not (_PHANTOM_FLAT_PATHS & set(schema["paths"]))

    for path, definition in api_paths.items():
        for method, operation in definition.items():
            if method.lower() not in _HTTP_METHODS or not isinstance(operation, dict):
                continue
            assert operation.get("tags"), f"missing domain tag: {method.upper()} {path}"
            assert operation.get("x-loki-api-domain") in operation["tags"]
            assert str(operation.get("x-loki-legacy-path", "")).startswith("/api/")

    tag_names = {tag["name"] for tag in schema.get("tags", [])}
    assert {"Sessions", "Automation", "Tools & Skills", "System"} <= tag_names
