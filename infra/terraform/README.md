# Loki Agent infrastructure

This stack deploys `https://loki.computer` with CloudFront, ACM TLS, Route53, a private S3 site origin, and Doku as the documentation renderer.

The root hostname is the Loki Agent splash page served from the private S3 origin. `/privacy` and `/terms` are static site pages from the same origin. `/docs` is routed through the Doku renderer while the generated documentation data stays on the private S3 origin at `/doku.docs.json` and related payload paths.

The S3 origin also contains `docs.json`, `llms.txt`, `llms-full.txt`, API/catalog JSON, images, OAuth metadata, and the shell/PowerShell installers.

## Terraform state

The deploy scripts automatically keep production Terraform state in a private, versioned S3 bucket named `wundercorp-loki-terraform-state-<AWS_ACCOUNT_ID>`. This makes state survive fresh checkouts and ZIP replacements. Set `LOKI_TERRAFORM_STATE_BUCKET` or `LOKI_TERRAFORM_STATE_KEY` only when you intentionally need a different backend.

When `--with-infra` is used, the deployer also reconciles known Loki resources that already exist in AWS but are missing from Terraform state. This is intended for interrupted first deployments: the existing S3 bucket, ACM certificate/validation record, CloudFront OAC, response-headers policy, functions, and distribution are adopted before the plan runs.

## Deploy infrastructure

The production public hosted zone for `loki.computer` is already wired into the stack as `Z09046593O6AIZUOSG6X8`. A normal production plan therefore needs no DNS variable:

```bash
terraform plan
terraform apply
```

For an alternate account or replacement zone, override it explicitly:

```bash
export TF_VAR_hosted_zone_id="Z_REPLACEMENT_ZONE_ID"
terraform plan
```

`doku_origin_domain` defaults to `doku.sh` and only serves the `/docs` renderer path.

## Build the site

```bash
cd ../../website
npm run build
```

The build script emits the splash page and legal pages together with the generated Doku payload in `website/build/`.

## One-shot site deployment

From the repository root:

```bash
./scripts/deploy-site.sh
```

To apply Terraform in the same deployment:

```bash
./scripts/deploy-site.sh --with-infra --yes
```

The broader npm + site release flow remains available through `./scripts/deploy.sh`.
