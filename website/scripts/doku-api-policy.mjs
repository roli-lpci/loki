import { readFileSync, writeFileSync } from 'node:fs'

const API_PREFIX = '/api/v1'
const LEGACY_PREFIX = '/api'

const GROUP_LABELS = new Map([
  ['mcp', 'MCP'],
  ['oauth', 'OAuth'],
  ['ssh', 'SSH'],
  ['fs', 'Filesystem'],
  ['git', 'Git'],
  ['tts', 'TTS']
])

export function canonicalEndpoint(endpoint) {
  if (typeof endpoint !== 'string') return null
  if (endpoint === API_PREFIX || endpoint.startsWith(`${API_PREFIX}/`)) return endpoint
  if (endpoint === LEGACY_PREFIX) return API_PREFIX
  if (endpoint.startsWith(`${LEGACY_PREFIX}/`)) {
    return `${API_PREFIX}${endpoint.slice(LEGACY_PREFIX.length)}`
  }
  return null
}

function groupLabel(endpoint) {
  const segments = endpoint.split('/').filter(Boolean)
  const resource = segments[2] || 'general'
  const known = GROUP_LABELS.get(resource.toLowerCase())
  if (known) return known
  return resource
    .split('-')
    .filter(Boolean)
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function generatedEndpointEntries(document) {
  return Object.entries(document.pageMeta || {}).filter(([, meta]) => (
    meta && meta.kind === 'api' && meta.generated === true && typeof meta.endpoint === 'string'
  ))
}

function rewriteEndpointContent(content, oldEndpoint, endpoint) {
  if (typeof content !== 'string' || oldEndpoint === endpoint) return content
  return content.split(oldEndpoint).join(endpoint)
}

function rebuildApiNavigation(document, keptEntries, removedPaths) {
  const tabs = document.navigation?.tabs
  if (!Array.isArray(tabs)) return
  const apiTab = tabs.find(tab => tab?.tab === 'API & Reference')
  if (!apiTab || !Array.isArray(apiTab.groups)) return

  const generatedPaths = new Set(keptEntries.map(([path]) => path))
  const preservedGroups = []

  for (const group of apiTab.groups) {
    const pages = Array.isArray(group?.pages) ? group.pages : []
    const preservedPages = pages.filter(page => (
      page && !removedPaths.has(page.path) && !generatedPaths.has(page.path)
    ))
    if (preservedPages.length) {
      preservedGroups.push({ ...group, pages: preservedPages })
    }
  }

  const grouped = new Map()
  for (const [path, meta] of keptEntries) {
    const label = groupLabel(meta.endpoint)
    if (!grouped.has(label)) grouped.set(label, [])
    grouped.get(label).push({
      title: `${meta.method || 'GET'} ${meta.endpoint}`,
      path,
      description: `${meta.method || 'GET'} ${meta.endpoint}`
    })
  }

  const generatedGroups = [...grouped.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([group, pages]) => ({
      group,
      pages: pages.sort((left, right) => left.title.localeCompare(right.title))
    }))

  apiTab.groups = [...preservedGroups, ...generatedGroups]
}

function rebuildApiOverview(document, keptEntries) {
  if (!document.pagesContent) return
  const baseUrl = document.doku?.api?.baseUrl || 'https://loki.computer'
  const endpointLines = keptEntries
    .map(([, meta]) => `- \`${meta.method || 'GET'}\` \`${meta.endpoint}\``)
    .sort((left, right) => left.localeCompare(right))

  document.pagesContent['generated/api-overview'] = [
    '# API Reference',
    '',
    `Primary API origin: \`${baseUrl}\``,
    '',
    `Canonical API prefix: \`${API_PREFIX}\``,
    '',
    'Legacy `/api/*` routes remain compatibility aliases, but new integrations should use the versioned prefix.',
    '',
    `Doku detected **${keptEntries.length}** documented Loki HTTP endpoints after public-API filtering.`,
    '',
    '## Endpoints',
    '',
    ...endpointLines,
    ''
  ].join('\n')
}

export function sanitizeDokuApiDocument(document) {
  const copy = structuredClone(document)
  copy.pageMeta ||= {}
  copy.pagesContent ||= {}

  const removedPaths = new Set()
  const keptEntries = []

  for (const [path, meta] of generatedEndpointEntries(copy)) {
    const oldEndpoint = meta.endpoint
    const endpoint = canonicalEndpoint(oldEndpoint)
    if (!endpoint) {
      removedPaths.add(path)
      delete copy.pageMeta[path]
      delete copy.pagesContent[path]
      continue
    }

    meta.endpoint = endpoint
    meta.description = `${meta.method || 'GET'} ${endpoint}`
    copy.pagesContent[path] = rewriteEndpointContent(copy.pagesContent[path], oldEndpoint, endpoint)
    keptEntries.push([path, meta])
  }

  keptEntries.sort((left, right) => {
    const endpointOrder = left[1].endpoint.localeCompare(right[1].endpoint)
    if (endpointOrder !== 0) return endpointOrder
    return String(left[1].method || '').localeCompare(String(right[1].method || ''))
  })

  rebuildApiNavigation(copy, keptEntries, removedPaths)
  rebuildApiOverview(copy, keptEntries)

  if (copy.doku?.api) {
    copy.doku.api.endpointCount = keptEntries.length
  }

  return copy
}

export function sanitizeDokuApiFile(path) {
  const document = JSON.parse(readFileSync(path, 'utf8'))
  const sanitized = sanitizeDokuApiDocument(document)
  writeFileSync(path, `${JSON.stringify(sanitized, null, 2)}\n`)
  return sanitized
}
