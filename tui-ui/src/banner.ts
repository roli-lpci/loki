import type { ThemeColors } from './theme.js'

const RICH_RE = /\[(?:bold\s+)?(?:dim\s+)?(#(?:[0-9a-fA-F]{3,8}))\]([\s\S]*?)(\[\/\])/g

export function parseRichMarkup(markup: string): Line[] {
  const lines: Line[] = []

  for (const raw of markup.split('\n')) {
    const trimmed = raw.trimEnd()

    if (!trimmed) {
      lines.push(['', ' '])

      continue
    }

    const matches = [...trimmed.matchAll(RICH_RE)]

    if (!matches.length) {
      lines.push(['', trimmed])

      continue
    }

    let cursor = 0

    for (const m of matches) {
      const before = trimmed.slice(cursor, m.index)

      if (before) {
        lines.push(['', before])
      }

      lines.push([m[1]!, m[2]!])
      cursor = m.index! + m[0].length
    }

    if (cursor < trimmed.length) {
      lines.push(['', trimmed.slice(cursor)])
    }
  }

  return lines
}

const LOGO_ART = [
  '██╗      ██████╗ ██╗  ██╗██╗       █████╗  ██████╗ ███████╗███╗   ██╗████████╗',
  '██║     ██╔═══██╗██║ ██╔╝██║      ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝',
  '██║     ██║   ██║█████╔╝ ██║█████╗███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ',
  '██║     ██║   ██║██╔═██╗ ██║╚════╝██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ',
  '███████╗╚██████╔╝██║  ██╗██║      ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ',
  '╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝      ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   '
]

const WORDMARK_LARGE_ART = [
  '⠀⠀⣤⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⣤⣀⠀',
  '⢸⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⡀',
  '⢻⣿⣿⡟⠻⣿⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⡿⠛⣿⣿⣿⠇',
  '⢸⣿⣿⣇⠀⠈⢻⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡿⠋⠀⢀⣿⣿⣿⠀',
  '⠈⣿⣿⣿⡄⠀⠐⠙⡇⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⡟⠀⠀⠀⣾⣿⣿⡇⠀',
  '⠀⢻⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⣿⠀⠀',
  '⠀⠘⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⣿⣿⡏⠀⠀',
  '⠀⠀⢸⣿⣿⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⣿⣿⡿⠁⠀⠀',
  '⠀⠀⠀⢿⣿⣿⣿⡀⠀⠀⠀⣀⣀⣤⣤⣤⣀⣀⡀⠀⠀⠀⣼⣿⣿⣿⠃⠀⠀⠀',
  '⠀⠀⠀⠈⣿⣿⣿⣷⣴⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣦⣼⣿⣿⣿⠏⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⣿⠟⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠛⣿⡇⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⣿⡄⠀⠀⠉⠉⠛⠻⠿⠿⠛⠋⠉⠀⠀⠀⣿⠇⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣿⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⢸⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⠈⢿⣿⣿⣿⣦⠀⠀⠀⠀⠀⢠⣾⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⠀⠈⢿⣿⣿⣿⠀⠀⠀⠀⠀⢸⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⡇⠀⠀⠀⠀⠀⢸⣿⡟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠗⠀⠀⠀⠀⠀⠸⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀',
]

const WORDMARK_COMPACT_ART = [
  '⢸⣿⣿⣇⠀⠈⢻⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡿⠋⠀⢀⣿⣿⣿⠀',
  '⠈⣿⣿⣿⡄⠀⠐⠙⡇⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⡟⠀⠀⠀⣾⣿⣿⡇⠀',
  '⠀⢻⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⣿⠀⠀',
  '⠀⠘⣿⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⣿⣿⡏⠀⠀',
  '⠀⠀⢸⣿⣿⣿⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⣿⣿⡿⠁⠀⠀',
  '⠀⠀⠀⢿⣿⣿⣿⡀⠀⠀⠀⣀⣀⣤⣤⣤⣀⣀⡀⠀⠀⠀⣼⣿⣿⣿⠃⠀⠀⠀',
  '⠀⠀⠀⠈⣿⣿⣿⣷⣴⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣦⣼⣿⣿⣿⠏⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⣿⠟⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠛⣿⡇⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⣿⡄⠀⠀⠉⠉⠛⠻⠿⠿⠛⠋⠉⠀⠀⠀⣿⠇⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⣿⣧⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣿⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⢸⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⠈⢿⣿⣿⣿⣦⠀⠀⠀⠀⠀⢠⣾⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀',
  '⠀⠀⠀⠀⠀⠀⠀⠈⢿⣿⣿⣿⠀⠀⠀⠀⠀⢸⣿⣿⣿⠃⠀⠀⠀⠀⠀⠀⠀⠀',
]

const WORDMARK_MINI_ART = ['L O K I', 'A G E N T']

const LOGO_GRADIENT = [0, 0, 1, 1, 2, 2] as const
const WORDMARK_LARGE_GRADIENT = [0, 0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 3, 4, 3, 3, 2, 2, 2, 1, 1, 0] as const
const WORDMARK_COMPACT_GRADIENT = [0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 3, 4, 5, 4, 3, 3, 2, 2] as const
const WORDMARK_MINI_GRADIENT = [1, 3] as const

const colorize = (art: string[], gradient: readonly number[], c: ThemeColors): Line[] => {
  const p = [c.primary, c.accent, c.border, c.muted]

  return art.map((text, i) => [p[gradient[i]!] ?? c.muted, text])
}

export const LOGO_WIDTH = Math.max(...LOGO_ART.map(line => line.length))
export const WORDMARK_WIDTH = Math.max(...WORDMARK_LARGE_ART.map(line => line.length))

export const logo = (c: ThemeColors, customLogo?: string): Line[] =>
  customLogo ? parseRichMarkup(customLogo) : colorize(LOGO_ART, LOGO_GRADIENT, c)

export const wordmark = (c: ThemeColors, customHero?: string, maxWidth = WORDMARK_WIDTH): Line[] => {
  if (customHero) return parseRichMarkup(customHero)
  if (maxWidth >= WORDMARK_WIDTH) return colorize(WORDMARK_LARGE_ART, WORDMARK_LARGE_GRADIENT, c)
  if (maxWidth >= 24) return colorize(WORDMARK_COMPACT_ART, WORDMARK_COMPACT_GRADIENT, c)
  return colorize(WORDMARK_MINI_ART, WORDMARK_MINI_GRADIENT, c)
}

export const artWidth = (lines: Line[]) => lines.reduce((m, [, t]) => Math.max(m, t.length), 0)

type Line = [string, string]
