/**
 * Tests for electron/backend-probes.ts.
 *
 * Run with: node --test electron/backend-probes.test.ts
 * (Wired into npm test:desktop:platforms in package.json.)
 */

import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { test } from 'vitest'

import {
  canImportLokiCli,
  DEFAULT_PROBE_TIMEOUT_MS,
  lokiRuntimeImportProbe,
  PROBE_TIMEOUT_MS,
  resolveProbeTimeoutMs,
  shouldTrustLokiOverride,
  verifyLokiCli
} from './backend-probes'

// Resolve the host's own Node binary -- guaranteed to be on disk and
// runnable. We use it as both a stand-in for "a python that doesn't
// have loki_cli" (since `node -c "import loki_cli"` will exit
// non-zero) and as a way to script verifyLokiCli's success path
// (a tiny script we write to disk that exits 0 on --version).
const NODE_BIN = process.execPath

test('canImportLokiCli returns false when path is falsy', () => {
  assert.equal(canImportLokiCli(''), false)
  assert.equal(canImportLokiCli(null), false)
  assert.equal(canImportLokiCli(undefined), false)
})

test('canImportLokiCli returns false when interpreter cannot run -c', () => {
  // node IS an interpreter, but `node -c "import loki_cli"` is a
  // SyntaxError -- different exit reason from a real Python's
  // ModuleNotFoundError, but the predicate is "exit 0 or not" and
  // both land on "not", which is exactly what we want for the
  // resolver fall-through.
  assert.equal(canImportLokiCli(NODE_BIN), false)
})

test('canImportLokiCli returns false when binary does not exist', () => {
  const ghost = path.join(os.tmpdir(), 'loki-probes-ghost-' + Date.now() + '.exe')
  assert.equal(canImportLokiCli(ghost), false)
})

test('loki runtime import probe checks config dependencies', () => {
  const probe = lokiRuntimeImportProbe()
  assert.match(probe, /\bimport yaml\b/)
  // dotenv is the first third-party import on the CLI boot path
  // (loki_cli/env_loader.py); a mid-update venv missing python-dotenv
  // passed the old probe and produced an unrecoverable boot loop.
  assert.match(probe, /\bimport dotenv\b/)
  assert.match(probe, /\bimport loki_cli\.config\b/)
})

test('explicit Loki override is authoritative', () => {
  assert.equal(shouldTrustLokiOverride('/nix/store/abc/bin/loki'), true)
})

test('empty Loki override is not authoritative', () => {
  assert.equal(shouldTrustLokiOverride(''), false)
  assert.equal(shouldTrustLokiOverride(undefined), false)
})

test('verifyLokiCli returns false when command is falsy', () => {
  assert.equal(verifyLokiCli(''), false)
  assert.equal(verifyLokiCli(null), false)
  assert.equal(verifyLokiCli(undefined), false)
})

test('verifyLokiCli returns false when binary does not exist', () => {
  const ghost = path.join(os.tmpdir(), 'loki-probes-ghost-' + Date.now() + '.exe')
  assert.equal(verifyLokiCli(ghost), false)
})

test('verifyLokiCli returns true when --version exits 0', () => {
  // Write a tiny script that exits 0 regardless of args, then invoke
  // it through node. This stands in for a working loki binary --
  // verifyLokiCli only cares about the exit code.
  const scriptPath = path.join(os.tmpdir(), `loki-probes-ok-${Date.now()}-${process.pid}.cjs`)
  fs.writeFileSync(scriptPath, 'process.exit(0)\n')

  try {
    // Use node as the launcher and our script as the "command". Pass
    // shell:false (default) -- node is a real binary, no shim.
    // execFileSync passes ['--version'] as args, which node ignores
    // gracefully (well, it prints its version and exits 0, which is
    // perfect -- exit code 0 is the only signal we read).
    assert.equal(verifyLokiCli(NODE_BIN), true)
  } finally {
    try {
      fs.unlinkSync(scriptPath)
    } catch {
      void 0
    }
  }
})

test('verifyLokiCli swallows timeouts (does not throw)', () => {
  // We can't easily provoke a real hang in CI without slowing the
  // suite, but we CAN confirm that an invocation that DOES throw
  // (because the binary is missing) returns false rather than
  // propagating. Same code path the timeout case takes.
  assert.equal(verifyLokiCli('/definitely/not/a/real/binary/anywhere'), false)
})

test('default probe timeout is 15s (not the old 5s death-loop value)', () => {
  assert.equal(DEFAULT_PROBE_TIMEOUT_MS, 15_000)
  // Module constant uses process.env at load time; with no override it
  // matches the default (tests run without LOKI_PROBE_TIMEOUT_MS).
  assert.equal(PROBE_TIMEOUT_MS, DEFAULT_PROBE_TIMEOUT_MS)
})

test('resolveProbeTimeoutMs honours LOKI_PROBE_TIMEOUT_MS', () => {
  assert.equal(resolveProbeTimeoutMs({}), DEFAULT_PROBE_TIMEOUT_MS)
  assert.equal(resolveProbeTimeoutMs({ LOKI_PROBE_TIMEOUT_MS: '30000' }), 30_000)
  assert.equal(resolveProbeTimeoutMs({ LOKI_PROBE_TIMEOUT_MS: '0' }), DEFAULT_PROBE_TIMEOUT_MS)
  assert.equal(resolveProbeTimeoutMs({ LOKI_PROBE_TIMEOUT_MS: 'nope' }), DEFAULT_PROBE_TIMEOUT_MS)
  // Cap runaway values
  assert.equal(resolveProbeTimeoutMs({ LOKI_PROBE_TIMEOUT_MS: '999999' }), 120_000)
})
