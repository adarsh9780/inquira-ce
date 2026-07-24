import { describe, expect, it } from 'vitest'

import {
  DEFAULT_APP_FONT_ID,
  DEFAULT_CODE_FONT_ID,
  normalizeAppFontId,
  normalizeCodeFontId,
} from '../src/constants/fonts'
import {
  DEFAULT_THEME_ID,
  getThemeById,
  normalizeThemeId,
} from '../src/constants/themes'

describe('UI constants', () => {
  it('normalizes supported font identifiers and rejects unknown values', () => {
    expect(normalizeAppFontId('INTER')).toBe('inter')
    expect(normalizeAppFontId('unknown')).toBe(DEFAULT_APP_FONT_ID)
    expect(normalizeCodeFontId('fira-code')).toBe('fira-code')
    expect(normalizeCodeFontId(null)).toBe(DEFAULT_CODE_FONT_ID)
  })

  it('normalizes current and legacy theme identifiers', () => {
    expect(normalizeThemeId('midnight')).toBe('midnight')
    expect(normalizeThemeId('classicdark')).toBe('midnight')
    expect(normalizeThemeId('evergreen')).toBe('warm')
    expect(normalizeThemeId('unknown')).toBe(DEFAULT_THEME_ID)
    expect(getThemeById('midnight').label).toBe('Bluehour')
  })
})
