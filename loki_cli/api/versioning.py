from __future__ import annotations

from copy import deepcopy
from typing import Any, Awaitable, Callable, MutableMapping, Optional

API_VERSION = "v1"
API_LEGACY_PREFIX = "/api"
API_PREFIX = f"{API_LEGACY_PREFIX}/{API_VERSION}"


_API_DOMAIN_BY_RESOURCE = {
    "actions": "Operations",
    "analytics": "Analytics",
    "audio": "Messaging & Media",
    "auth": "Authentication",
    "chat": "Sessions",
    "config": "Configuration",
    "credentials": "Authentication",
    "cron": "Automation",
    "curator": "Operations",
    "dashboard": "Dashboard",
    "egress": "Operations",
    "env": "Configuration",
    "files": "Files & Git",
    "fs": "Files & Git",
    "gateway": "Operations",
    "git": "Files & Git",
    "health": "System",
    "learning": "Memory & Learning",
    "local-models": "Models",
    "logs": "System",
    "loki": "System",
    "mcp": "Tools & Skills",
    "media": "Messaging & Media",
    "memory": "Memory & Learning",
    "messaging": "Messaging & Media",
    "model": "Models",
    "ops": "Operations",
    "pairing": "Messaging & Media",
    "plugins": "Tools & Skills",
    "portal": "Authentication",
    "profiles": "Configuration",
    "providers": "Models",
    "sessions": "Sessions",
    "skills": "Tools & Skills",
    "ssh": "Files & Git",
    "status": "System",
    "system": "System",
    "tools": "Tools & Skills",
    "webhooks": "Automation",
}

_API_DOMAIN_DESCRIPTIONS = {
    "Analytics": "Usage, cost, and model analytics.",
    "Authentication": "Authentication, credentials, and portal identity.",
    "Automation": "Cron jobs, webhooks, and scheduled execution.",
    "Configuration": "Profiles, configuration, and environment settings.",
    "Dashboard": "Dashboard presentation and extension surfaces.",
    "Files & Git": "Managed files, filesystem operations, Git, and SSH.",
    "Memory & Learning": "Memory providers and learning graph operations.",
    "Messaging & Media": "Messaging channels, pairing, audio, and media.",
    "Models": "Model selection, providers, and local model lifecycle.",
    "Operations": "Gateway lifecycle, maintenance, curator, and operational actions.",
    "Sessions": "Conversation sessions and chat operations.",
    "System": "Health, status, logs, and system information.",
    "Tools & Skills": "Tools, skills, plugins, and MCP integrations.",
}


def api_domain_tag(path: str) -> str | None:
    canonical = canonical_api_path(path)
    prefix = f"{API_PREFIX}/"
    if not canonical.startswith(prefix):
        return None
    resource = canonical[len(prefix):].split("/", 1)[0]
    return _API_DOMAIN_BY_RESOURCE.get(resource, resource.replace("-", " ").title())


def canonical_api_path(path: str) -> str:
    if path == API_LEGACY_PREFIX:
        return API_PREFIX
    if path.startswith(f"{API_PREFIX}/") or path == API_PREFIX:
        return path
    if path.startswith(f"{API_LEGACY_PREFIX}/"):
        return f"{API_PREFIX}{path[len(API_LEGACY_PREFIX):]}"
    return path


def legacy_api_path(path: str) -> Optional[str]:
    if path == API_PREFIX:
        return API_LEGACY_PREFIX
    if path.startswith(f"{API_PREFIX}/"):
        return f"{API_LEGACY_PREFIX}{path[len(API_PREFIX):]}"
    return None


def _legacy_raw_path(raw_path: Any) -> Any:
    if not isinstance(raw_path, (bytes, bytearray)):
        return raw_path
    canonical_prefix = API_PREFIX.encode("ascii")
    legacy_prefix = API_LEGACY_PREFIX.encode("ascii")
    if raw_path == canonical_prefix:
        return legacy_prefix
    if raw_path.startswith(canonical_prefix + b"/"):
        return legacy_prefix + raw_path[len(canonical_prefix):]
    return raw_path


