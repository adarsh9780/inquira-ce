export const APP_FONT_OPTIONS = [
  {
    id: 'default',
    label: 'Default',
    description: 'Current UI font stack (Manrope).',
  },
  {
    id: 'ubuntu',
    label: 'Ubuntu',
    description: 'Sans-serif UI variant using Ubuntu.',
  },
  {
    id: 'inter',
    label: 'Inter',
    description: 'Modern sans-serif used widely in desktop and web apps.',
  },
  {
    id: 'source-sans-3',
    label: 'Source Sans 3',
    description: 'Readable humanist sans for dense productivity screens.',
  },
  {
    id: 'ibm-plex-sans',
    label: 'IBM Plex Sans',
    description: 'Neutral enterprise-grade sans with strong UI clarity.',
  },
]

export const CODE_FONT_OPTIONS = [
  {
    id: 'jetbrains-mono',
    label: 'JetBrains Mono',
    description: 'Default coding font optimized for development workflows.',
  },
  {
    id: 'fira-code',
    label: 'Fira Code',
    description: 'Popular coding font with ligature support.',
  },
  {
    id: 'source-code-pro',
    label: 'Source Code Pro',
    description: 'Clean Adobe monospaced font for source editing.',
  },
  {
    id: 'ibm-plex-mono',
    label: 'IBM Plex Mono',
    description: 'Technical mono style with balanced character shapes.',
  },
  {
    id: 'roboto-mono',
    label: 'Roboto Mono',
    description: 'Compact monospaced font commonly used in IDEs and tools.',
  },
]

export const DEFAULT_APP_FONT_ID = APP_FONT_OPTIONS[0].id
export const DEFAULT_CODE_FONT_ID = CODE_FONT_OPTIONS[0].id

const APP_FONT_ID_SET = new Set(APP_FONT_OPTIONS.map((font) => font.id))
const CODE_FONT_ID_SET = new Set(CODE_FONT_OPTIONS.map((font) => font.id))

export function normalizeAppFontId(fontId) {
  const normalized = String(fontId || '').trim().toLowerCase()
  if (!normalized) return DEFAULT_APP_FONT_ID
  return APP_FONT_ID_SET.has(normalized) ? normalized : DEFAULT_APP_FONT_ID
}

export function normalizeCodeFontId(fontId) {
  const normalized = String(fontId || '').trim().toLowerCase()
  if (!normalized) return DEFAULT_CODE_FONT_ID
  return CODE_FONT_ID_SET.has(normalized) ? normalized : DEFAULT_CODE_FONT_ID
}
