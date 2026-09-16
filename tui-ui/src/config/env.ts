import type { MouseTrackingMode } from '@wundercorp/loki-ink'

import { isTermuxTuiMode } from '../lib/termux.js'

const truthy = (value: string | undefined): boolean => /^(?:1|true|yes|on)$/i.test(String(value ?? '').trim())

export const STARTUP_QUERY = String(process.env.LOKI_TUI_QUERY ?? '')
export const STARTUP_IMAGE = String(process.env.LOKI_TUI_IMAGE ?? '')
export const STARTUP_RESUME_ID = String(process.env.LOKI_TUI_RESUME ?? '')

export const DASHBOARD_TUI_MODE = truthy(process.env.LOKI_TUI_DASHBOARD)
export const TERMUX_TUI_MODE = isTermuxTuiMode(process.env)
export const INLINE_MODE = TERMUX_TUI_MODE || truthy(process.env.LOKI_TUI_INLINE)
export const SHOW_FPS = truthy(process.env.LOKI_TUI_FPS)
export const DEV_CREDITS_MODE = truthy(process.env.LOKI_DEV_CREDITS)
export const NO_CONFIRM_DESTRUCTIVE = truthy(process.env.LOKI_TUI_NO_CONFIRM)

export const MOUSE_TRACKING: MouseTrackingMode = truthy(process.env.LOKI_TUI_DISABLE_MOUSE) ? 'off' : 'all'