class VersionedAPIAliasMiddleware:
    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: MutableMapping[str, Any], receive: Callable, send: Callable) -> None:
        if scope.get("type") not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        internal_path = legacy_api_path(path)
        if internal_path is not None:
            routed_scope = dict(scope)
            routed_scope["path"] = internal_path
            routed_scope["raw_path"] = _legacy_raw_path(scope.get("raw_path"))
            state = dict(scope.get("state") or {})
            state["loki_api_requested_path"] = path
            state["loki_api_version"] = API_VERSION
            routed_scope["state"] = state
            await self.app(routed_scope, receive, send)
            return

        if scope.get("type") == "http" and path.startswith(f"{API_LEGACY_PREFIX}/"):
            successor = canonical_api_path(path)

            async def send_with_deprecation(message: MutableMapping[str, Any]) -> None:
                if message.get("type") == "http.response.start":
                    headers = list(message.get("headers") or [])
                    headers.append((b"x-loki-api-deprecated", b"true"))
                    headers.append((b"link", f'<{successor}>; rel="successor-version"'.encode("utf-8")))
                    message = dict(message)
                    message["headers"] = headers
                await send(message)

            await self.app(scope, receive, send_with_deprecation)
            return

        await self.app(scope, receive, send)


def _canonicalize_openapi_schema(schema: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(schema)
    paths = result.get("paths")
    if isinstance(paths, dict):
        canonical_paths: dict[str, Any] = {}
        for path, definition in paths.items():
            canonical_path = canonical_api_path(path)
            copied_definition = deepcopy(definition)
            if isinstance(copied_definition, dict):
                domain = api_domain_tag(canonical_path)
                for method, operation in copied_definition.items():
                    if not isinstance(operation, dict):
                        continue
                    if canonical_path != path:
                        operation.setdefault("x-loki-legacy-path", path)
                    if method.lower() in {"get", "post", "put", "patch", "delete", "options", "head"} and domain:
                        operation.setdefault("tags", [domain])
                        operation.setdefault("x-loki-api-domain", domain)
            if canonical_path in canonical_paths and canonical_paths[canonical_path] != copied_definition:
                raise RuntimeError(f"API path collision while versioning OpenAPI schema: {canonical_path}")
            canonical_paths[canonical_path] = copied_definition
        result["paths"] = canonical_paths

    info = result.setdefault("info", {})
    if isinstance(info, dict):
        info["x-loki-api-version"] = API_VERSION
        info["x-loki-api-prefix"] = API_PREFIX
    used_tags = {
        tag
        for definition in result.get("paths", {}).values()
        if isinstance(definition, dict)
        for operation in definition.values()
        if isinstance(operation, dict)
        for tag in operation.get("tags", [])
        if isinstance(tag, str)
    }
    existing_tags = [
        tag
        for tag in result.get("tags", [])
        if isinstance(tag, dict) and isinstance(tag.get("name"), str)
    ]
    existing_names = {tag["name"] for tag in existing_tags}
    result["tags"] = existing_tags + [
        {"name": tag, "description": _API_DOMAIN_DESCRIPTIONS[tag]}
        for tag in _API_DOMAIN_DESCRIPTIONS
        if tag in used_tags and tag not in existing_names
    ]
    result["x-loki-api-version"] = API_VERSION
    result["x-loki-legacy-prefix"] = API_LEGACY_PREFIX
    return result


def install_api_versioning(app: Any) -> None:
    if getattr(app.state, "_loki_api_versioning_installed", False):
        return

    original_openapi = app.openapi
    cached_schema: dict[str, Any] | None = None

    def versioned_openapi() -> dict[str, Any]:
        nonlocal cached_schema
        if cached_schema is None:
            cached_schema = _canonicalize_openapi_schema(original_openapi())
            app.openapi_schema = cached_schema
        return cached_schema

    app.openapi = versioned_openapi
    app.add_middleware(VersionedAPIAliasMiddleware)
    app.state._loki_api_versioning_installed = True
