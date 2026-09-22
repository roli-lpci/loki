# Installer UX and release alignment

This build includes three release/onboarding changes:

- The returning-user `loki tools` menu defaults to `Done`, so pressing Enter exits immediately when no tool changes are needed.
- The POSIX and PowerShell installer banners use Loki's blue/cyan theme instead of magenta.
- Production deployment is aligned with the public install source. `install.sh` installs the Git checkout from `main` by default; the deploy script now refuses a production deploy from another branch unless explicitly overridden, and `npm publish` is pinned to `https://registry.npmjs.org`.

The public one-line installer is a Git-based managed install. It does not install Loki from the npm package. Updating S3 or publishing npm therefore does not update what the one-line installer installs unless the corresponding source is also on the release branch (`main` by default).

For an intentional development-branch install, use either:

```bash
curl -fsSL https://loki.computer/install.sh | bash -s -- --branch my-branch
```

or:

```bash
curl -fsSL https://loki.computer/install.sh | LOKI_INSTALL_BRANCH=my-branch bash
```

For production, deploy from `main`. To intentionally deploy another branch, set `LOKI_ALLOW_NON_RELEASE_BRANCH_DEPLOY=1`. This override should not be used for normal releases because the public installer still defaults to the release branch.
