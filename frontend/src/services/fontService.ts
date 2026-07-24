import {
  DEFAULT_APP_FONT_ID,
  DEFAULT_CODE_FONT_ID,
  normalizeAppFontId,
  normalizeCodeFontId,
} from '../constants/fonts'
import { uiPreferencesService, type UiPreferences } from './uiPreferencesService'

const APP_FONT_PREF_KEYS = ['ui_font', 'uiFont', 'font']
const CODE_FONT_PREF_KEYS = ['ui_code_font', 'uiCodeFont', 'code_font', 'codeFont']

function resolveAppFontFromPrefs(prefs: UiPreferences): string {
  if (!prefs || typeof prefs !== 'object') return DEFAULT_APP_FONT_ID
  const matchedKey = APP_FONT_PREF_KEYS.find((key) => typeof prefs[key] === 'string' && prefs[key].trim())
  return normalizeAppFontId(matchedKey ? prefs[matchedKey] : DEFAULT_APP_FONT_ID)
}

function resolveCodeFontFromPrefs(prefs: UiPreferences): string {
  if (!prefs || typeof prefs !== 'object') return DEFAULT_CODE_FONT_ID
  const matchedKey = CODE_FONT_PREF_KEYS.find((key) => typeof prefs[key] === 'string' && prefs[key].trim())
  return normalizeCodeFontId(matchedKey ? prefs[matchedKey] : DEFAULT_CODE_FONT_ID)
}

export const fontService = {
  async loadAppFontPreference(): Promise<string> {
    try {
      const prefs = await uiPreferencesService.getPreferences()
      return resolveAppFontFromPrefs(prefs)
    } catch (_error) {
      return DEFAULT_APP_FONT_ID
    }
  },

  async saveAppFontPreference(fontId: unknown): Promise<boolean> {
    const normalized = normalizeAppFontId(fontId)
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
  },

  async loadCodeFontPreference(): Promise<string> {
    try {
      const prefs = await uiPreferencesService.getPreferences()
      return resolveCodeFontFromPrefs(prefs)
    } catch (_error) {
      return DEFAULT_CODE_FONT_ID
    }
  },

  async saveCodeFontPreference(fontId: unknown): Promise<boolean> {
    const normalized = normalizeCodeFontId(fontId)
    try {
      const prefs = await uiPreferencesService.getPreferences()
      const nextPrefs = {
        ...(prefs && typeof prefs === 'object' ? prefs : {}),
        ui_code_font: normalized
      }
      await uiPreferencesService.savePreferences(nextPrefs)
      return true
    } catch (_error) {
      return false
    }
  },
}
