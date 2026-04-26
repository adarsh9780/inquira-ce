export const THEME_OPTIONS = [
  {
    id: 'warm',
    label: 'Warm Light',
    description: 'Current default palette with warm neutrals.',
    preview: ['#FAF9F6', '#F5F4EF', '#C96A2E']
  },
  {
    id: 'evergreen',
    label: 'Evergreen',
    description: 'Calm green-forward light palette for extended sessions.',
    preview: ['#F4F8F5', '#EAF3ED', '#1F7A5A']
  },
  {
    id: 'midnight',
    label: 'Midnight Dark',
    description: 'Deep slate dark palette with warm brand accent and softer glare.',
    preview: ['#101722', '#151E2B', '#C96A2E']
  },
  {
    id: 'daddylight',
    label: "Daddy's Light Theme",
    description: 'Warm neutral cream base with orange primary and mauve accent.',
    preview: ['#e9eae1', '#f4f5f0', '#ed9912']
  },
  {
    id: 'daddydark',
    label: "Daddy's Dark Theme",
    description: 'Inverted warm neutral base with orange primary and mauve accent.',
    preview: ['#d2d5c3', '#e9eae1', '#ed9912']
  }
]

export const DEFAULT_THEME_ID = 'warm'
export const THEME_IDS = THEME_OPTIONS.map((theme) => theme.id)

export function normalizeThemeId(value) {
  const normalized = String(value || '').trim().toLowerCase()
  return THEME_IDS.includes(normalized) ? normalized : DEFAULT_THEME_ID
}

export function getThemeById(value) {
  const normalized = normalizeThemeId(value)
  return THEME_OPTIONS.find((theme) => theme.id === normalized) || THEME_OPTIONS[0]
}
