export const THEME_OPTIONS = [
  {
    id: 'warm',
    label: 'Foundry',
    description: 'Editorial parchment light theme with clay actions and cooler data accents.',
    preview: ['#FBF8F2', '#F4EEE5', '#B86A3D']
  },
  {
    id: 'midnight',
    label: 'Bluehour',
    description: 'High-contrast graphite dark theme with warm copper actions and clear data accents.',
    preview: ['#101821', '#182431', '#D18455']
  }
]

export const DEFAULT_THEME_ID = 'warm'
export const THEME_IDS = THEME_OPTIONS.map((theme) => theme.id)

export function normalizeThemeId(value) {
  const normalized = String(value || '').trim().toLowerCase()
  if (['classicdark', 'daddydark'].includes(normalized)) return 'midnight'
  if (['classiclight', 'evergreen', 'daddylight'].includes(normalized)) return 'warm'
  return THEME_IDS.includes(normalized) ? normalized : DEFAULT_THEME_ID
}

export function getThemeById(value) {
  const normalized = normalizeThemeId(value)
  return THEME_OPTIONS.find((theme) => theme.id === normalized) || THEME_OPTIONS[0]
}
