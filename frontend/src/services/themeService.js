import { DEFAULT_THEME_ID, normalizeThemeId } from '../constants/themes'
import { uiPreferencesService } from './uiPreferencesService'

const THEME_PREF_KEYS = ['ui_theme', 'uiTheme', 'theme']

function resolveThemeFromPrefs(prefs) {
  if (!prefs || typeof prefs !== 'object') return DEFAULT_THEME_ID
  const matchedKey = THEME_PREF_KEYS.find((key) => typeof prefs[key] === 'string' && prefs[key].trim())
  return normalizeThemeId(matchedKey ? prefs[matchedKey] : DEFAULT_THEME_ID)
}

export const themeService = {
  async loadThemePreference() {
    try {
      const prefs = await uiPreferencesService.getPreferences()
      return resolveThemeFromPrefs(prefs)
    } catch (_error) {
      return DEFAULT_THEME_ID
    }
  },

  async saveThemePreference(themeId) {
    const normalized = normalizeThemeId(themeId)
    try {
      const prefs = await uiPreferencesService.getPreferences()
      const nextPrefs = {
        ...(prefs && typeof prefs === 'object' ? prefs : {}),
        ui_theme: normalized
      }
      await uiPreferencesService.savePreferences(nextPrefs)
      return true
    } catch (_error) {
      return false
    }
  }
}
