import { nativeApp } from '../api/native'

const UI_PREFERENCES_SCOPE = 'ui-preferences'

export type UiPreferences = Record<string, unknown>

function loadBrowserPreferences(): UiPreferences {
    if (typeof localStorage === 'undefined') return {}
    try {
        const stored = localStorage.getItem('ui_preferences')
        if (!stored) return {}
        const parsed = JSON.parse(stored)
        return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
    } catch (_error) {
        return {}
    }
}

export const uiPreferencesService = {
    async getPreferences(): Promise<UiPreferences> {
        const app = nativeApp()
        if (app?.LoadLocalState) {
            try {
                const nativePreferences = await app.LoadLocalState(UI_PREFERENCES_SCOPE)
                if (nativePreferences && typeof nativePreferences === 'object' && !Array.isArray(nativePreferences)) {
                    return nativePreferences as UiPreferences
                }
                return {}
            } catch (error) {
                console.warn('Failed to load UI preferences through Wails:', error)
                return {}
            }
        }
        return loadBrowserPreferences()
    },

    async savePreferences(prefs: UiPreferences): Promise<boolean> {
        const app = nativeApp()
        if (app?.SaveLocalState) {
            try {
                return Boolean(await app.SaveLocalState(UI_PREFERENCES_SCOPE, prefs))
            } catch (error) {
                console.warn('Failed to save UI preferences through Wails:', error)
                return false
            }
        }
        try {
            localStorage.setItem('ui_preferences', JSON.stringify(prefs))
            return true
        } catch (_error) {
            return false
        }
    },
}
