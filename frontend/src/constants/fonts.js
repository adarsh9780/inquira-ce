export const FONT_OPTIONS = [
  {
    id: 'default',
    label: 'Default',
    description: 'Current UI font stack (Manrope).',
  },
  {
    id: 'ubuntu-mono',
    label: 'Ubuntu Mono',
    description: 'Monospaced UI variant using Ubuntu Mono.',
  },
]

export const DEFAULT_FONT_ID = FONT_OPTIONS[0].id

const FONT_ID_SET = new Set(FONT_OPTIONS.map((font) => font.id))

export function normalizeFontId(fontId) {
  const normalized = String(fontId || '').trim().toLowerCase()
  if (!normalized) return DEFAULT_FONT_ID
  return FONT_ID_SET.has(normalized) ? normalized : DEFAULT_FONT_ID
}
