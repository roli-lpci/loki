import { useQuery } from '@tanstack/react-query'

import { getLokiConfigRecord, type ProfileScope, profileScopeKey } from '@/loki'
import { queryClient, writeCache } from '@/lib/query-client'
import type { LokiConfigRecord } from '@/types/loki'

// One shared cache for the whole profile config record (`GET /api/config`).
// Every settings surface (MCP, model, config) reads and writes through this key
// so a save in one shows in the others, and revisiting a tab paints the cache
// instead of blanking on a fresh fetch.
//
// Distinct from session/hooks/use-loki-config.ts, which is side-effecting —
// it pushes personality/cwd/voice/… into the session stores for live chat.
export const LOKI_CONFIG_KEY = ['loki-config-record'] as const

// Per-scope cache key. The base key (no suffix) is the app-wide active
// profile, unchanged for every caller that passes nothing. An explicit scope —
// the Capabilities scope selector configuring ANOTHER profile, possibly on
// another registered gateway — gets its own suffixed key so switching the
// selector refetches and never paints stale cross-profile config (the
// AGENTS.md scope-in-key rule). profileScopeKey folds a remote pin's
// connection id into the suffix, so two gateways' same-named profiles never
// share a cache row.
export const lokiConfigKey = (profile?: ProfileScope) =>
  profile == null ? LOKI_CONFIG_KEY : ([...LOKI_CONFIG_KEY, profileScopeKey(profile)] as const)

// staleTime 0 → serve cache instantly, background-revalidate on every mount.
// `profile` scopes both the query key and the fetch; omitting it preserves the
// exact app-wide behavior (base key, `profileScoped(undefined)` fallback).
export const useLokiConfigRecord = (profile?: ProfileScope) =>
  useQuery({
    queryKey: lokiConfigKey(profile),
    // null/undefined both mean "no override" → fetch with undefined so
    // capabilityScoped falls back to the app-wide active profile (passing null
    // would wrongly target the primary backend).
    queryFn: () => getLokiConfigRecord(profile ?? undefined),
    staleTime: 0
  })

// setLokiConfigCache writes the app-wide (base-key) record. Pass a profile to
// write the suffixed per-profile cache instead — keeps the selector's optimistic
// write-through landing on the same key its query reads.
export const setLokiConfigCache = writeCache<LokiConfigRecord>(LOKI_CONFIG_KEY)
export const lokiConfigCacheWriter = (profile?: ProfileScope) =>
  writeCache<LokiConfigRecord>(lokiConfigKey(profile))

export const invalidateLokiConfig = (profile?: ProfileScope) =>
  queryClient.invalidateQueries({ queryKey: lokiConfigKey(profile) })
