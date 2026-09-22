# Loki release source sync fix

The public installer at `https://loki.computer/install.sh` installs Loki from the standalone Git repository `github.com/wundercorp/loki`, not from the npm package.

When Loki is released from the `shop-master` monorepo under `cli/@wundercorp.loki`, pushing `origin HEAD` only updates the monorepo remote. It does not necessarily update the standalone repository that the installer clones.

This build updates `scripts/deploy.sh` so a release from a monorepo:

1. pushes the monorepo release commit to its normal origin;
2. creates a `git subtree split` for the Loki package directory;
3. pushes that split commit to `git@github.com:wundercorp/loki.git` on the configured release branch;
4. verifies the remote branch points at exactly that split commit before npm/site deployment continues.

The target can be overridden with `LOKI_RELEASE_REPO_URL` and the branch with `LOKI_RELEASE_BRANCH`.

The installer also prints the checked-out Loki version, branch, and short commit after the repository update so stale source is immediately visible.

The Python setup wizard banner now uses blue/cyan instead of magenta and computes its padding rather than relying on manually-spaced box lines.
