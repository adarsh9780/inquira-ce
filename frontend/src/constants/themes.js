export const THEME_OPTIONS = [
  {
    id: 'classiclight',
    label: 'Northbound',
    description: 'Neutral white application shell with graphite text and restrained slate accents.',
    preview: ['#FFFFFF', '#E5E7EB', '#3B82F6']
  },
  {
    id: 'classicdark',
    label: 'Afterhours',
    description: 'Standard charcoal dark mode with balanced panels and cool slate highlights.',
    preview: ['#111827', '#253046', '#7C93C8']
  },
  {
    id: 'warm',
    label: 'Foundry',
    description: 'Editorial parchment light theme with clay actions and cooler data accents.',
    preview: ['#FBF8F2', '#F4EEE5', '#B86A3D']
  },
  {
    id: 'evergreen',
    label: 'Canopy',
    description: 'Quiet sage palette with deeper contrast for long analytical sessions.',
    preview: ['#F7FAF7', '#ECF2ED', '#21684F']
  },
  {
    id: 'midnight',
    label: 'Bluehour',
    description: 'Layered graphite dark mode with restrained copper accents and softer contrast.',
    preview: ['#111A24', '#182230', '#C97443']
  },
  {
    id: 'daddylight',
    label: 'Atelier',
    description: 'Cream-and-plum light theme with toasted gold highlights and softer neutrals.',
    preview: ['#FBF6EF', '#F4EDE3', '#7B6178']
  },
  {
    id: 'daddydark',
    label: 'Ledger',
    description: 'Moss-charcoal dark theme with old-gold primaries and muted plum accents.',
    preview: ['#1C231F', '#222B26', '#C08B3A']
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
