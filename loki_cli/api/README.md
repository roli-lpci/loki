# Loki HTTP API layout

`loki_cli.api` owns the public HTTP API contract. The canonical contract is versioned at `/api/v1`.

- `versioning.py` defines the version boundary, compatibility aliases, deprecation headers, and OpenAPI canonicalization.
- `v1/router.py` owns route registration order for API v1.
- `web_routers/` contains the existing handler implementations. They intentionally keep their historical `/api/...` decorator paths while v1 is introduced compatibly; the versioning middleware maps `/api/v1/...` requests to those handlers.

New public documentation and integrations should use `/api/v1/...`. Existing `/api/...` callers continue to work during the v1 compatibility lifecycle and receive a `Link` header pointing at the canonical successor path.

Do not add public HTTP routes directly to `web_server.py`. Add or extend a domain handler, register it through `api/v1/router.py`, and add contract tests for the canonical `/api/v1` path.
