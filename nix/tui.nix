# nix/tui.nix — Loki TUI (Ink/React) compiled with tsc and bundled
{ lokiNpmLib, ... }:
lokiNpmLib.buildNpmPackage {
  dirs = [
    "tui-ui"
    "apps/shared"
  ];

  doCheck = false;

  buildPhase = ''
    # esbuild bundles everything — no need for tsc or vite.
    # Run from the workspace root where node_modules/ lives.
    node tui-ui/scripts/build.mjs
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out/lib/loki-tui
    # esbuild writes to tui-ui/dist/ from the source root (no cd).
    cp -r tui-ui/dist $out/lib/loki-tui/dist

    # package.json kept for "type": "module" resolution on `node dist/entry.js`.
    cp tui-ui/package.json $out/lib/loki-tui/

    runHook postInstall
  '';
}
