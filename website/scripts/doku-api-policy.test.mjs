import assert from 'node:assert/strict'
import test from 'node:test'

import { canonicalEndpoint, sanitizeDokuApiDocument } from './doku-api-policy.mjs'

test('canonicalEndpoint accepts only Loki API paths and adds v1', () => {
  assert.equal(canonicalEndpoint('/api/skills'), '/api/v1/skills')
  assert.equal(canonicalEndpoint('/api/v1/skills'), '/api/v1/skills')
  assert.equal(canonicalEndpoint('/title'), null)
  assert.equal(canonicalEndpoint('/manage/link'), null)
})

test('Doku policy removes phantom flat endpoints and groups canonical API resources', () => {
  const input = {
    doku: { api: { baseUrl: 'https://loki.computer', endpointCount: 3 } },
    pageMeta: {
      'generated/api-overview': { kind: 'api', generated: true },
      'api/title/get-title': {
        kind: 'api', generated: true, method: 'GET', endpoint: '/title', description: 'GET /title'
      },
      'api/skills/get-api-skills': {
        kind: 'api', generated: true, method: 'GET', endpoint: '/api/skills', description: 'GET /api/skills'
      },
      'api/cron/post-api-cron-fire': {
        kind: 'api', generated: true, method: 'POST', endpoint: '/api/cron/fire', description: 'POST /api/cron/fire'
      }
    },
    pagesContent: {
      'generated/api-overview': 'old overview',
      'api/title/get-title': '# GET /title',
      'api/skills/get-api-skills': '# GET /api/skills\nhttps://loki.computer/api/skills',
      'api/cron/post-api-cron-fire': '# POST /api/cron/fire'
    },
    navigation: {
      tabs: [{
        tab: 'API & Reference',
        groups: [
          { group: 'API', pages: [{ title: 'API Reference', path: 'generated/api-overview' }] },
          { group: 'Title', pages: [{ title: 'GET /title', path: 'api/title/get-title' }] },
          { group: 'Skills', pages: [{ title: 'GET /api/skills', path: 'api/skills/get-api-skills' }] },
          { group: 'Cron', pages: [{ title: 'POST /api/cron/fire', path: 'api/cron/post-api-cron-fire' }] }
        ]
      }]
    }
  }

  const output = sanitizeDokuApiDocument(input)

  assert.equal(output.pageMeta['api/title/get-title'], undefined)
  assert.equal(output.pagesContent['api/title/get-title'], undefined)
  assert.equal(output.pageMeta['api/skills/get-api-skills'].endpoint, '/api/v1/skills')
  assert.match(output.pagesContent['api/skills/get-api-skills'], /\/api\/v1\/skills/)
  assert.equal(output.doku.api.endpointCount, 2)
  assert.match(output.pagesContent['generated/api-overview'], /Canonical API prefix: `\/api\/v1`/)
  assert.doesNotMatch(output.pagesContent['generated/api-overview'], /\/title/)

  const groups = output.navigation.tabs[0].groups
  assert.deepEqual(groups.map(group => group.group), ['API', 'Cron', 'Skills'])
  assert.equal(groups[1].pages[0].title, 'POST /api/v1/cron/fire')
  assert.equal(groups[2].pages[0].title, 'GET /api/v1/skills')
})
