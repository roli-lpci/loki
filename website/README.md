# Loki Agent site

`loki.computer` is a minimal static splash page backed by the private S3/CloudFront site origin. The documentation payload is generated alongside it and remains available at `/doku.docs.json`; `/docs` is routed through the Doku renderer.

## Local preview

```bash
npm start
```

This builds the splash page plus the Doku payload and serves them on `http://127.0.0.1:3000`. It does not upload the Doku payload to `doku.sh`.

## Build

```bash
npm run build
```

The deployable site is written to `website/build/`.

## One-shot deployment

From the repository root:

```bash
./scripts/deploy-site.sh
```

For the first deployment or after Terraform changes:

```bash
./scripts/deploy-site.sh --with-infra --yes
```

The Terraform defaults are already configured for the `loki.computer` Route 53 hosted zone. Environment overrides remain available through the existing deploy script.
