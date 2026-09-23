# Guardian Search MCP `/v1` migration — complete source delivery

Date: 2026-09-23

## Delivered archives

- `LokiAgent_Guardian_MCP_v1_FULL.zip` is the complete supplied Loki source snapshot with the integration applied, not a patch or updater. Its top-level directory is `LokiAgent/`. The version metadata is synchronized to `0.21.22`.
- `Guardian_Search_MCP_v1_FULL.zip` is the complete supplied Guardian Search source snapshot (excluding the old, redundant nested `Archive.zip`). Its top-level directory is `Guardian-Search/` and **already includes** `infra/terraform/`, deployment scripts, website assets, API code, and tests. API package version is `1.1.2`.
- `Guardian_Terraform_MCP_v1_FULL.zip` is an optional standalone copy of the complete Terraform source, including DNS/TLS diagnostics and examples. Do not apply it a second time if you use the Terraform directory in the full Guardian archive.

The source archives do not include a `.git` directory or runtime secrets. The actual Terraform `backend.hcl` from the original upload is deliberately not redistributed; `scripts/deploy.sh` will bootstrap/generate it for the selected AWS account. `backend.hcl.example` remains included.

## Endpoint and routing contract

| URL | Role |
| --- | --- |
| `https://guardianbrowser.sh/business` | Product/business overview and integration examples |
| `https://mcp.guardianbrowser.sh/` | Dedicated MCP developer landing |
| `https://mcp.guardianbrowser.sh/v1` | Canonical Streamable HTTP MCP transport |
| `https://api.guardianbrowser.sh/v1/...` | Existing JSON API, OpenAPI, authentication, and search |

The API and MCP share an ALB and an API container, but the backend uses **hostname-aware dispatch**: `/v1` is MCP only for the MCP hostname, so the existing REST `/v1` tree stays intact on the API hostname. The legacy **MCP-host** `/mcp` path returns HTTP 308 to `/v1` for a temporary migration period. Advertise and configure `/v1` directly: not every MCP client reliably follows redirects.

`MCP_PUBLIC_URL=https://mcp.guardianbrowser.sh/v1` is the ECS production environment value and Terraform `mcp_url` output. Guardian's agent manifest, `llms.txt`, API config, business page, dedicated landing, examples, and Loki defaults also use `/v1`.

## Deploy Guardian first

From a clean Guardian backend repository checkout, extract the complete Guardian archive **outside** your repository:

```bash
mkdir -p /tmp/guardian-migration
unzip Guardian_Search_MCP_v1_FULL.zip -d /tmp/guardian-migration

cd /path/to/your/guardian-backend

git status --short
git switch -c feat/guardian-search-mcp-v1
rsync -a /tmp/guardian-migration/Guardian-Search/ ./
git diff --check
```

Review the changes carefully if your existing checkout differs from the supplied snapshot. Avoid `rsync --delete`, which could remove newer files or local work. If your existing source tree is not clean, commit or stash its changes before merging. There is no `apply.sh` and no patch file to put inside a Git checkout.

Validate before deploying on a development host with the project dependencies:

```bash
python3 -m pip install -e '.[test]'
pytest -q tests/test_site.py tests/test_mcp_routing.py tests/test_search.py
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
```

For local deployment:

```bash
docker compose up --build
curl -H 'Host: mcp.localhost' http://localhost:8000/
curl http://localhost:8000/v1/health
```

The local API uses `MCP_PUBLIC_URL=http://mcp.localhost:8000/v1`. Send the `Host: mcp.localhost` header to reach MCP through the shared API port, or run `docker compose --profile mcp up --build` for the optional independent `http://localhost:8001/v1` process.

For production, verify AWS identity, Terraform state bucket, DNS/ACM, container credentials and permissions, then deploy:

```bash
sh scripts/deploy.sh
terraform -chdir=infra/terraform output -raw mcp_url
bash infra/terraform/scripts/check_dns_tls_v3.sh guardianbrowser.sh
bash scripts/smoke-test.sh
```

The production smoke test performs an **actual MCP initialize JSON-RPC POST** (not merely a HEAD request), plus website/discovery, REST API health/config, and multi-engine search checks.

## Integrate Loki second

Extract the full Loki source archive outside the Git working tree and merge into a clean checkout:

```bash
unzip LokiAgent_Guardian_MCP_v1_FULL.zip -d /tmp/guardian-migration

cd /path/to/your/wundercorp-loki
git status --short
git switch -c feat/guardian-search-mcp-v1
rsync -a /tmp/guardian-migration/LokiAgent/ ./
git diff --check
```

Verify Loki before a release:

```bash
python3 -m pytest -q \
  tests/tools/test_webmcp_tool.py \
  tests/loki_cli/test_guardian_search_mcp_default.py \
  tests/loki_cli/test_link_sso_commands.py \
  tests/loki_cli/test_ops_mode.py
python3 scripts/sync_version.py verify
node scripts/verify-package-contents.mjs
loki mcp test guardian_search
```

The default Loki configuration registers `guardian_search` at the canonical `/v1` URL. The toggle is available as a named toolset. `/go shopping` uses Guardian product discovery first when available, checks WebMCP capability metadata without unnecessarily launching a browser, and keeps Loki's ordinary web search as a fallback when Guardian is offline. Checkout still requires Link approval. The optional remote Guardian tools are **not** hard requirements for activating the shopping workflow, so losing the MCP connection does not unnecessarily disable shopping.

## Local verification performed for this delivery

- Loki focused integration tests: **28 passed**.
- Loki version synchronization check and package-contents check: **passed**.
- Guardian Python syntax and Bash smoke-test syntax checks: **passed**.
- Guardian route, HTML, API, and search suite: **55 passed against a local stub of the missing MCP dependency**, exercising host routing, redirects, site assets, existing REST endpoints, and search behavior. This is not a full production MCP SDK test.

**Not verified in this offline environment:** real MCP SDK handshake against the actual installed `mcp` package, Terraform CLI `validate`, Docker container builds, DNS/ACM, and production deployment. The dependency installation could not reach PyPI, and Terraform is unavailable here. The included tests and production smoke-test script are the remaining release gates to run in an environment with those dependencies and AWS access. No live production configuration was changed by creating these archives.
