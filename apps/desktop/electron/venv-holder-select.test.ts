import assert from 'node:assert/strict'

import { test } from 'vitest'

import { hasWindowsPathPrefix, isLokiOwnedVenvDaemon } from './venv-holder-select'

const SCRIPTS = 'C:\\Loki\\venv\\Scripts'

test('matches the hindsight daemon shim (exe under venv Scripts + hindsight cmdline)', () => {
  assert.equal(
    isLokiOwnedVenvDaemon(
      'C:\\Loki\\venv\\Scripts\\pythonw.exe',
      'C:\\Loki\\venv\\Scripts\\pythonw.exe -m hindsight_api.main --daemon --idle-timeout 300 --port 9177',
      SCRIPTS
    ),
    true
  )
})

test('Windows path prefix match is ordinal case-insensitive', () => {
  assert.equal(
    isLokiOwnedVenvDaemon(
      'c:\\loki\\venv\\scripts\\python.exe',
      'python.exe -m hindsight_api.main --daemon',
      'C:\\Loki\\venv\\Scripts'
    ),
    true
  )
})

test('excludes external venv holders that are not the hindsight daemon', () => {
  // a user terminal running the loki CLI from the venv — must NOT be killed
  assert.equal(isLokiOwnedVenvDaemon('C:\\Loki\\venv\\Scripts\\loki.exe', 'loki chat -q "hi"', SCRIPTS), false)
  // an unrelated python script using the venv interpreter
  assert.equal(
    isLokiOwnedVenvDaemon('C:\\Loki\\venv\\Scripts\\python.exe', 'python C:\\tools\\import.py', SCRIPTS),
    false
  )
})

test('excludes exes outside the venv even when the cmdline mentions hindsight', () => {
  assert.equal(
    isLokiOwnedVenvDaemon('C:\\Other\\pythonw.exe', 'pythonw -m hindsight_api.main --daemon', SCRIPTS),
    false
  )
})

test('prefix boundary: sibling dirs (ScriptsX) do not match', () => {
  assert.equal(hasWindowsPathPrefix('C:\\Loki\\venv\\ScriptsX\\python.exe', SCRIPTS), false)
  assert.equal(hasWindowsPathPrefix('C:\\Loki\\venv\\Scripts\\python.exe', SCRIPTS), true)
})

test('null/undefined fields never match', () => {
  assert.equal(isLokiOwnedVenvDaemon(null, 'x', SCRIPTS), false)
  assert.equal(isLokiOwnedVenvDaemon('C:\\Loki\\venv\\Scripts\\pythonw.exe', null, SCRIPTS), false)
  assert.equal(isLokiOwnedVenvDaemon(undefined, undefined, SCRIPTS), false)
})
