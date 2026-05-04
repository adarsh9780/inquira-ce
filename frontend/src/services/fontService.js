import { DEFAULT_FONT_ID, normalizeFontId } from '../constants/fonts'
import { uiPreferencesService } from './uiPreferencesService'

const FONT_PREF_KEYS = ['ui_font', 'uiFont', 'font']

function resolveFontFromPrefs(prefs) {
  if (!prefs || typeof prefs !== 'object') return DEFAULT_FONT_ID
  const matchedKey = FONT_PREF_KEYS.find((key) => typeof prefs[key] === 'string' && prefs[key].trim())
  return normalizeFontId(matchedKey ? prefs[matchedKey] : DEFAULT_FONT_ID)
}

export const fontService = {
  async loadFontPreference() {
    try {
      const prefs = await uiPreferencesService.getPreferences()
      return resolveFontFromPrefs(prefs)
    } catch (_error) {
      return DEFAULT_FONT_ID
    }
  },

  async saveFontPreference(fontId) {
    const normalized = normalizeFontId(fontId)
    try {
      const prefs = await uiPreferencesService.getPreferences()
      const nextPrefs = {
        ...(prefs && typeof prefs === 'object' ? prefs : {}),
        ui_font: normalized
      }
      await uiPreferencesService.savePreferences(nextPrefs)
      return true
    } catch (_error) {
      return false
    }
  }
}
