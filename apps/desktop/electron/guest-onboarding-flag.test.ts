import assert from 'node:assert/strict'

import { test } from 'vitest'

import { desktopBackendSpawnEnv, guestOnboardingEnabled } from './guest-onboarding'
import { buildSpawnCommand } from './remote-lifecycle'

test('guestOnboardingEnabled: exactly "1" in env or --guest-onboarding on argv turns the free tier on', () => {
  assert.equal(guestOnboardingEnabled([], { LOKI_GUEST_ONBOARDING: '1' }), true)
  assert.equal(guestOnboardingEnabled(['electron', '.', '--guest-onboarding'], {}), true)

  assert.equal(guestOnboardingEnabled([], {}), false)
  assert.equal(guestOnboardingEnabled([], { LOKI_GUEST_ONBOARDING: 'true' }), false)
  assert.equal(guestOnboardingEnabled([], { LOKI_GUEST_ONBOARDING: '0' }), false)
  assert.equal(guestOnboardingEnabled(['electron', '.', '--local'], { LOKI_GUEST_ONBOARDING: '' }), false)
})

test('desktopBackendSpawnEnv stamps the launch decision last and never lets an inherited value leak', () => {
  const base = {
    LOKI_HOME: '/tmp/home',
    LOKI_DESKTOP: '1',
    LOKI_GUEST_ONBOARDING: '1',
    PATH: '/usr/bin'
  }

  const on = desktopBackendSpawnEnv({ ...base, LOKI_GUEST_ONBOARDING: '0' }, true)
  assert.equal(on.LOKI_GUEST_ONBOARDING, '1')

  const off = desktopBackendSpawnEnv(base, false)
  assert.equal(off.LOKI_GUEST_ONBOARDING, '0', 'a stray inherited "1" must not turn the free tier on')

  for (const env of [on, off]) {
    assert.equal(env.LOKI_HOME, base.LOKI_HOME)
    assert.equal(env.LOKI_DESKTOP, base.LOKI_DESKTOP)
    assert.equal(env.PATH, base.PATH)
  }
})

test('remote SSH spawn command carries LOKI_GUEST_ONBOARDING=1 only when the launch decided on', () => {
  const on = buildSpawnCommand('/x/loki', 'work', { logPath: '~/.loki/log', guestOnboarding: true })
  assert.match(on, /exec env LOKI_DESKTOP=1 LOKI_GUEST_ONBOARDING=1 /)

  const off = buildSpawnCommand('/x/loki', 'work', { logPath: '~/.loki/log', guestOnboarding: false })
  assert.match(off, /exec env LOKI_DESKTOP=1 /)
  assert.doesNotMatch(off, /LOKI_GUEST_ONBOARDING/)

  const unset = buildSpawnCommand('/x/loki', 'work', { logPath: '~/.loki/log' })
  assert.doesNotMatch(unset, /LOKI_GUEST_ONBOARDING/)
})
