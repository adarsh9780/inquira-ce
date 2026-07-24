export interface ThemeOption {
  id: string
  label: string
  description: string
  preview: readonly [string, string, string]
}

export const THEME_OPTIONS: readonly ThemeOption[] = [
  {
    id: 'warm',
    label: 'Foundry',
    description: 'Editorial parchment light theme with clay actions and cooler data accents.',
    preview: ['#FBF8F2', '#F4EEE5', '#B86A3D']
  },
  {
    id: 'midnight',
    label: 'Bluehour',
    description: 'Low-glare navy workspace with crisp tables, balanced contrast, and distinct chart colors.',
    preview: ['#101923', '#16212C', '#78A9E6']
  }
]

export const DEFAULT_THEME_ID = 'warm'
export const THEME_IDS = THEME_OPTIONS.map((theme) => theme.id)

export function normalizeThemeId(value: unknown): string {
  const normalized = String(value || '').trim().toLowerCase()
  if (['classicdark', 'daddydark'].includes(normalized)) return 'midnight'
  if (['classiclight', 'evergreen', 'daddylight'].includes(normalized)) return 'warm'
  return THEME_IDS.includes(normalized) ? normalized : DEFAULT_THEME_ID
}

export function getThemeById(value: unknown): ThemeOption {
  const normalized = normalizeThemeId(value)
  return THEME_OPTIONS.find((theme) => theme.id === normalized) || THEME_OPTIONS[0]
}
