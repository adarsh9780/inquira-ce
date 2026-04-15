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
    label: 'Midnight',
    description: 'High-contrast dark palette for low-light environments.',
    preview: ['#0F172A', '#111827', '#E38B57']
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
