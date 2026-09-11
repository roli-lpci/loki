import { describe, expect, it } from 'vitest'

import {
  normalizeLokiOpenString,
  pathFromLokiDeepLink,
  pathFromOpenDeepLink,
  resolveLokiOpenPath
} from './loki-open-target'

describe('normalizeLokiOpenString', () => {
  it('accepts hash-router paths and strips a leading hash', () => {
    expect(normalizeLokiOpenString('/index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeLokiOpenString('#/index-network/intent/1')).toBe('/index-network/intent/1')
  })

  it('maps plugin-scoped loki:// deep links to the same path', () => {
    expect(normalizeLokiOpenString('loki://index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeLokiOpenString('loki://index-network/intent/1?focus=true')).toBe(
      '/index-network/intent/1?focus=true'
    )
  })

  it('maps loki://open/… deep links by stripping the open host', () => {
    expect(normalizeLokiOpenString('loki://open/index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeLokiOpenString('loki://open/settings/plugins')).toBe('/settings/plugins')
  })

  it('rejects reserved loki kinds and unsafe paths', () => {
    expect(normalizeLokiOpenString('loki://blueprint/morning-brief')).toBeNull()
    expect(normalizeLokiOpenString('loki://plugin/install')).toBeNull()
    expect(normalizeLokiOpenString('https://example.com/x')).toBeNull()
    expect(normalizeLokiOpenString('/../etc/passwd')).toBeNull()
    expect(normalizeLokiOpenString('index-network')).toBeNull()
  })
})

describe('resolveLokiOpenPath', () => {
  it('merges structured path + params', () => {
    expect(resolveLokiOpenPath({ path: '/index-network/intent/1', params: { focus: 'true' } })).toBe(
      '/index-network/intent/1?focus=true'
    )
  })

  it('resolves href the same as a bare string', () => {
    expect(resolveLokiOpenPath({ href: 'loki://index-network/intent/1' })).toBe('/index-network/intent/1')
  })
})

describe('pathFromLokiDeepLink', () => {
  it('builds the navigate path from a plugin-scoped deep-link payload', () => {
    expect(pathFromLokiDeepLink('index-network', 'intent/1')).toBe('/index-network/intent/1')
  })

  it('builds the navigate path from loki://open/… payloads', () => {
    expect(pathFromOpenDeepLink('index-network/intent/1')).toBe('/index-network/intent/1')
    expect(pathFromLokiDeepLink('open', 'agent/42')).toBe('/agent/42')
  })

  it('ignores reserved kinds', () => {
    expect(pathFromLokiDeepLink('blueprint', 'morning-brief')).toBeNull()
    expect(pathFromLokiDeepLink('plugin', 'install')).toBeNull()
  })
})
